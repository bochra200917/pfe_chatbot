# app/sql_security.py
import re

import sqlglot
from sqlglot import exp
from app.db_whitelist import ALLOWED_TABLES, ALLOWED_COLUMNS, ALLOWED_JOINS

class SQLSecurityError(Exception):
    pass

def validate_sql_query(sql: str):

    try:
        parsed = sqlglot.parse_one(sql)
    except Exception:
        raise SQLSecurityError("Invalid SQL syntax")

    # autoriser uniquement SELECT
    if not isinstance(parsed, exp.Select):
        raise SQLSecurityError("Only SELECT allowed")

    # blocage sous-requêtes
    for sub in parsed.find_all(exp.Subquery):
        raise SQLSecurityError("Subqueries not allowed")

    # blocage UNION
    if parsed.find(exp.Union):
        raise SQLSecurityError("UNION not allowed")

    # LIMIT obligatoire
    if parsed.args.get("limit") is None:
        raise SQLSecurityError("LIMIT clause required")

    table_alias_map = {}

    tables = list(parsed.find_all(exp.Table))

    # limiter nombre tables
    if len(tables) > 3:
        raise SQLSecurityError("Too many tables")

    for table in tables:

        table_name = table.name
        alias = table.alias

        if table_name not in ALLOWED_TABLES:
            raise SQLSecurityError(f"Unauthorized table: {table_name}")

        if alias:
            table_alias_map[alias] = table_name

    # validation colonnes
    for column in parsed.find_all(exp.Column):

        col = column.name
        table = column.table

        if table in table_alias_map:
            table = table_alias_map[table]

        if table:

            if table not in ALLOWED_COLUMNS:
                raise SQLSecurityError(f"Unauthorized table reference: {table}")

            if col not in ALLOWED_COLUMNS[table]:
                raise SQLSecurityError(
                    f"Unauthorized column {col} in table {table}"
                )

    # validation JOIN
    for join in parsed.find_all(exp.Join):

        left = join.this
        right = join.args.get("expression")

        if isinstance(left, exp.Table) and isinstance(right, exp.Table):

            pair = (left.name, right.name)

            if pair not in ALLOWED_JOINS and pair[::-1] not in ALLOWED_JOINS:
                raise SQLSecurityError(f"Unauthorized join {pair}")

def enforce_limit(sql: str, max_limit: int = 100):

    sql_clean = sql.strip().rstrip(";")
    sql_lower = sql_clean.lower()

    if "limit" in sql_lower:

        try:

            limit_part = sql_lower.split("limit")[1].strip()
            limit_value = int(limit_part.split()[0])

            if limit_value > max_limit:

                sql_clean = sql_clean.split("LIMIT")[0]
                sql_clean += f" LIMIT {max_limit}"

        except Exception:

            sql_clean = sql_clean.split("LIMIT")[0]
            sql_clean += f" LIMIT {max_limit}"

        return sql_clean

    # ajouter LIMIT si absent
    return sql_clean + f" LIMIT {max_limit}"


FORBIDDEN_KEYWORDS = [
    ";",
    "--",
    "/*",
    "*/",
    " drop ",
    " delete ",
    " update ",
    " insert ",
    " alter ",
    " truncate ",
    " union ",
    " union select ",
    " or 1=1",
    " or '1'='1'",
    " or \"1\"=\"1\"",
    " sleep(",
    " benchmark(",
    " information_schema",
    " load_file(",
]

def detect_injection(text: str):

    lower = text.lower()

    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(r'^\s*SELECT\b', text.strip(), re.IGNORECASE):
            raise ValueError("Raw SQL query detected")

        if keyword in lower:
            raise SQLSecurityError("Potential SQL injection detected")