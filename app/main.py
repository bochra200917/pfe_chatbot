from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from app.chatbot import get_response
from app.audit import get_audit_dashboard
from app.summarizer import generate_summary
import secrets
import os
from dotenv import load_dotenv

app = FastAPI()

security = HTTPBasic()

load_dotenv()

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

    if len(request.question) > 500:
        raise HTTPException(status_code=400, detail="Question trop longue")

    try:

        response = get_response(request.question)

        metadata = response.get("metadata", {})

        template_name = metadata.get("template", "unknown")
        row_count = metadata.get("row_count", 0)

        summary = generate_summary(template_name, row_count)

        response["summary"] = summary

        return response

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/audit")
def audit_dashboard(user: str = Depends(authenticate)):

    return get_audit_dashboard()