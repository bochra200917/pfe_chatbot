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

    if not isinstance(parsed, exp.Select):
        raise SQLSecurityError("Only SELECT allowed")

    # blocage subqueries
    for sub in parsed.find_all(exp.Subquery):
        raise SQLSecurityError("Subqueries not allowed")

    # blocage union
    if parsed.find(exp.Union):
        raise SQLSecurityError("UNION not allowed")

    table_alias_map = {}

    tables = list(parsed.find_all(exp.Table))

    if len(tables) > 3:
        raise SQLSecurityError("Too many tables")

    for table in tables:

        table_name = table.name
        alias = table.alias

        if table_name not in ALLOWED_TABLES:
            raise SQLSecurityError(f"Unauthorized table: {table_name}")

        if alias:
            table_alias_map[alias] = table_name

    for column in parsed.find_all(exp.Column):

        col = column.name
        table = column.table

        if table in table_alias_map:
            table = table_alias_map[table]

        if table and table in ALLOWED_COLUMNS:

            if col not in ALLOWED_COLUMNS[table]:
                raise SQLSecurityError(f"Unauthorized column {col}")

    for join in parsed.find_all(exp.Join):

        left = join.this
        right = join.args.get("expression")

        if isinstance(left, exp.Table) and isinstance(right, exp.Table):

            pair = (left.name, right.name)

            if pair not in ALLOWED_JOINS and pair[::-1] not in ALLOWED_JOINS:
                raise SQLSecurityError(f"Unauthorized join {pair}")


def enforce_limit(sql: str, max_limit: int = 200):

    sql_lower = sql.lower()

    if "limit" in sql_lower:

        try:
            limit_value = int(sql_lower.split("limit")[1].strip().split()[0])

            if limit_value > max_limit:
                sql = sql_lower.split("limit")[0] + f" LIMIT {max_limit}"

        except:
            sql = sql_lower.split("limit")[0] + f" LIMIT {max_limit}"

        return sql

    return sql.strip().rstrip(";") + f" LIMIT {max_limit}"


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
    " or 1=1"
]


def detect_injection(text: str):

    lower = text.lower()

    for keyword in FORBIDDEN_KEYWORDS:

        if keyword in lower:
            raise SQLSecurityError("Potential SQL injection detected")