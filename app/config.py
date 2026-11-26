import os
import sys

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

if not OLLAMA_BASE_URL or not MODEL_NAME:
    print("ERROR: OLLAMA_BASE_URL and MODEL_NAME are required")
    sys.exit(1)