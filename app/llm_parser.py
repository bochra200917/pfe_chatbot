#app/llm_parser.py
import json
import re
from models.pydantic_models import LLMQuery, ChatbotResponse

def parse_llm_json(response: str) -> LLMQuery:

    try:
        # Nettoyer les balises markdown si présentes
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", response).strip()

        if not clean:
            raise ValueError("Réponse LLM vide")

        data = json.loads(clean)

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