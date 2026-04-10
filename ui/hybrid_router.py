"""
hybrid_router.py
Endpoint FastAPI — Mode hybride NL2SQL
Chatbot Dolibarr — PFE Bochra Ben Yedder

Lancement : uvicorn hybrid_router:app --host 0.0.0.0 --port 8001 --reload
"""

import logging
import uuid
import os
import json
import statistics
from collections import Counter
from datetime import datetime
from typing import Optional
from pathlib import Path

from dotenv import load_dotenv

# Charge le .env depuis la racine du projet (un niveau au-dessus de /ui)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from hybrid_engine import HybridEngine, HybridResult, validate_sql_security

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Fichier de logs hybride ──────────────────────────────────────────────────
HYBRID_LOGS_FILE = "logs/hybrid_requests.jsonl"


def log_hybrid_request(result: HybridResult, request_id: str):
    """Persiste chaque requête hybride dans un fichier JSONL pour audit et analytics."""
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp":   result.timestamp,
        "request_id":  request_id,
        "question":    result.question,
        "mode":        result.mode,
        "intent":      result.intent,
        "sql":         result.sql,
        "valid":       result.valid,
        "llm_called":  result.llm_called,
        "duration_ms": result.duration_ms,
        "error":       result.error,
        "warning":     result.warning,
    }
    with open(HYBRID_LOGS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_hybrid_logs() -> list:
    """Charge tous les logs hybrides depuis le fichier JSONL."""
    if not os.path.exists(HYBRID_LOGS_FILE):
        return []
    logs = []
    with open(HYBRID_LOGS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except Exception:
                    pass
    return logs


# ─── App FastAPI ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Chatbot Dolibarr — API Hybride NL2SQL",
    description=(
        "Mode hybride : Templates V1/V2 d'abord, "
        "Claude (Anthropic) en fallback pour routing et génération SQL."
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Instance moteur (singleton) ──────────────────────────────────────────────
engine = HybridEngine(templates_file="templates.json")

# ─── Schémas Pydantic ─────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500, description="Question en langage naturel")
    force_llm: bool = Field(False, description="Forcer le passage par le LLM (ignorer templates)")


class AskResponse(BaseModel):
    request_id: str
    question: str
    mode: str
    intent: Optional[str]
    sql: Optional[str]
    params: dict
    valid: bool
    llm_called: bool
    duration_ms: float
    timestamp: str
    warning: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    templates_loaded: int
    active_templates: int
    timestamp: str


class ReloadResponse(BaseModel):
    status: str
    templates_loaded: int
    timestamp: str


class ValidateSQLRequest(BaseModel):
    sql: str = Field(..., description="Requête SQL à valider")


class ValidateSQLResponse(BaseModel):
    valid: bool
    message: str


# ─── Middleware de logging HTTP ────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.now()
    response = await call_next(request)
    duration = (datetime.now() - start).total_seconds() * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration:.1f}ms)"
    )
    return response


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health():
    """Vérifie que l'API est opérationnelle et retourne les stats des templates."""
    templates = engine.templates
    active = sum(1 for t in templates.values() if t.get("active", True))
    return HealthResponse(
        status="ok",
        templates_loaded=len(templates),
        active_templates=active,
        timestamp=datetime.now().isoformat(),
    )


@app.post("/ask", response_model=AskResponse, tags=["NL2SQL"])
def ask(request: AskRequest):
    """
    Point d'entrée principal.

    Stratégie :
    1. Matching templates V1/V2 (regex + mots-clés)
    2. Si échec → LLM Claude : classifier l'intent et extraire les params
    3. Si question complexe → LLM Claude : générer le SQL directement
    4. Validation AST (sqlglot) avant tout retour
    5. Log persistant de chaque requête pour audit et analytics
    """
    request_id = str(uuid.uuid4())[:8]

    # Forcer LLM si demandé
    if request.force_llm:
        engine_templates_backup = engine.templates.copy()
        engine.templates = {}

    try:
        result = engine.process(request.question)
    finally:
        if request.force_llm:
            engine.templates = engine_templates_backup

    # ── Log persistant ────────────────────────────────────────────────────────
    log_hybrid_request(result, request_id)

    logger.info(
        f"[{request_id}] mode={result.mode} | "
        f"intent={result.intent} | valid={result.valid} | "
        f"llm={result.llm_called} | {result.duration_ms}ms"
    )

    return AskResponse(
        request_id=request_id,
        question=result.question,
        mode=result.mode,
        intent=result.intent,
        sql=result.sql,
        params=result.params,
        valid=result.valid,
        llm_called=result.llm_called,
        duration_ms=result.duration_ms,
        timestamp=result.timestamp,
        warning=result.warning,
        error=result.error,
    )


@app.post("/reload", response_model=ReloadResponse, tags=["Admin"])
def reload_templates():
    """Recharge les templates depuis templates.json sans redémarrer l'API."""
    engine.reload_templates()
    logger.info(f"Templates rechargés : {len(engine.templates)} templates")
    return ReloadResponse(
        status="reloaded",
        templates_loaded=len(engine.templates),
        timestamp=datetime.now().isoformat(),
    )


@app.post("/validate-sql", response_model=ValidateSQLResponse, tags=["Admin"])
def validate_sql(request: ValidateSQLRequest):
    """
    Valide un SQL manuellement (SELECT-only, whitelist tables, AST sqlglot).
    Utile pour tester un SQL avant de l'ajouter dans un template.
    """
    valid, message = validate_sql_security(request.sql)
    return ValidateSQLResponse(valid=valid, message=message)


@app.get("/templates", tags=["Admin"])
def list_templates():
    """Liste tous les templates actifs avec leur intent et leurs paramètres."""
    return {
        tid: {
            "intent":      t.get("intent", tid),
            "description": t.get("description", ""),
            "params":      t.get("params", []),
            "keywords":    t.get("keywords", []),
            "active":      t.get("active", True),
        }
        for tid, t in engine.templates.items()
        if t.get("active", True)
    }


@app.get("/analytics", tags=["Admin"])
def analytics_hybrid():
    """
    Statistiques comportementales sur les requêtes hybrides.
    Utilisé par l'interface admin pour l'onglet Analytics hybride.
    """
    logs = load_hybrid_logs()

    if not logs:
        return {"empty": True}

    total     = len(logs)
    llm_calls = sum(1 for l in logs if l.get("llm_called"))
    tpl_hits  = sum(1 for l in logs if l.get("mode") == "template")
    errors    = sum(1 for l in logs if not l.get("valid"))

    durations        = [l["duration_ms"] for l in logs if "duration_ms" in l]
    durations_sorted = sorted(durations)

    mode_counts   = dict(Counter(l.get("mode")   for l in logs if l.get("mode")))
    intent_counts = dict(Counter(l.get("intent") for l in logs if l.get("intent")))

    # Latence P95 / P99
    def percentile(data: list, pct: float) -> float:
        if not data:
            return 0.0
        idx = max(0, int(len(data) * pct) - 1)
        return round(data[idx], 1)

    latency = {
        "mean_ms":   round(statistics.mean(durations), 1)   if durations else 0,
        "median_ms": round(statistics.median(durations), 1) if durations else 0,
        "p95_ms":    percentile(durations_sorted, 0.95),
        "p99_ms":    percentile(durations_sorted, 0.99),
    }

    # Top 10 questions
    question_counts = dict(Counter(l.get("question", "") for l in logs))
    top_questions   = dict(sorted(question_counts.items(), key=lambda x: -x[1])[:10])

    return {
        "total_requests":        total,
        "llm_call_rate_pct":     round(llm_calls / total * 100, 1),
        "template_hit_rate_pct": round(tpl_hits  / total * 100, 1),
        "error_rate_pct":        round(errors    / total * 100, 1),
        "latency":               latency,
        "mode_distribution":     mode_counts,
        "top_intents":           dict(sorted(intent_counts.items(), key=lambda x: -x[1])[:10]),
        "top_questions":         top_questions,
    }


# ─── Handler erreurs globales ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur non gérée : {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Erreur interne du serveur.", "detail": str(exc)},
    )