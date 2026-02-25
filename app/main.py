# app/main.py

from fastapi import FastAPI
from pydantic import BaseModel
from app.chatbot import get_response
from app.audit import get_audit_dashboard

app = FastAPI()


class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(request: QuestionRequest):
    return get_response(request.question)


@app.get("/audit")
def audit_dashboard():
    return get_audit_dashboard()