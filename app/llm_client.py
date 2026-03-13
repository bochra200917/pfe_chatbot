# app/llm_client.py
import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "google/gemini-2.0-flash-lite-001"

# Rate limit : max appels par jour
MAX_CALLS_PER_DAY = 100
_call_count = 0
_last_reset = time.strftime("%Y-%m-%d")

def _check_rate_limit():
    global _call_count, _last_reset
    today = time.strftime("%Y-%m-%d")
    if today != _last_reset:
        _call_count = 0
        _last_reset = today
    if _call_count >= MAX_CALLS_PER_DAY:
        raise Exception(f"Quota journalier LLM atteint ({MAX_CALLS_PER_DAY} appels/jour)")
    _call_count += 1

def call_llm(prompt: str):

    _check_rate_limit()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "temperature": 0,
        "max_tokens": 200,
        "messages": [
            {"role": "system", "content": "Tu es un assistant qui identifie l'intention d'une question métier. Retourne UNIQUEMENT un JSON valide, sans markdown, sans explication."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        raise Exception(f"LLM API error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"]