# app/chatbot.py

import re
import unicodedata
import time

from app.templates_sql import TEMPLATE_MAPPING
from app.db import execute_query
from app.logger import log_query
from app.sql_security import detect_injection
from app.chatbot_v3 import run_llm_pipeline


MONTHS = {
    "janvier": "01",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "decembre": "12"
}


# ---------------------------
# NORMALISATION TEXTE
# ---------------------------
def normalize(text: str):

    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")

    return text


# ---------------------------
# ROUTING NLP → TEMPLATE
# ---------------------------
def match_question(question: str):

    q = normalize(question)

    # factures entre dates
    match = re.search(r'(\d{4}-\d{2}-\d{2}).*(\d{4}-\d{2}-\d{2})', q)

    if "facture" in q and match:

        return "get_factures_between", {
            "start_date": match.group(1),
            "end_date": match.group(2)
        }

    # factures partiellement payées
    if "partiellement pay" in q:

        return "get_factures_partiellement_payees", {}

    # factures non payées
    if "non pay" in q or "impaye" in q:

        return "get_factures_non_payees", {}

    # factures par client
    match = re.search(r'client\s+(.+)', q)

    if "facture" in q and match:

        client_name = match.group(1).strip()

        return "get_factures_par_client", {
            "client": client_name
        }

    # ventes par mois texte
    for month_name, month_num in MONTHS.items():

        if month_name in q:

            match_year = re.search(r'\b(20\d{2})\b', q)

            if match_year:

                return "get_total_ventes_mois", {
                    "year": match_year.group(1),
                    "month": month_num
                }

    # ventes YYYY-MM
    match = re.search(r'(\d{4})-(\d{2})', q)

    if match and any(word in q for word in ["total", "ventes", "chiffre"]):

        return "get_total_ventes_mois", {
            "year": match.group(1),
            "month": match.group(2)
        }

    # clients plusieurs commandes
    match = re.search(r'plus de (\d+) commandes', q)

    if match:

        return "get_clients_multiple_commandes", {
            "min_commandes": int(match.group(1))
        }

    if "plusieurs commandes" in q:

        return "get_clients_multiple_commandes", {
            "min_commandes": 2
        }

    # stock faible
    if "stock" in q:

        match = re.search(r'\d+', q)

        if match:

            return "get_produits_stock_faible", {
                "stock_min": int(match.group())
            }

        return "get_produits_stock_faible", {
            "stock_min": 5
        }

    # factures négatives
    if "negatif" in q:

        return "get_factures_negatives", {}

    return None, None


# ---------------------------
# EXECUTION COMPLETE
# ---------------------------
def get_response(question: str):

    start_time = time.time()

    # sécurité SQL
    try:
        detect_injection(question)

    except Exception:

        return {
            "table": [],
            "summary": "Requête rejetée pour des raisons de sécurité.",
            "metadata": {
                "status": "rejected"
            }
        }

    template_name, params = match_question(question)

    # gestion ambiguïtés
    ambiguous_patterns = [
        "factures du client",
        "ventes du mois",
        "donne moi les ventes",
        "factures du mois dernier"
    ]

    if template_name is None:

        if any(p in question.lower() for p in ambiguous_patterns):

            return {
                "table": [],
                "summary": "Veuillez préciser votre demande.",
                "metadata": {
                    "status": "clarification_required"
                }
            }

        # fallback LLM
        try:

            result = run_llm_pipeline(question)

            return {
                "table": result,
                "summary": f"{len(result)} résultat(s) trouvé(s).",
                "metadata": {
                    "template": "llm_generated",
                    "row_count": len(result),
                    "status": "success_llm"
                }
            }

        except Exception:

            return {
                "table": [],
                "summary": "Je ne peux pas répondre à cette question.",
                "metadata": {
                    "status": "rejected"
                }
            }

    # récupération fonction SQL
    template_function = TEMPLATE_MAPPING.get(template_name)

    if template_function is None:

        return {
            "table": [],
            "summary": "Template non trouvé.",
            "metadata": {
                "template": template_name
            }
        }

    sql_query = template_function()

    try:

        columns, rows, execution_time = execute_query(sql_query, params)
        duration = round((time.time() - start_time) * 1000, 2)

        result_rows = [dict(zip(columns, row)) for row in rows]

        log_id = log_query(
            question,
            sql_query,
            duration,
            len(result_rows),
            template_name,
            params,
            "success",
            None
        )

        return {
            "table": result_rows,
            "summary": f"{len(result_rows)} résultat(s) trouvé(s).",
            "metadata": {
                "template": template_name,
                "duration_ms": duration,
                "row_count": len(result_rows),
                "params": params,
                "logs_id": log_id
            }
        }

    except Exception as e:

        duration = execution_time
        log_id = log_query(
            question,
            sql_query,
            duration,
            0,
            template_name,
            params,
            "error",
            str(e)
        )

        return {
            "table": [],
            "summary": "Erreur lors de l'exécution.",
            "metadata": {
                "template": template_name,
                "duration_ms": duration,
                "row_count": 0,
                "params": params,
                "error": str(e),
                "logs_id": log_id
            }
        }