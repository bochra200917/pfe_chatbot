# main.py
from fastapi import FastAPI, HTTPException
from app.db import execute_query
from app.templates_sql import get_factures_between

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Chatbot API is running"}

@app.get("/factures")
def get_factures(start_date: str, end_date: str):
    try:
        sql = get_factures_between(start_date, end_date)
        columns, rows = execute_query(sql)
        results = [dict(zip(columns, row)) for row in rows]
        return {"count": len(results), "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))