
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def main():
    ollama_base_url = os.getenv("OLLAMA_BASE_URL")
    model_name = os.getenv("MODEL_NAME")

    # Fail fast if configuration is missing
    if not ollama_base_url or not model_name:
        print("ERROR: OLLAMA_BASE_URL and MODEL_NAME are required in .env")
        sys.exit(1)

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly: BI agent online."
            }
        ],
        "stream": False
    }

    try:
        response = requests.post(
            f"{ollama_base_url.rstrip('/')}/api/chat",
            json=payload
        )

        print(f"HTTP Status Code: {response.status_code}")

        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text

        print(json.dumps(response_body, indent=2))

        response.raise_for_status()

    except requests.RequestException as e:
        print(f"ERROR: Failed to communicate with Ollama: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
