#app/sql_builder.py
from app.db_whitelist import ALLOWED_TABLES, ALLOWED_COLUMNS


def build_sql(query):

    table = query.tables[0]

    if table not in ALLOWED_TABLES:
        raise Exception("Unauthorized table")

    columns = query.columns

    if columns == ["*"]:
        columns_sql = "*"
    else:
        columns_sql = ", ".join(columns)

    sql = f"SELECT {columns_sql} FROM {table}"

    if query.filters:

        conditions = []

        for key, value in query.filters.items():

            if key not in ALLOWED_COLUMNS[table]:
                raise Exception("Unauthorized column")

            conditions.append(f"{key} = :{key}")

        where = " AND ".join(conditions)

        sql += f" WHERE {where}"

    sql += f" LIMIT {query.limit}"

    return sql