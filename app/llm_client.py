#app/llm_client.py
import os
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_NAME = "moonshotai/kimi-k2-instruct"


def call_llm(prompt: str):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "temperature": 0,
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "You convert business questions into structured JSON for SQL queries. Return JSON only."
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
        timeout=10
    )

    if response.status_code != 200:
        raise Exception("LLM API error")

    data = response.json()

    return data["choices"][0]["message"]["content"]