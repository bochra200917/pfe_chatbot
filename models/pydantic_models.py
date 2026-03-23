# models/pydantic_models.py
# Version : 1.0
# Description : Modèles Pydantic V2 pour la validation des données
#               entrantes et sortantes du système NL2SQL V3.

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any

VALID_INTENTS = [
    "get_factures_between",
    "get_factures_par_client",
    "get_factures_non_payees",
    "get_factures_partiellement_payees",
    "get_factures_negatives",
    "get_clients_multiple_commandes",
    "get_produits_stock_faible",
    "get_total_ventes_mois",
]

VALID_TABLES = [
    "m38h_facture",
    "m38h_societe",
    "m38h_commande",
    "m38h_product",
    "m38h_paiement_facture",
]


# ─────────────────────────────────────────────────────────────
# Requête entrante
# ─────────────────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


# ─────────────────────────────────────────────────────────────
# JSON généré par le LLM
# ─────────────────────────────────────────────────────────────
class LLMQuery(BaseModel):
    intent: str
    tables: List[str] = Field(..., min_length=1, max_length=1)
    columns: List[str] = Field(default=[], max_length=10)
    filters: Dict[str, Any] = Field(default={})
    limit: int = Field(default=100, ge=1, le=100)

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, v):
        if v not in VALID_INTENTS:
            raise ValueError(
                f"Intent '{v}' invalide. Intents valides : {VALID_INTENTS}"
            )
        return v

    @field_validator("tables")
    @classmethod
    def validate_tables(cls, v):
        for table in v:
            if table not in VALID_TABLES:
                raise ValueError(
                    f"Table '{table}' non autorisée. Tables valides : {VALID_TABLES}"
                )
        return v

    @field_validator("columns")
    @classmethod
    def validate_columns_count(cls, v):
        if len(v) > 10:
            raise ValueError("Nombre de colonnes maximum : 10")
        return v


# ─────────────────────────────────────────────────────────────
# Réponse complète du chatbot
# ─────────────────────────────────────────────────────────────
class ChatbotResponse(BaseModel):
    table: List[Dict[str, Any]] = Field(default=[])
    summary: str
    metadata: Dict[str, Any]


# ─────────────────────────────────────────────────────────────
# Dashboard audit
# ─────────────────────────────────────────────────────────────
class AuditResponse(BaseModel):
    total_requests: int
    success_count: int
    error_count: int
    rejected_count: int
    avg_duration_ms: float
    top_templates: List[Dict[str, Any]]
    top_questions: List[Dict[str, Any]]


# ─────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str