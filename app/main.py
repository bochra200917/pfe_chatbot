# app/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from app.chatbot import match_question
from app.db import execute_query
from app.logger import log_query
import time

app = FastAPI()

class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(request: QuestionRequest):

    start_time = time.time()

    template_function, params = match_question(request.question)

    if not template_function:
        return {
            "table": [],
            "summary": "Question non reconnue. Exemples supportés : factures entre dates, total ventes mois, factures non payées...",
            "metadata": {
                "template": None,
                "duration_ms": 0,
                "row_count": 0,
                "params": {},
                "logs_id": None
            }
        }

    sql_query = template_function()

    try:
        columns, rows = execute_query(sql_query, params)

        duration = round((time.time() - start_time) * 1000, 2)

        result_rows = [dict(zip(columns, row)) for row in rows]

        log_id = log_query(
            question=request.question,
            sql_query=sql_query,
            execution_time=duration,
            row_count=len(result_rows),
            template_name=template_function.__name__,
            params=params,
            status="success",
            error=None
        )

        return {
            "table": result_rows,
            "summary": f"{len(result_rows)} résultat(s) trouvé(s).",
            "metadata": {
                "template": template_function.__name__,
                "duration_ms": duration,
                "row_count": len(result_rows),
                "params": params,
                "logs_id": log_id
            }
        }

    except Exception as e:

        duration = round((time.time() - start_time) * 1000, 2)

        log_id = log_query(
            question=request.question,
            sql_query=sql_query,
            execution_time=duration,
            row_count=0,
            template_name=template_function.__name__,
            params=params,
            status="error",
            error=str(e)
        )

        return {
            "table": [],
            "summary": "Erreur lors de l'exécution.",
            "metadata": {
                "template": template_function.__name__,
                "duration_ms": duration,
                "row_count": 0,
                "params": params,
                "error": str(e),
                "logs_id": log_id
            }
        }