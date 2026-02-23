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


def get_response(question, params={}):
    question_lower = question.lower()

    # Factures entre deux dates
    match_dates = re.search(r"factures entre (\d{4}-\d{2}-\d{2}) et (\d{4}-\d{2}-\d{2})", question_lower)
    if match_dates:
        start_date = match_dates.group(1)
        end_date = match_dates.group(2)
        sql = get_factures_between()
        columns, rows = execute_query(sql, {"start_date": start_date, "end_date": end_date})
        response_table = [dict(zip(columns, row)) for row in rows]
        return {"table": response_table, "summary": f"{len(rows)} factures entre {start_date} et {end_date}"}

    # Factures pour un client spécifique
    match_client = re.search(r"factures pour le client (.+)", question_lower)
    if match_client:
        client_name = match_client.group(1).strip()
        sql = get_factures_par_client()
        columns, rows = execute_query(sql, {"client": client_name})
        response_table = [dict(zip(columns, row)) for row in rows]
        return {"table": response_table, "summary": f"{len(rows)} factures pour le client {client_name}"}

    # Factures avec total_ht négatif
    if "total_ht négatif" in question_lower:
        sql = get_factures_negatives()
        columns, rows = execute_query(sql, {})
        response_table = [dict(zip(columns, row)) for row in rows]
        return {"table": response_table, "summary": f"{len(rows)} factures avec total_ht négatif"}

    # Clients ayant plus de N commandes
    if "clients ayant plus" in question_lower:
        sql = get_clients_multiple_commandes()
        columns, rows = execute_query(sql, {"min_commandes": params.get("min_commandes", 1)})
        response_table = [dict(zip(columns, row)) for row in rows]
        return {"table": response_table, "summary": f"{len(rows)} clients trouvés"}

    # Produits avec stock faible
    if "produits stock faible" in question_lower:
        sql = get_produits_stock_faible()
        columns, rows = execute_query(sql, {"stock_min": params.get("stock_min", 5)})
        response_table = [dict(zip(columns, row)) for row in rows]
        return {"table": response_table, "summary": f"{len(rows)} produits avec stock faible"}

    # Chiffre d’affaires d’un mois
    match_ca = re.search(r"total ventes (\w+) (\d{4})", question_lower)
    if match_ca:
        month_str, year = match_ca.groups()
        year = int(year)
        month = FR_MONTHS.get(month_str.lower())
        if month is None:
            return {"error": f"Mois inconnu : {month_str}"}

        sql = get_chiffre_affaires_mois()
        columns, rows = execute_query(sql, {"month": month, "year": year})
        if not rows:
            return {"table": [], "summary": f"Aucune vente pour {month_str} {year}"}
        response_table = [dict(zip(columns, row)) for row in rows]
        return {"table": response_table, "summary": f"Total ventes pour {month_str} {year}"}

    # Facture non reconnue
    return {"error": "Question non reconnue"}