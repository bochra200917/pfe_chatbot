# test/test_llm.py
import os
from dotenv import load_dotenv
import requests

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
print(f"Clé utilisée : {key[:10]}...")

response = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    },
    json={
        "model": "google/gemini-2.0-flash-lite-001",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "dis bonjour"}]
    }
)

print(response.status_code)
print(response.json())