# app/llm_parser.py

import json
from app.models_v3 import LLMQuery


def parse_llm_json(response: str) -> LLMQuery:
    """
    Parse et valide la réponse JSON du LLM
    """

    try:
        data = json.loads(response)

        parsed = LLMQuery(**data)

        # validation tables
        if not parsed.tables:
            raise ValueError("LLM n'a retourné aucune table")

        # validation colonnes
        if not parsed.columns:
            raise ValueError("LLM n'a retourné aucune colonne")

        # limite maximum
        if parsed.limit > 100:
            parsed.limit = 100

        if parsed.limit <= 0:
            parsed.limit = 10

        return parsed

    except Exception as e:
        raise ValueError(f"Réponse LLM invalide: {e}")