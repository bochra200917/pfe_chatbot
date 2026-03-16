# models/pydantic_models.py
# Version : 1.0
# Description : Modèles Pydantic pour la validation des données
#               entrantes et sortantes du système NL2SQL V3.

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any


# ─────────────────────────────────────────────────────────────
# Intents disponibles (8 templates SQL prédéfinis)
# ─────────────────────────────────────────────────────────────
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

# Tables autorisées (whitelist v1.0)
VALID_TABLES = [
    "m38h_facture",
    "m38h_societe",
    "m38h_commande",
    "m38h_product",
    "m38h_paiement_facture",
]


# ─────────────────────────────────────────────────────────────
# Modèle : requête entrante de l'utilisateur
# ─────────────────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    """Requête entrante via POST /ask"""
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Question en langage naturel posée par l'utilisateur"
    )


# ─────────────────────────────────────────────────────────────
# Modèle : JSON généré par le LLM
# ─────────────────────────────────────────────────────────────
class LLMQuery(BaseModel):
    """
    Contrat JSON produit par le LLM.
    Le LLM identifie uniquement l'intent et les paramètres.
    Il ne génère jamais de SQL directement.
    """
    intent: str = Field(
        ...,
        description="Nom exact du template SQL à utiliser"
    )
    tables: List[str] = Field(
        ...,
        min_items=1,
        max_items=1,
        description="Table principale concernée (une seule autorisée)"
    )
    columns: List[str] = Field(
        default=[],
        max_items=10,
        description="Colonnes pertinentes identifiées"
    )
    filters: Dict[str, Any] = Field(
        default={},
        description="Paramètres extraits de la question"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=100,
        description="Nombre maximum de lignes retournées"
    )

    @validator("intent")
    def validate_intent(cls, v):
        if v not in VALID_INTENTS:
            raise ValueError(
                f"Intent '{v}' invalide. "
                f"Intents valides : {VALID_INTENTS}"
            )
        return v

    @validator("tables")
    def validate_tables(cls, v):
        for table in v:
            if table not in VALID_TABLES:
                raise ValueError(
                    f"Table '{table}' non autorisée. "
                    f"Tables valides : {VALID_TABLES}"
                )
        return v

    @validator("columns")
    def validate_columns_count(cls, v):
        if len(v) > 10:
            raise ValueError("Nombre de colonnes maximum : 10")
        return v


# ─────────────────────────────────────────────────────────────
# Modèle : métadonnées de la réponse
# ─────────────────────────────────────────────────────────────
class ResponseMetadata(BaseModel):
    """Métadonnées retournées avec chaque réponse"""
    template: Optional[str] = Field(
        None,
        description="Nom du template SQL utilisé"
    )
    duration_ms: Optional[float] = Field(
        None,
        description="Durée d'exécution en millisecondes"
    )
    row_count: Optional[int] = Field(
        None,
        description="Nombre de lignes retournées"
    )
    params: Optional[Dict[str, Any]] = Field(
        default={},
        description="Paramètres utilisés dans la requête"
    )
    logs_id: Optional[str] = Field(
        None,
        description="UUID du log d'audit"
    )
    status: Optional[str] = Field(
        None,
        description="Statut : success | rejected | clarification_required | error"
    )
    error: Optional[str] = Field(
        None,
        description="Message d'erreur si status=error"
    )


# ─────────────────────────────────────────────────────────────
# Modèle : réponse complète du chatbot
# ─────────────────────────────────────────────────────────────
class ChatbotResponse(BaseModel):
    """Réponse complète retournée par POST /ask"""
    table: List[Dict[str, Any]] = Field(
        default=[],
        description="Lignes de résultats"
    )
    summary: str = Field(
        ...,
        description="Résumé textuel de la réponse"
    )
    metadata: ResponseMetadata = Field(
        ...,
        description="Métadonnées d'exécution"
    )


# ─────────────────────────────────────────────────────────────
# Modèle : réponse du dashboard d'audit
# ─────────────────────────────────────────────────────────────
class AuditResponse(BaseModel):
    """Réponse du endpoint GET /audit"""
    total_requests: int
    success_count: int
    error_count: int
    rejected_count: int
    avg_duration_ms: float
    top_templates: List[Dict[str, Any]]
    top_questions: List[Dict[str, Any]]


# ─────────────────────────────────────────────────────────────
# Modèle : réponse health check
# ─────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    """Réponse du endpoint GET /health"""
    status: str