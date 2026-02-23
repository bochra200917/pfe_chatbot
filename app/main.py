from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os

from app.db import execute_query
from app.chatbot import get_response
from app.templates_sql import get_factures_between

app = FastAPI(title="Chatbot SQL API", version="1.0")

# -----------------------------
# MODELS
# -----------------------------

class QuestionRequest(BaseModel):
    question: str
    # params retiré pour simplifier Swagger et UX
    # params: dict = {}  # plus nécessaire

class SQLRequest(BaseModel):
    sql: str
    params: dict = {}  # nécessaire pour debug SQL

# -----------------------------
# ROOT
# -----------------------------

@app.get("/")
def root():
    return {"message": "Chatbot API is running"}

# -----------------------------
# HEALTH CHECK
# -----------------------------

@app.get("/health")
def health_check():
    """
    Vérifie la connexion à la base de données.
    """
    try:
        execute_query("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

# -----------------------------
# CHATBOT ROUTE
# -----------------------------

@app.post("/chat")
def chat(request: QuestionRequest):
    """
    Exécute une question via le chatbot.
    """
    result = get_response(request.question)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result

# -----------------------------
# FACTURES ROUTE
# -----------------------------

@app.get("/factures")
def get_factures(start_date: str, end_date: str):
    """
    Récupère les factures entre deux dates.
    """
    try:
        sql = get_factures_between()
        columns, rows = execute_query(sql, {"start_date": start_date, "end_date": end_date})
        results = [dict(zip(columns, row)) for row in rows]

        return {
            "count": len(results),
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------
# DEBUG SQL ROUTE
# -----------------------------

@app.post("/debug-sql")
def debug_sql(request: SQLRequest):
    """
    Exécute une requête SQL brute (lecture uniquement).
    """
    try:
        columns, rows = execute_query(request.sql, request.params)
        results = [dict(zip(columns, row)) for row in rows]

        return {
            "count": len(results),
            "data": results
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------
# LOG VIEWER
# -----------------------------

@app.get("/logs")
def get_logs(limit: int = 50):
    """
    Retourne les dernières entrées du fichier de logs.
    """
    log_file = "chatbot_logs.json"

    if not os.path.exists(log_file):
        return {"count": 0, "logs": []}

    with open(log_file, "r") as f:
        lines = f.readlines()

    logs = [json.loads(line) for line in lines[-limit:]]

    return {"count": len(logs), "logs": logs}