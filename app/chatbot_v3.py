# app/chatbot_v3.py
from app.llm_client import call_llm
from app.llm_prompt import build_prompt
from app.llm_parser import parse_llm_json
from app.sql_builder import build_sql
from app.db import execute_query
from app.sql_security import validate_sql_query, detect_injection, enforce_limit
from app.logger import log_query
from app.db_whitelist import ALLOWED_COLUMNS
import time

def validate_filters(filters):

    if not isinstance(filters, dict):
        raise ValueError("Invalid filters format")

    clean = {}

    for key, value in filters.items():

        if not isinstance(key, str):
            raise ValueError("Invalid filter key")

        # vérifier que la colonne existe dans la whitelist
        column_allowed = False

        for table_columns in ALLOWED_COLUMNS.values():
            if key in table_columns:
                column_allowed = True
                break

        if not column_allowed:
            raise ValueError(f"Unauthorized filter column: {key}")

        if isinstance(value, str):

            if len(value) > 100:
                raise ValueError("Filter value too long")

            clean[key] = value

        elif isinstance(value, (int, float)):
            clean[key] = value

        else:
            raise ValueError("Invalid filter value")

    return clean

def run_llm_pipeline(question: str):

    start = time.time()

    # détection injection dans question
    detect_injection(question)

    prompt = build_prompt(question)

    llm_response = call_llm(prompt)

    parsed = parse_llm_json(llm_response)

    filters = parsed.filters if parsed.filters else {}

    params = validate_filters(filters)

    sql = build_sql(parsed)

    # validation SQL AST
    validate_sql_query(sql)

    # enforcement LIMIT
    sql = enforce_limit(sql)

    columns, rows, execution_time = execute_query(sql, params)

    result = [dict(zip(columns, r)) for r in rows]

    log_query(
        question=question,
        sql_query=sql,
        execution_time=execution_time,
        row_count=len(rows),
        template_name=parsed.intent,
        params=params,
        status="success"
    )

    return {
        "table": result,
        "metadata": {
            "template": parsed.intent,
            "row_count": len(rows),
            "duration_ms": execution_time,
            "params": params
        }
    }