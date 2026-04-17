# app/llm_parser.py

import json
import re
from datetime import datetime, timedelta
from app.models_v3 import LLMQuery


# ✅ INTENTS VALIDES
VALID_INTENTS = [
    "get_factures_between",
    "get_factures_par_client",
    "get_factures_non_payees",
    "get_factures_partiellement_payees",
    "get_factures_negatives",
    "get_clients_multiple_commandes",
    "get_produits_stock_faible",
    "get_total_ventes_mois",
    "get_total_paiements",
    "get_commandes_par_mois",
    "get_produits_non_commandes"  # ✅ AJOUT ICI
]


# ✅ ALIASES INTENTS
INTENT_ALIASES = {
    "get_produits_pas_commandes": "get_produits_non_commandes",
    "produits_non_commandes": "get_produits_non_commandes",
}


# ✅ ALIASES TABLES
TABLE_ALIASES = {
    "produit": "m38h_product",
    "products": "m38h_product"
}


# ✅ NORMALISATION TABLES
def normalize_tables(tables):
    if not tables:
        return ["m38h_commande"]

    normalized = []
    for t in tables:
        t = t.lower().strip()
        t = TABLE_ALIASES.get(t, t)
        normalized.append(t)

    return [normalized[0]]  # UNE seule table


# ✅ PARSER PRINCIPAL
def parse_llm_json(response: str, prompt: str) -> LLMQuery:
    try:
        # Nettoyage markdown
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", response).strip()

        if not clean:
            raise ValueError("Réponse LLM vide")

        data = json.loads(clean)

        # ─────────────────────────────
        # 🔥 CORRECTION INTENT
        # ─────────────────────────────
        intent = data.get("intent")

        if intent in INTENT_ALIASES:
            intent = INTENT_ALIASES[intent]

        if intent not in VALID_INTENTS:
            raise ValueError(f"Intent non supporté: {intent}")
        
        data["intent"] = intent

        # ─────────────────────────────
        # 🔥 CORRECTION TABLES
        # ─────────────────────────────
        tables = data.get("tables", [])
        data["tables"] = normalize_tables(tables)

        # ─────────────────────────────
        # 🔥 CORRECTION FILTRES
        # ─────────────────────────────
        filters = data.get("filters", {})

        # cas commandes par mois avec start_date
        if intent == "get_commandes_par_mois" and "start_date" in filters:
            start = filters["start_date"]
            data["filters"] = {
                "year": start[:4],
                "month": start[5:7]
            }

        # cas ventes mois avec start_date
        if intent == "get_total_ventes_mois" and "start_date" in filters:
            start = filters["start_date"]
            data["filters"] = {
                "year": start[:4],
                "month": start[5:7]
            }

        # cas "3 derniers mois"
        if prompt and "3 derniers mois" in prompt.lower():
            end = datetime.today()
            start = end - timedelta(days=90)

            data["intent"] = "get_total_paiements"
            data["filters"] = {
                "start_date": start.strftime("%Y-%m-%d"),
                "end_date": end.strftime("%Y-%m-%d")
            }

        # ─────────────────────────────
        # 🔥 LIMIT SAFE
        # ─────────────────────────────
        if data.get("limit", 100) > 100:
            data["limit"] = 100

        if data.get("limit", 0) <= 0:
            data["limit"] = 10

        # ─────────────────────────────
        # ✅ VALIDATION FINALE
        # ─────────────────────────────
        parsed = LLMQuery(**data)

        return parsed

    except Exception as e:
        raise ValueError(f"Réponse LLM invalide: {e}")