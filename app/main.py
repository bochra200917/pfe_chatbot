# app/main.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from app.chatbot import get_response
from app.audit import get_audit_dashboard
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
    return get_response(request.question)


@app.get("/audit")
def audit_dashboard(user: str = Depends(authenticate)):    
    return get_audit_dashboard()
