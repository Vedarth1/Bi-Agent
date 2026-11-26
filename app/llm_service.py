import requests
from app.config import OLLAMA_BASE_URL, MODEL_NAME

def ask_llm(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    response = requests.post(
        f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
        json=payload
    )
    response.raise_for_status()

    return response.json()["message"]["content"]