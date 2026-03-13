# app/chatbot_v3.py
from app.llm_client import call_llm
from app.llm_prompt import build_prompt
from app.llm_parser import parse_llm_json
from app.db import execute_query
from app.sql_security import validate_sql_query, detect_injection, enforce_limit
from app.logger import log_query
from app.templates_sql import TEMPLATE_MAPPING
import time

def run_llm_pipeline(question: str):

    start = time.time()

    # détection injection dans la question
    detect_injection(question)

    # appel LLM → identification de l'intent et extraction des paramètres
    prompt = build_prompt(question)
    llm_response = call_llm(prompt)
    parsed = parse_llm_json(llm_response)

    # routing vers le template existant (pas de SQL libre)
    template_function = TEMPLATE_MAPPING.get(parsed.intent)

    if template_function is None:
        raise ValueError(f"Intent '{parsed.intent}' ne correspond à aucun template connu")

    # récupération du SQL depuis le template (sécurisé)
    sql = template_function()

    # validation SQL + enforcement LIMIT
    validate_sql_query(sql)
    sql = enforce_limit(sql)

    # exécution avec les paramètres extraits par le LLM
    params = parsed.filters if parsed.filters else {}
    columns, rows, execution_time = execute_query(sql, params)

    result = [dict(zip(columns, r)) for r in rows]

    duration = round((time.time() - start) * 1000, 2)

    log_query(
        question=question,
        sql_query=sql,
        execution_time=duration,
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
            "duration_ms": duration,
            "params": params
        }
    }