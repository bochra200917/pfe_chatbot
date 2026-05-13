# app/main.py — version mise à jour avec /predict + /feedback + /learning
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
from app.chatbot import get_response
from app.audit import get_audit_dashboard
from app.summarizer import generate_summary
from app.cache import chatbot_cache
from app.predictor import (
    predict_ca_next_month,
    predict_stock_alert,
    compute_loyalty_score,
    get_learning_insights,
    get_improvement_candidates
)
import secrets
import os
import json
from datetime import datetime
from dotenv import load_dotenv

app = FastAPI(
    title="Chatbot ZAI Informatique — API",
    description="API NL2SQL sécurisée pour Dolibarr",
    version="3.1.0"
)

from app.db import warmup_pool

security = HTTPBasic()
load_dotenv()

USERNAME = os.getenv("API_USER", "admin")
PASSWORD = os.getenv("API_PASS", "secret")
FEEDBACK_FILE = "logs/feedback.jsonl"


def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    ok_u = secrets.compare_digest(credentials.username, USERNAME)
    ok_p = secrets.compare_digest(credentials.password, PASSWORD)
    if not (ok_u and ok_p):
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username


# ─────────────────────────────────────────────
# Modèles Pydantic
# ─────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str


class PredictRequest(BaseModel):
    template: str
    params: dict = {}
    data: list = []  # données historiques optionnelles


class FeedbackRequest(BaseModel):
    logs_id: str
    question: str
    rating: str             # "positive" | "negative"
    comment: Optional[str] = ""


# ─────────────────────────────────────────────
# Endpoints existants
# ─────────────────────────────────────────────

@app.post("/ask")
def ask(request: QuestionRequest, user: str = Depends(authenticate)):

    print("\n==============================")
    print("QUESTION RECUE =", request.question)
    print("==============================\n")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    if len(request.question) > 500:
        raise HTTPException(status_code=400, detail="Question trop longue")

    try:
        response = get_response(request.question)

        print("\n========= RESPONSE =========")
        print(response)
        print("============================\n")

        metadata = response.get("metadata", {})
        status   = metadata.get("status", "")

        print("METADATA =", metadata)
        print("STATUS =", status)

        if status not in ["rejected", "clarification_required", "error"]:

            template_name = metadata.get("template", "unknown")
            row_count     = metadata.get("row_count", 0)
            from_cache    = metadata.get("from_cache", False)

            print("TEMPLATE =", template_name)
            print("ROW COUNT =", row_count)

            summary = generate_summary(template_name, row_count)

            if from_cache:
                summary += " (cache)"

            response["summary"] = summary

        return response

    except Exception as e:

        print("\n========= ERREUR =========")
        print(str(e))
        print("==========================\n")

        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/audit")
def audit_dashboard(user: str = Depends(authenticate)):
    return get_audit_dashboard()


@app.get("/cache/stats")
def cache_stats(user: str = Depends(authenticate)):
    from app.db import get_pool_stats
    return {
        **chatbot_cache.get_stats(),
        "db_pool": get_pool_stats()
    }

@app.post("/cache/clear")
def cache_clear(user: str = Depends(authenticate)):
    chatbot_cache.invalidate()
    return {"message": "Cache vidé avec succès"}


@app.get("/health")
def health():
    return {"status": "ok", "version": "3.1.0", "timestamp": datetime.now().isoformat()}


# ─────────────────────────────────────────────
# Nouvel endpoint : /predict
# ─────────────────────────────────────────────

@app.post("/predict")
def predict(request: PredictRequest, user: str = Depends(authenticate)):
    """
    Analyse prédictive selon le template.
    - get_total_ventes_mois   → prévision CA mois suivant
    - get_produits_stock_faible → alertes rupture prévue
    - get_clients_multiple_commandes → scores fidélité
    """
    template = request.template
    data     = request.data

    if template == "get_total_ventes_mois":
        if not data:
            return {"error": "Données historiques requises (champ 'data')"}
        return predict_ca_next_month(data)

    elif template == "get_produits_stock_faible":
        if not data:
            return {"error": "Données stock requises (champ 'data')"}
        return {"alerts": predict_stock_alert(data)}

    elif template == "get_clients_multiple_commandes":
        if not data:
            return {"error": "Données clients requises (champ 'data')"}
        return {"clients": compute_loyalty_score(data)}

    else:
        return {"error": f"Analyse prédictive non disponible pour le template '{template}'"}


# ─────────────────────────────────────────────
# Nouvel endpoint : /feedback
# ─────────────────────────────────────────────

@app.post("/feedback")
def submit_feedback(request: FeedbackRequest, user: str = Depends(authenticate)):
    """
    Enregistre le feedback utilisateur (✓ / ✗) pour l'apprentissage continu.
    """
    if request.rating not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="rating doit être 'positive' ou 'negative'")

    os.makedirs("logs", exist_ok=True)

    entry = {
        "timestamp": datetime.now().isoformat(),
        "logs_id":   request.logs_id,
        "question":  request.question,
        "rating":    request.rating,
        "comment":   request.comment or ""
    }

    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"message": "Feedback enregistré", "logs_id": request.logs_id}


# ─────────────────────────────────────────────
# Nouvel endpoint : /learning
# ─────────────────────────────────────────────

@app.get("/learning")
def learning_insights(user: str = Depends(authenticate)):
    """
    Analyse les feedbacks pour identifier les axes d'amélioration.
    Retourne : taux satisfaction, questions problématiques, suggestions.
    """
    return get_learning_insights()


@app.get("/learning/candidates")
def learning_candidates(user: str = Depends(authenticate)):
    """
    Retourne les questions négatives candidates à intégrer au golden set.
    """
    return {"candidates": get_improvement_candidates()}

@app.get("/analytics")
def analytics(user: str = Depends(authenticate)):
    """Analytics complètes sur les requêtes utilisateurs."""
    from app.analytics import get_analytics
    return get_analytics()

# ─────────────────────────────────────────────
# Nouvel endpoint : /execute
# ─────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    sql: str

@app.post("/reload")
def reload_templates(user: str = Depends(authenticate)):
    """Recharge les templates depuis templates.json sans redémarrer."""
    from app.chatbot import reload_templates as _reload
    _reload()
    return {"status": "reloaded", "timestamp": datetime.now().isoformat()}

@app.post("/execute")
def execute_sql(request: ExecuteRequest, user: str = Depends(authenticate)):
    """
    Exécute un SQL généré par le moteur hybride (LLM).
    Sécurisé : validation SELECT-only + whitelist avant exécution.
    """
    from app.sql_security import validate_sql_query, enforce_limit
    from app.db import execute_query

    if not request.sql:
        raise HTTPException(status_code=400, detail="SQL vide reçu")

    print("SQL reçu:", request.sql)
    print("REQUEST BODY:", request.dict())
    
    sql = request.sql.strip()
    # Validation sécurité
    try:
        validate_sql_query(sql)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL invalide : {str(e)}")

    # Enforce LIMIT
    sql = enforce_limit(sql, 200)

    # Exécution
    try:
        columns, rows, execution_time = execute_query(sql, {})
        result_rows = [dict(zip(columns, row)) for row in rows]
        return {
            "rows":           result_rows,
            "row_count":      len(result_rows),
            "execution_time": execution_time,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur exécution : {str(e)}")
    
@app.on_event("startup")
async def startup_event():
    """Pré-charge le pool de connexions au démarrage de l'API."""
    warmup_pool()