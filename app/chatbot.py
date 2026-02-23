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
            status="error",
            error=str(e)
        )

        return None, str(e)


def get_response(question, params={}):
    question_lower = question.lower()

    # -----------------------------
    # Factures entre deux dates
    # -----------------------------
    match_dates = re.search(r"factures entre (\d{4}-\d{2}-\d{2}) et (\d{4}-\d{2}-\d{2})", question_lower)
    if match_dates:
        start_date = match_dates.group(1)
        end_date = match_dates.group(2)
        sql = get_factures_between()
        table, count = execute_and_log(question, sql, {"start_date": start_date, "end_date": end_date})
        return {"table": table, "summary": f"{count} factures entre {start_date} et {end_date}"}

    # -----------------------------
    # Factures pour un client spécifique
    # -----------------------------
    match_client = re.search(r"factures pour le client (.+)", question_lower)
    if match_client:
        client_name = match_client.group(1).strip()
        sql = get_factures_par_client()
        table, count = execute_and_log(question, sql, {"client": client_name})
        return {"table": table, "summary": f"{count} factures pour le client {client_name}"}

    # -----------------------------
    # Factures non payées
    # -----------------------------
    if "factures non payées" in question_lower:
        sql = """
        SELECT f.rowid AS facture_id,
               f.ref AS facture_ref,
               s.nom AS client,
               f.total_ttc AS montant_total,
               COALESCE(SUM(p.amount), 0) AS montant_payé,
               f.total_ttc - COALESCE(SUM(p.amount), 0) AS montant_restant
        FROM m38h_facture f
        LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
        LEFT JOIN m38h_paiement_facture pf ON pf.fk_facture = f.rowid
        LEFT JOIN m38h_paiement p ON p.rowid = pf.fk_paiement
        GROUP BY f.rowid, f.ref, s.nom, f.total_ttc
        HAVING montant_restant > 0
        """
        table, count = execute_and_log(question, sql, {})
        return {"table": table, "summary": f"{count} factures non payées"}

    # -----------------------------
    # Factures avec total_ht négatif
    # -----------------------------
    if "total_ht négatif" in question_lower:
        sql = get_factures_negatives()
        table, count = execute_and_log(question, sql, {})
        return {"table": table, "summary": f"{count} factures avec total_ht négatif"}

    # -----------------------------
    # Clients ayant plus de N commandes
    # -----------------------------
    if "clients ayant plus" in question_lower:
        match = re.search(r"plus de (\d+)", question_lower)
        n = int(match.group(1)) if match else 1
        sql = get_clients_multiple_commandes()
        table, count = execute_and_log(question, sql, {"min_commandes": n})
        return {"table": table, "summary": f"{count} clients avec plus de {n} commandes"}

    # -----------------------------
    # Produits avec stock faible
    # -----------------------------
    if "produits stock faible" in question_lower:
        match = re.search(r"(\d+)", question_lower)
        stock_min = int(match.group(1)) if match else 5
        sql = get_produits_stock_faible()
        table, count = execute_and_log(question, sql, {"stock_min": stock_min})
        return {"table": table, "summary": f"{count} produits avec stock < {stock_min}"}

    # -----------------------------
    # Chiffre d’affaires d’un mois
    # -----------------------------
    match_ca = re.search(r"total ventes (\w+) (\d{4})", question_lower)
    if match_ca:
        month_str, year = match_ca.groups()
        year = int(year)
        month = FR_MONTHS.get(month_str.lower())
        if month is None:
            return {"error": f"Mois inconnu : {month_str}"}
        sql = get_chiffre_affaires_mois()
        table, count = execute_and_log(question, sql, {"month": month, "year": year})
        if count == 0:
            return {"table": [], "summary": f"Aucune vente pour {month_str} {year}"}
        return {"table": table, "summary": f"Total ventes pour {month_str} {year}"}

    # -----------------------------
    # Question non reconnue
    # -----------------------------
    return {"error": "Question non reconnue"}