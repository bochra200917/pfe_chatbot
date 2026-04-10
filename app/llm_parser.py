#app/llm_parser.py
import json
import re
from app.models_v3 import LLMQuery, ChatbotResponse
from datetime import datetime, timedelta

TABLE_MAPPING = {
    "factures": "m38h_facture",
    "facture": "m38h_facture",
    "clients": "m38h_societe",
    "client": "m38h_societe",
    "paiements": "m38h_paiement_facture",
    "paiement": "m38h_paiement_facture"
}

def normalize_tables(tables):
    normalized = []
    for t in tables:
        t_clean = t.lower().strip()
        mapped = TABLE_MAPPING.get(t_clean, t_clean)
        normalized.append(mapped)

    # 🔥 garder UNE seule table (la première)
    if len(normalized) > 1:
        return [normalized[0]]

    return normalized

def parse_llm_json(response: str, prompt: str) -> LLMQuery:
    try:
        # Nettoyer les balises markdown si présentes
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", response).strip()

        if not clean:
            raise ValueError("Réponse LLM vide")

        data = json.loads(clean)
        # CORRECTION INTELLIGENTE DES FILTRES

        intent = data.get("intent")
        filters = data.get("filters", {})

        # Cas 1 : LLM met start_date/end_date mais intent ventes_mois
        if intent == "get_total_ventes_mois" and "start_date" in filters:
            try:
                start = filters["start_date"]
                year = start[:4]
                month = start[5:7]

                data["filters"] = {
                    "year": year,
                    "month": month
                }
            except Exception:
                pass
        
        if prompt and "3 derniers mois" in prompt.lower():
            end_date = datetime.today()
            start_date = end_date - timedelta(days=90)

            data["filters"] = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
            data["intent"] = "get_total_paiements"
        
        # Cas 2 : LLM met year/month mais intent between
        if intent == "get_factures_between" and "year" in filters:
            try:
                year = filters["year"]
                month = filters.get("month", "01")

                data["filters"] = {
                    "start_date": f"{year}-{month}-01",
                    "end_date": f"{year}-{month}-28"
        }  
            except Exception:
                pass
        
        # NORMALISATION AVANT VALIDATION
        if "tables" in data:
            data["tables"] = normalize_tables(data["tables"])

        parsed = LLMQuery(**data)

        if not parsed.tables:
            raise ValueError("LLM n'a retourné aucune table")

        if len(parsed.tables) > 1:
            raise ValueError("LLM tente d'utiliser plusieurs tables")

        if len(parsed.columns) > 10:
            raise ValueError("Trop de colonnes demandées")

        if parsed.limit > 100:
            parsed.limit = 100

        if parsed.limit <= 0:
            parsed.limit = 10

        return parsed

    except Exception as e:
        raise ValueError(f"Réponse LLM invalide: {e}")