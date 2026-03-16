# tests/test_pydantic.py
# Tests unitaires pour la validation Pydantic (LLMQuery + ChatbotResponse)

import pytest
from pydantic import ValidationError
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models_v3 import LLMQuery, ChatbotResponse


# ─────────────────────────────────────────────────────────────
# LLMQuery — cas valides
# ─────────────────────────────────────────────────────────────

def test_llmquery_valid_no_filters():
    """Intent valide sans filtres"""
    q = LLMQuery(
        intent="get_factures_non_payees",
        tables=["m38h_facture"],
        columns=[],
        filters={},
        limit=100
    )
    assert q.intent == "get_factures_non_payees"
    assert q.limit == 100

def test_llmquery_valid_with_filters():
    """Intent valide avec filtres client"""
    q = LLMQuery(
        intent="get_factures_par_client",
        tables=["m38h_facture"],
        columns=["ref", "total_ht"],
        filters={"client": "mondher"},
        limit=50
    )
    assert q.filters["client"] == "mondher"
    assert q.limit == 50

def test_llmquery_valid_dates():
    """Intent valide avec filtres dates"""
    q = LLMQuery(
        intent="get_factures_between",
        tables=["m38h_facture"],
        columns=["ref", "datef"],
        filters={"start_date": "2026-01-01", "end_date": "2026-02-28"},
        limit=100
    )
    assert q.filters["start_date"] == "2026-01-01"
    assert q.filters["end_date"] == "2026-02-28"

def test_llmquery_valid_stock():
    """Intent valide avec seuil stock"""
    q = LLMQuery(
        intent="get_produits_stock_faible",
        tables=["m38h_product"],
        columns=["ref", "label", "stock"],
        filters={"stock_min": 5},
        limit=100
    )
    assert q.filters["stock_min"] == 5

def test_llmquery_valid_ventes_mois():
    """Intent valide avec année et mois"""
    q = LLMQuery(
        intent="get_total_ventes_mois",
        tables=["m38h_facture"],
        columns=[],
        filters={"year": "2026", "month": "01"},
        limit=100
    )
    assert q.filters["year"] == "2026"
    assert q.filters["month"] == "01"

def test_llmquery_all_intents_valid():
    """Tous les 8 intents doivent être acceptés"""
    valid_intents = [
        "get_factures_between",
        "get_factures_par_client",
        "get_factures_non_payees",
        "get_factures_partiellement_payees",
        "get_factures_negatives",
        "get_clients_multiple_commandes",
        "get_produits_stock_faible",
        "get_total_ventes_mois",
    ]
    for intent in valid_intents:
        q = LLMQuery(
            intent=intent,
            tables=["m38h_facture"],
            columns=[],
            filters={},
            limit=100
        )
        assert q.intent == intent


# ─────────────────────────────────────────────────────────────
# LLMQuery — cas invalides
# ─────────────────────────────────────────────────────────────

def test_llmquery_invalid_intent():
    """Intent inconnu doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        LLMQuery(
            intent="get_all_data",
            tables=["m38h_facture"],
            columns=[],
            filters={},
            limit=100
        )

def test_llmquery_empty_intent():
    """Intent vide doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        LLMQuery(
            intent="",
            tables=["m38h_facture"],
            columns=[],
            filters={},
            limit=100
        )

def test_llmquery_limit_too_high():
    """Limit > 100 doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        LLMQuery(
            intent="get_factures_non_payees",
            tables=["m38h_facture"],
            columns=[],
            filters={},
            limit=500
        )

def test_llmquery_limit_zero():
    """Limit = 0 doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        LLMQuery(
            intent="get_factures_non_payees",
            tables=["m38h_facture"],
            columns=[],
            filters={},
            limit=0
        )

def test_llmquery_missing_intent():
    """Champ intent manquant doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        LLMQuery(
            tables=["m38h_facture"],
            columns=[],
            filters={},
            limit=100
        )

def test_llmquery_missing_tables():
    """Champ tables manquant doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        LLMQuery(
            intent="get_factures_non_payees",
            columns=[],
            filters={},
            limit=100
        )

def test_llmquery_sql_injection_in_filters():
    """Les filtres contenant du SQL brut ne doivent pas passer la validation intent"""
    with pytest.raises(ValidationError):
        LLMQuery(
            intent="DROP TABLE m38h_facture",
            tables=["m38h_facture"],
            columns=[],
            filters={},
            limit=100
        )

def test_llmquery_too_many_columns():
    """Plus de 10 colonnes doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        LLMQuery(
            intent="get_factures_non_payees",
            tables=["m38h_facture"],
            columns=["c1","c2","c3","c4","c5","c6","c7","c8","c9","c10","c11"],
            filters={},
            limit=100
        )


# ─────────────────────────────────────────────────────────────
# ChatbotResponse — cas valides
# ─────────────────────────────────────────────────────────────

def test_chatbot_response_success():
    """Réponse succès valide"""
    r = ChatbotResponse(
        table=[{"ref": "F001", "total_ttc": 1000}],
        summary="1 résultat(s) trouvé(s).",
        metadata={
            "template": "get_factures_non_payees",
            "duration_ms": 150.0,
            "row_count": 1,
            "params": {},
            "logs_id": "abc-123",
            "status": "success"
        }
    )
    assert r.summary == "1 résultat(s) trouvé(s)."
    assert len(r.table) == 1

def test_chatbot_response_rejected():
    """Réponse rejet valide"""
    r = ChatbotResponse(
        table=[],
        summary="Requête rejetée pour des raisons de sécurité.",
        metadata={"status": "rejected"}
    )
    assert r.metadata["status"] == "rejected"
    assert r.table == []

def test_chatbot_response_clarification():
    """Réponse clarification valide"""
    r = ChatbotResponse(
        table=[],
        summary="Veuillez préciser votre demande.",
        metadata={"status": "clarification_required"}
    )
    assert r.metadata["status"] == "clarification_required"

def test_chatbot_response_empty_table():
    """Table vide est valide"""
    r = ChatbotResponse(
        table=[],
        summary="0 résultat(s) trouvé(s).",
        metadata={"template": "get_factures_non_payees", "row_count": 0}
    )
    assert r.table == []

def test_chatbot_response_missing_summary():
    """Summary manquant doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        ChatbotResponse(
            table=[],
            metadata={"status": "success"}
        )

def test_chatbot_response_missing_metadata():
    """Metadata manquant doit lever une ValidationError"""
    with pytest.raises(ValidationError):
        ChatbotResponse(
            table=[],
            summary="OK"
        )