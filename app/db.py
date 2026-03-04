# app/db.py
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import re
import sqlglot
from sqlglot import exp

from app.db_whitelist import (
    ALLOWED_TABLES,
    ALLOWED_COLUMNS,
    ALLOWED_JOINS
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL non définie")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

# -------------------------
# Validation SQL avancée AST
# -------------------------

def validate_sql_ast(sql_query: str):

    try:
        parsed = sqlglot.parse_one(sql_query)
    except Exception:
        raise Exception("SQL invalide (parsing AST échoué)")

    # 1️⃣ SELECT uniquement
    if not isinstance(parsed, exp.Select):
        raise Exception("Seules les requêtes SELECT sont autorisées.")

    # 2️⃣ Vérification tables
    tables = {t.name for t in parsed.find_all(exp.Table)}
    for table in tables:
        if table not in ALLOWED_TABLES:
            raise Exception(f"Table non autorisée : {table}")

    # 3️⃣ Vérification colonnes
    for column in parsed.find_all(exp.Column):
        table = column.table
        col = column.name

        if table:
            if table not in ALLOWED_COLUMNS:
                raise Exception(f"Table colonne non autorisée : {table}")

            if col not in ALLOWED_COLUMNS[table]:
                raise Exception(f"Colonne non autorisée : {table}.{col}")

    # 4️⃣ Vérification jointures
    for join in parsed.find_all(exp.Join):
        left = join.this
        right = join.args.get("expression")

        if isinstance(left, exp.Table) and isinstance(right, exp.Table):
            pair = (left.name, right.name)
            reverse_pair = (right.name, left.name)

            if pair not in ALLOWED_JOINS and reverse_pair not in ALLOWED_JOINS:
                raise Exception(
                    f"Jointure non autorisée entre {left.name} et {right.name}"
                )

    return True


# -------------------------
# Exécution sécurisée
# -------------------------

def execute_query(sql_query: str, params: dict = None, limit: int = 200):

    if params is None:
        params = {}

    # AST validation
    validate_sql_ast(sql_query)

    # LIMIT automatique
    if "limit" not in sql_query.lower():
        sql_query += f"\nLIMIT {limit}"

    try:
        with engine.connect() as connection:

            # Statement timeout (5 sec)
            connection.execute(text("SET SESSION max_statement_time=5"))
            result = connection.execute(text(sql_query), params)
            rows = result.fetchall()
            columns = result.keys()

            if len(rows) > limit:
                raise Exception("Nombre de lignes dépasse la limite autorisée.")

            return columns, rows

    except Exception as e:
        raise Exception(f"Erreur DB sécurisée : {str(e)}")