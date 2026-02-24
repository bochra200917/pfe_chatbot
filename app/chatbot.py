# app/chatbot.py

import re
from datetime import datetime
from app import templates_sql
from app.db import execute_query
import uuid
import time

MONTHS = {
    "janvier": "01",
    "février": "02",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "août": "08",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "décembre": "12",
    "decembre": "12"
}

def match_question(question: str):
    question = question.lower().strip()

    # ==============================
    # FACTURES ENTRE DATES
    # ==============================
    match = re.search(r'(\d{4}-\d{2}-\d{2}).*(\d{4}-\d{2}-\d{2})', question)
    if "facture" in question and match:
        return templates_sql.get_factures_between, {
            "start_date": match.group(1),
            "end_date": match.group(2)
        }

    # ==============================
    # MOIS TEXTE (janvier 2026)
    # ==============================
    for month_name, month_num in MONTHS.items():
        if month_name in question:
            match_year = re.search(r'\b(20\d{2})\b', question)
            if match_year:
                return templates_sql.get_total_ventes_mois, {
                    "year": match_year.group(1),
                    "month": month_num
                }

    # ==============================
    # TOTAL VENTES YYYY-MM
    # ==============================
    match = re.search(r'(\d{4})-(\d{2})', question)
    if match and ("total" in question or "ventes" in question or "chiffre" in question):
        return templates_sql.get_total_ventes_mois, {
            "year": match.group(1),
            "month": match.group(2)
        }

    # ==============================
    # FACTURES NON PAYÉES
    # ==============================
    if "non pay" in question:
        return templates_sql.get_factures_non_payees, {}

    # ==============================
    # FACTURES PARTIELLEMENT PAYÉES
    # ==============================
    if "partiel" in question:
        return templates_sql.get_factures_partiellement_payees, {}

    # ==============================
    # FACTURES PAR CLIENT
    # ==============================
    match = re.search(r'client\s+(\w+)', question)
    if "facture" in question and match:
        return templates_sql.get_factures_par_client, {
            "client": match.group(1)
        }

    # ==============================
    # CLIENTS AVEC N COMMANDES
    # ==============================
    match = re.search(r'plus de (\d+) commandes', question)
    if match:
        return templates_sql.get_clients_multiple_commandes, {
            "min_commandes": int(match.group(1))
        }
    if "plusieurs commandes" in question or "commandes multiples" in question:
        return templates_sql.get_clients_multiple_commandes, {
            "min_commandes": 2
        }

    # ==============================
    # STOCK FAIBLE
    # ==============================
    match = re.search(r'stock.*(\d+)', question)
    if match:
        return templates_sql.get_produits_stock_faible, {
            "stock_min": int(match.group(1))
        }

    # ==============================
    # FACTURES MONTANTS NÉGATIFS
    # ==============================
    if "montant négatif" in question or "total_ht < 0" in question or "factures négatives" in question:
        return templates_sql.get_factures_negatives, {}

    return None, None


# ==============================
# FONCTION PRINCIPALE : GET RESPONSE
# ==============================
def get_response(question: str):
    start_time = time.time()
    template_func, params = match_question(question)

    if template_func is None:
        return {
            "table": [],
            "summary": "Question non reconnue",
            "metadata": {
                "template": None,
                "duration_ms": 0,
                "row_count": 0,
                "params": {}
            }
        }

    columns, rows = execute_query(template_func(), params)
    duration = (time.time() - start_time) * 1000
    return {
        "table": [dict(zip(columns, r)) for r in rows],
        "summary": f"{len(rows)} résultat(s) trouvé(s).",
        "metadata": {
            "template": template_func.__name__,
            "duration_ms": duration,
            "row_count": len(rows),
            "params": params,
            "logs_id": str(uuid.uuid4())
        }
    }