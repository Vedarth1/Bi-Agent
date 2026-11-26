import json
import requests
from app.config import OLLAMA_BASE_URL, MODEL_NAME
from app.tools import TOOLS, execute_tool


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


def ask_llm(prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]

    # ---- ROUND 1: ask the model, offering the tools ----
    data1 = _chat(messages)
    print("---- response1 ----")
    print(json.dumps(data1, indent=2))

    message = data1["message"]

    # ---- if the model requested tools, honor them ----
    if "tool_calls" in message and message["tool_calls"]:

        # echo the assistant's own tool_call message back — Ollama expects
        # the conversation to contain the model's request before the result
        messages.append(message)

        for tool_call in message["tool_calls"]:
            name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]  # OBJECT in native API (OpenAI uses a JSON string)
            result = execute_tool(name, arguments)
            print(f"TOOL EXECUTED: {name}({arguments}) -> {result[:100]}")
            messages.append({"role": "tool", "content": result})

        print("---- messages before round 2 ----")
        print(json.dumps(messages, indent=2))

        # ---- ROUND 2: identical call, longer list ----
        data2 = _chat(messages)
        print("---- response2 ----")
        print(json.dumps(data2, indent=2))
        return data2["message"]["content"]

    # no tools requested -> the model already answered
    return message["content"]