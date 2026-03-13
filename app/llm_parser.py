# app/llm_parser.py
import json
from app.models_v3 import LLMQuery

def parse_llm_json(response: str) -> LLMQuery:

    try:
        data = json.loads(response)

        parsed = LLMQuery(**data)

        if not parsed.tables:
            raise ValueError("LLM n'a retourné aucune table")

        if len(parsed.tables) > 1:
            raise ValueError("LLM tente d'utiliser plusieurs tables")

        if not parsed.columns:
            raise ValueError("LLM n'a retourné aucune colonne")

        if len(parsed.columns) > 10:
            raise ValueError("Trop de colonnes demandées")

        if parsed.limit > 100:
            parsed.limit = 100

        if parsed.limit <= 0:
            parsed.limit = 10

        return parsed

    except Exception as e:
        raise ValueError(f"Réponse LLM invalide: {e}")