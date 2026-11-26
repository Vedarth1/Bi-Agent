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
    "4. If run_query returns SQL ERROR about a broken query, fix the SQL and retry once.If the error says an action is not allowed (read-only), do NOT retry — tell the user it is not permitted.\n"
    "5. Never write tool calls as text or JSON inside your reply. To use a tool, emit a real tool_call.\n"
    "6. Final answers: short prose, based only on data returned by tools."
)

def _chat(messages: list) -> dict:
    """One raw POST to Ollama. Returns the parsed response body."""
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "tools": TOOLS,
    }
    response = requests.post(
        f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
        json=payload,
    )
    response.raise_for_status()
    return response.json()

def _try_parse_tool_call(content: str) -> dict | None:
    """Repair path: some models emit tool calls as plain JSON inside content
    instead of a real tool_calls object. Find the first '{' and try to parse
    outward-expanding substrings until one is valid JSON."""
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
    """Models use inconsistent shapes. Accept both:
    {'name': ..., 'parameters': {...}}  and  {'function': {'name': ..., 'arguments': {...}}}"""
    fn = obj.get("function")
    if isinstance(fn, dict) and fn.get("name"):
        args = fn.get("arguments") or {}
        return fn["name"], args if isinstance(args, dict) else {}

    name = obj.get("name")
    if not name:
        return None
    args = obj.get("parameters") or obj.get("arguments") or {}
    return name, args if isinstance(args, dict) else {}

def run_agent(prompt: str, max_iterations: int = MAX_ITERATIONS) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    for iteration in range(1, max_iterations + 1):
        data = _chat(messages)
        message = data["message"]
        tool_calls = message.get("tool_calls") or []

        # no tool requests -> the model is done; this is the final answer
        if not tool_calls:
            content = message.get("content", "").strip()
            recovered = _try_parse_tool_call(content) if content else None
            if recovered:
                name, arguments = _normalize_tool_call(recovered)
                print(f"RECOVERED text tool call: {name}({arguments})")
                messages.append(message)  # echo the assistant's text message
                result = execute_tool(name, arguments)
                print(f"TOOL {name}({arguments}) -> {result[:120]}")
                messages.append({"role": "tool", "content": result})
                continue  # next iteration: model now has the result

            if content:
                return content
            return "ERROR: model returned an empty response"

        print(f"---- iteration {iteration}: {len(tool_calls)} tool call(s) ----")
        messages.append(message)  # echo assistant's tool_call message back

        for tc in tool_calls:
            name = tc["function"]["name"]
            arguments = tc["function"]["arguments"]
            result = execute_tool(name, arguments)
            print(f"TOOL {name}({arguments}) -> {result[:120]}")
            messages.append({"role": "tool", "content": result})

        usage = data.get("prompt_eval_count")
        print(f"context now: prompt_eval_count={usage}")

    return (
        f"ERROR: stopped after {max_iterations} tool iterations without a final answer. "
        f"Last context size: {len(messages)} messages."
    )