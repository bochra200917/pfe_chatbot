# app/main.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from app.chatbot import get_response
from app.audit import get_audit_dashboard
from app.summarizer import generate_summary
import secrets
import os

app = FastAPI()

security = HTTPBasic()

USERNAME = os.getenv("API_USER", "admin")
PASSWORD = os.getenv("API_PASS", "secret")


def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


class QuestionRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(request: QuestionRequest, user: str = Depends(authenticate)):

    # Récupération de la réponse brute du chatbot
    response = get_response(request.question)

    # Extraction des éléments nécessaires
    template_name = response.get("metadata", {}).get("template")
    row_count = response.get("metadata", {}).get("row_count", 0)

    # Génération du résumé via summarizer.py
    summary = generate_summary(template_name, row_count)

    # Remplacement du résumé dans la réponse finale
    response["summary"] = summary

    return response


@app.get("/audit")
def audit_dashboard(user: str = Depends(authenticate)):
    return get_audit_dashboard()