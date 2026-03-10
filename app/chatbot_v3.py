# app/chatbot_v3.py
from app.llm_client import call_llm
from app.llm_prompt import build_prompt
from app.llm_parser import parse_llm_json
from app.sql_builder import build_sql
from app.db import execute_query
from app.sql_security import validate_sql_query, detect_injection
from app.logger import log_query
import time


def validate_filters(filters):

    if not isinstance(filters, dict):
        raise ValueError("Invalid filters format")

    clean = {}

    for k, v in filters.items():

        if not isinstance(k, str):
            raise ValueError("Invalid filter key")

        if isinstance(v, (str, int, float)):
            clean[k] = v
        else:
            raise ValueError("Invalid filter value")

    return clean


def run_llm_pipeline(question):

    start = time.time()

    detect_injection(question)

    prompt = build_prompt(question)

    llm_response = call_llm(prompt)

    parsed = parse_llm_json(llm_response)

    params = validate_filters(parsed.filters)

    sql = build_sql(parsed)

    validate_sql_query(sql)

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
            "duration": execution_time,
            "params": params
        }
    }