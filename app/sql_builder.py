# app/sql_builder.py
from app.db_whitelist import ALLOWED_TABLES, ALLOWED_COLUMNS

def build_sql(parsed):

    tables = parsed.tables
    columns = parsed.columns
    filters = parsed.filters
    limit = parsed.limit or 100

    if not tables:
        raise ValueError("No table specified")

    for t in tables:
        if t not in ALLOWED_TABLES:
            raise ValueError(f"Unauthorized table {t}")

    table = tables[0]

    # colonnes autorisées
    if columns:

        safe_columns = []

        for c in columns:
            if c not in ALLOWED_COLUMNS.get(table, []):
                raise ValueError(f"Unauthorized column {c}")
            safe_columns.append(c)

        column_sql = ", ".join(safe_columns)

    else:
        column_sql = "*"

    sql = f"SELECT {column_sql} FROM {table}"

    if filters:

        conditions = []

        for k in filters.keys():
            conditions.append(f"{k} = %({k})s")

        sql += " WHERE " + " AND ".join(conditions)

    sql += f" LIMIT {limit}"

    return sql