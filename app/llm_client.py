# app/llm_client.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY manquant dans .env")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_NAME = "google/gemini-2.0-flash-lite"

def call_llm(prompt: str):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "temperature": 0,
        "max_tokens": 200,
        "messages": [
            {
                "role": "system",
                "content": "Convert business questions to JSON for SQL queries. Return JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"LLM API error {response.status_code}: {response.text}")

    data = response.json()

    return data["choices"][0]["message"]["content"]