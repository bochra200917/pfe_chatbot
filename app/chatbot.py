import re
import unicodedata
import time
from app import templates_sql
from app.db import execute_query
from app.logger import log_query


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


def normalize(text: str):
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    return text


def match_question(question: str):
    q = normalize(question)

    # ===============================
    # FACTURES ENTRE DATES
    # ===============================
    match = re.search(r'(\d{4}-\d{2}-\d{2}).*(\d{4}-\d{2}-\d{2})', q)
    if "facture" in q and match:
        return templates_sql.get_factures_between, {
            "start_date": match.group(1),
            "end_date": match.group(2)
        }

    # ===============================
    # FACTURES PARTIELLEMENT PAYEES
    # ===============================
    if "partiellement pay" in q:
        return templates_sql.get_factures_partiellement_payees, {}

    # ===============================
    # FACTURES NON PAYEES
    # ===============================
    if "non pay" in q:
        return templates_sql.get_factures_non_payees, {}

    # ===============================
    # FACTURES PAR CLIENT
    # ===============================
    match = re.search(r'client\s+(.+)', q)
    if "facture" in q and match:
        client_name = match.group(1).strip()
        return templates_sql.get_factures_par_client, {
            "client": client_name
        }

    # ===============================
    # TOTAL VENTES MOIS TEXTE
    # ===============================
    for month_name, month_num in MONTHS.items():
        if month_name in q:
            match_year = re.search(r'\b(20\d{2})\b', q)
            if match_year:
                return templates_sql.get_total_ventes_mois, {
                    "year": match_year.group(1),
                    "month": month_num
                }

    # ===============================
    # TOTAL VENTES YYYY-MM
    # ===============================
    match = re.search(r'(\d{4})-(\d{2})', q)
    if match and any(word in q for word in ["total", "ventes", "chiffre"]):
        return templates_sql.get_total_ventes_mois, {
            "year": match.group(1),
            "month": match.group(2)
        }

    # ===============================
    # CLIENTS PLUSIEURS COMMANDES
    # ===============================
    match = re.search(r'plus de (\d+) commandes', q)
    if match:
        return templates_sql.get_clients_multiple_commandes, {
            "min_commandes": int(match.group(1))
        }

    if "plusieurs commandes" in q:
        return templates_sql.get_clients_multiple_commandes, {
            "min_commandes": 2
        }

    if "commandes multiples" in q:
        return templates_sql.get_clients_multiple_commandes, {
            "min_commandes": 2
        }

    # ===============================
    # STOCK FAIBLE
    # ===============================
    if "stock" in q:
        match = re.search(r'\d+', q)
        if match:
            return templates_sql.get_produits_stock_faible, {
                "stock_min": int(match.group())
            }

    # ===============================
    # FACTURES NEGATIVES
    # ===============================
    if "negatif" in q:
        return templates_sql.get_factures_negatives, {}

    return None, None


def get_response(question: str):

    start_time = time.time()
    template_function, params = match_question(question)

    if template_function is None:
        return {
            "table": [],
            "summary": "Question non reconnue.",
            "metadata": {
                "template": None,
                "duration_ms": 0,
                "row_count": 0,
                "params": {},
                "logs_id": None
            }
        }

    sql_query = template_function()

    try:
        columns, rows = execute_query(sql_query, params)
        duration = round((time.time() - start_time) * 1000, 2)

        result_rows = [dict(zip(columns, row)) for row in rows]

        log_id = log_query(
            question=question,
            sql_query=sql_query,
            execution_time=duration,
            row_count=len(result_rows),
            template_name=template_function.__name__,
            params=params,
            status="success",
            error=None
        )

        return {
            "table": result_rows,
            "summary": f"{len(result_rows)} résultat(s) trouvé(s).",
            "metadata": {
                "template": template_function.__name__,
                "duration_ms": duration,
                "row_count": len(result_rows),
                "params": params,
                "logs_id": log_id
            }
        }

    except Exception as e:

        duration = round((time.time() - start_time) * 1000, 2)

        log_id = log_query(
            question=question,
            sql_query=sql_query,
            execution_time=duration,
            row_count=0,
            template_name=template_function.__name__,
            params=params,
            status="error",
            error=str(e)
        )

        return {
            "table": [],
            "summary": "Erreur lors de l'exécution.",
            "metadata": {
                "template": template_function.__name__,
                "duration_ms": duration,
                "row_count": 0,
                "params": params,
                "error": str(e),
                "logs_id": log_id
            }
        }