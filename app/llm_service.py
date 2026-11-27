import json
import requests
from app.config import OLLAMA_BASE_URL, MODEL_NAME
from app.tools import TOOLS, execute_tool

MAX_ITERATIONS = 6

SYSTEM_PROMPT = (
    "You are a BI assistant that answers questions about a PostgreSQL database.\n"
    "Rules:\n"
    "1. You MUST use the provided tools for ALL data access. Never invent tables or columns.\n"
    "2. Call list_tables first if unsure what tables exist.\n"
    "3. Before writing SQL, call get_schema to learn the exact column names.\n"
    "4. If run_query returns SQL ERROR about a broken query, fix the SQL and retry once. If the error says an action is not allowed (read-only), do NOT retry — tell the user it is not permitted.\n"
    "5. Never write tool calls as text or JSON inside your reply. To use a tool, emit a real tool_call.\n"
    "6. Final answers: short prose, based only on data returned by tools."
)

CHART_SPEC_FORMAT = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["bar", "line", "pie"]},
        "title": {"type": "string"},
        "x_key": {"type": "string"},
        "y_key": {"type": "string"},
    },
    "required": ["type", "title", "x_key", "y_key"],
}


def _chat(messages: list, extra_payload: dict | None = None) -> dict:
    """One raw POST to Ollama. Returns the parsed response body."""
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "tools": TOOLS,
    }
    if extra_payload:
        payload.update(extra_payload)
    response = requests.post(
        f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
        json=payload,
    )
    response.raise_for_status()
    return response.json()


def _try_parse_tool_call(content: str) -> dict | None:
    """Repair path: some models emit tool calls as plain JSON inside content.
    Find the first '{' and try parsing outward-expanding substrings."""
    if "{" not in content:
        return None
    start = content.find("{")
    for end in range(len(content), start, -1):
        candidate = content[start:end]
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("name" in obj or "function" in obj):
            return obj
        return None  # valid JSON, but not a tool call — don't guess further
    return None


def _normalize_tool_call(obj: dict) -> tuple[str, dict] | None:
    """Accept both {'name': ..., 'parameters': {...}} and the official nested shape."""
    fn = obj.get("function")
    if isinstance(fn, dict) and fn.get("name"):
        args = fn.get("arguments") or {}
        return fn["name"], args if isinstance(args, dict) else {}

    name = obj.get("name")
    if not name:
        return None
    args = obj.get("parameters") or obj.get("arguments") or {}
    return name, args if isinstance(args, dict) else {}


def run_agent(prompt: str, max_iterations: int = MAX_ITERATIONS) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    sql_used = None
    tools_used = []

    for iteration in range(1, max_iterations + 1):
        data = _chat(messages)
        message = data["message"]
        tool_calls = message.get("tool_calls") or []
        content = message.get("content", "").strip()

        # no tool requests -> try to repair a text-disguised tool call, else final answer
        if not tool_calls:
            recovered = _try_parse_tool_call(content) if content else None
            if recovered:
                recovered_call = _normalize_tool_call(recovered)
                if recovered_call:
                    name, arguments = recovered_call
                    print(f"RECOVERED text tool call: {name}({arguments})")
                    messages.append(message)
                    result = execute_tool(name, arguments)
                    print(f"TOOL {name}({arguments}) -> {result[:120]}")
                    messages.append({"role": "tool", "content": result})
                    tools_used.append(name)
                    if name == "run_query" and not result.startswith(("ERROR", "SQL ERROR")):
                        sql_used = arguments.get("sql")
                    continue

            if content:
                return {"answer": content, "sql_used": sql_used,
                        "iterations": iteration - 1, "tools_used": tools_used}
            return {"answer": "ERROR: model returned an empty response",
                    "sql_used": sql_used, "iterations": iteration - 1, "tools_used": tools_used}

        print(f"---- iteration {iteration}: {len(tool_calls)} tool call(s) ----")
        messages.append(message)  # echo assistant's tool_call message back

        for tc in tool_calls:
            name = tc["function"]["name"]
            arguments = tc["function"]["arguments"]
            result = execute_tool(name, arguments)
            print(f"TOOL {name}({arguments}) -> {result[:120]}")
            messages.append({"role": "tool", "content": result})
            tools_used.append(name)
            if name == "run_query" and not result.startswith(("ERROR", "SQL ERROR")):
                sql_used = arguments.get("sql")

        print(f"context now: prompt_eval_count={data.get('prompt_eval_count')}")

    return {
        "answer": f"ERROR: stopped after {max_iterations} tool iterations without a final answer.",
        "sql_used": sql_used,
        "iterations": max_iterations,
        "tools_used": tools_used,
    }


def build_chart_spec(question: str, columns: list[str], rows: list[list]) -> dict:
    """Constrained decoding: Ollama's format= parameter forces a JSON chart spec."""
    data_text = "\n".join(
        [", ".join(columns)] + [", ".join(str(v) for v in row) for row in rows]
    )
    messages = [
        {"role": "system",
         "content": "You convert query results into chart specifications. Respond with JSON only, matching the requested schema."},
        {"role": "user",
         "content": (
             f"Question: {question}\n\n"
             f"Columns: {columns}\n\n"
             f"Data:\n{data_text}\n\n"
             "Pick type, title, x_key and y_key. x_key/y_key MUST be exact column names from the list."
         )},
    ]
    data = _chat(messages, extra_payload={
        "tools": [],               # no tools wanted here
        "format": CHART_SPEC_FORMAT,
    })
    return json.loads(data["message"]["content"])