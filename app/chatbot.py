# chatbot.py

from app.db import execute_query
from app.templates_sql import (
    get_factures_between,
    get_clients_multiple_commandes,
    get_produits_stock_faible,
    get_factures_negatives,
    get_chiffre_affaires_mois,
    get_factures_par_client
)
from app.logger import log_query

import re
import time

FR_MONTHS = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12
}

def execute_and_log(question, sql, params):
    start_time = time.time()
    try:
        columns, rows = execute_query(sql, params)
        execution_time = round(time.time() - start_time, 4)

        log_query(
            question=question,
            sql_query=sql,
            execution_time=execution_time,
            row_count=len(rows),
            status="success"
        )

        table = [dict(zip(columns, row)) for row in rows]

        return table, len(rows)

    except Exception as e:
        execution_time = round(time.time() - start_time, 4)
        log_query(
            question=question,
            sql_query=sql,
            execution_time=execution_time,
            row_count=0,
            status="error"
        )
        return None, str(e)


def get_response(question):
    question_lower = question.lower()

    # Factures entre dates
    match_dates = re.search(r"factures entre (\d{4}-\d{2}-\d{2}) et (\d{4}-\d{2}-\d{2})", question_lower)
    if match_dates:
        start_date, end_date = match_dates.groups()
        sql = get_factures_between()
        table, count = execute_and_log(question, sql, {
            "start_date": start_date,
            "end_date": end_date
        })
        return {"table": table, "summary": f"{count} factures entre {start_date} et {end_date}"}

    # Factures par client
    match_client = re.search(r"factures pour le client (.+)", question_lower)
    if match_client:
        client_name = match_client.group(1).strip()
        sql = get_factures_par_client()
        table, count = execute_and_log(question, sql, {
            "client": client_name
        })
        return {"table": table, "summary": f"{count} factures pour le client {client_name}"}

    # Factures négatives
    if "total_ht négatif" in question_lower:
        sql = get_factures_negatives()
        table, count = execute_and_log(question, sql, {})
        return {"table": table, "summary": f"{count} factures avec total_ht négatif"}

    # Clients multi commandes
    if "clients ayant plus" in question_lower:
        sql = get_clients_multiple_commandes()
        table, count = execute_and_log(question, sql, {"min_commandes": 1})
        return {"table": table, "summary": f"{count} clients trouvés"}

    # Produits stock faible
    if "produits stock faible" in question_lower:
        sql = get_produits_stock_faible()
        table, count = execute_and_log(question, sql, {"stock_min": 5})
        return {"table": table, "summary": f"{count} produits avec stock faible"}

    # Chiffre d'affaires
    match_ca = re.search(r"total ventes (\w+) (\d{4})", question_lower)
    if match_ca:
        month_str, year = match_ca.groups()
        month = FR_MONTHS.get(month_str.lower())
        if not month:
            return {"error": "Mois non reconnu"}

        sql = get_chiffre_affaires_mois()
        table, count = execute_and_log(question, sql, {
            "year": int(year),
            "month": month
        })
        return {"table": table, "summary": f"Total ventes pour {month_str} {year}"}

    return {"error": "Question non reconnue"}