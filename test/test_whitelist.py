# tests/test_whitelist.py
# Tests unitaires pour la whitelist (tables, colonnes, jointures)

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db_whitelist import (
    ALLOWED_TABLES,
    ALLOWED_COLUMNS,
    ALLOWED_JOINS,
    WHITELIST_VERSION
)


# ─────────────────────────────────────────────────────────────
# Version
# ─────────────────────────────────────────────────────────────

def test_whitelist_version_exists():
    """La whitelist doit avoir une version définie"""
    assert WHITELIST_VERSION is not None
    assert WHITELIST_VERSION != ""

def test_whitelist_version_format():
    """La version doit suivre le format vX.Y"""
    import re
    assert re.match(r"^v\d+\.\d+$", WHITELIST_VERSION), \
        f"Format de version invalide : {WHITELIST_VERSION}"


# ─────────────────────────────────────────────────────────────
# Tables autorisées
# ─────────────────────────────────────────────────────────────

def test_allowed_tables_not_empty():
    """La liste des tables autorisées ne doit pas être vide"""
    assert len(ALLOWED_TABLES) > 0

def test_allowed_tables_contains_facture():
    assert "m38h_facture" in ALLOWED_TABLES

def test_allowed_tables_contains_societe():
    assert "m38h_societe" in ALLOWED_TABLES

def test_allowed_tables_contains_commande():
    assert "m38h_commande" in ALLOWED_TABLES

def test_allowed_tables_contains_product():
    assert "m38h_product" in ALLOWED_TABLES

def test_allowed_tables_contains_paiement():
    assert "m38h_paiement_facture" in ALLOWED_TABLES

def test_allowed_tables_count():
    """Exactement 5 tables autorisées"""
    assert len(ALLOWED_TABLES) == 5

def test_table_not_allowed_user():
    """Table sensible m38h_user ne doit pas être autorisée"""
    assert "m38h_user" not in ALLOWED_TABLES

def test_table_not_allowed_salary():
    """Table sensible m38h_salary ne doit pas être autorisée"""
    assert "m38h_salary" not in ALLOWED_TABLES

def test_table_not_allowed_accounting():
    """Table comptabilité ne doit pas être autorisée"""
    assert "m38h_accounting_account" not in ALLOWED_TABLES


# ─────────────────────────────────────────────────────────────
# Colonnes autorisées
# ─────────────────────────────────────────────────────────────

def test_allowed_columns_not_empty():
    """Les colonnes autorisées ne doivent pas être vides"""
    assert len(ALLOWED_COLUMNS) > 0

def test_allowed_columns_facture_has_ref():
    assert "ref" in ALLOWED_COLUMNS.get("m38h_facture", set())

def test_allowed_columns_facture_has_total_ht():
    assert "total_ht" in ALLOWED_COLUMNS.get("m38h_facture", set())

def test_allowed_columns_facture_has_total_ttc():
    assert "total_ttc" in ALLOWED_COLUMNS.get("m38h_facture", set())

def test_allowed_columns_facture_has_datef():
    assert "datef" in ALLOWED_COLUMNS.get("m38h_facture", set())

def test_allowed_columns_societe_has_nom():
    assert "nom" in ALLOWED_COLUMNS.get("m38h_societe", set())

def test_allowed_columns_product_has_stock():
    assert "stock" in ALLOWED_COLUMNS.get("m38h_product", set())

def test_allowed_columns_paiement_has_amount():
    assert "amount" in ALLOWED_COLUMNS.get("m38h_paiement_facture", set())

def test_allowed_columns_no_password():
    """Aucune colonne password ne doit être autorisée"""
    for table, columns in ALLOWED_COLUMNS.items():
        assert "password" not in columns, \
            f"Colonne 'password' trouvée dans {table}"

def test_allowed_columns_no_pass_hash():
    """Aucune colonne pass ne doit être autorisée"""
    for table, columns in ALLOWED_COLUMNS.items():
        assert "pass" not in columns, \
            f"Colonne 'pass' trouvée dans {table}"

def test_allowed_columns_defined_for_all_tables():
    """Chaque table autorisée doit avoir ses colonnes définies"""
    for table in ALLOWED_TABLES:
        assert table in ALLOWED_COLUMNS, \
            f"Table '{table}' n'a pas de colonnes définies dans ALLOWED_COLUMNS"
        assert len(ALLOWED_COLUMNS[table]) > 0, \
            f"Table '{table}' a une liste de colonnes vide"


# ─────────────────────────────────────────────────────────────
# Jointures autorisées
# ─────────────────────────────────────────────────────────────

def test_allowed_joins_not_empty():
    """La liste des jointures autorisées ne doit pas être vide"""
    assert len(ALLOWED_JOINS) > 0

def test_allowed_joins_facture_societe():
    """Jointure facture ↔ societe doit être autorisée"""
    assert ("m38h_facture", "m38h_societe") in ALLOWED_JOINS

def test_allowed_joins_societe_commande():
    """Jointure societe ↔ commande doit être autorisée"""
    assert ("m38h_societe", "m38h_commande") in ALLOWED_JOINS

def test_allowed_joins_facture_paiement():
    """Jointure facture ↔ paiement doit être autorisée"""
    assert ("m38h_facture", "m38h_paiement_facture") in ALLOWED_JOINS

def test_allowed_joins_count():
    """Exactement 3 jointures autorisées"""
    assert len(ALLOWED_JOINS) == 3

def test_join_not_allowed_facture_user():
    """Jointure avec m38h_user ne doit pas être autorisée"""
    assert ("m38h_facture", "m38h_user") not in ALLOWED_JOINS

def test_join_not_allowed_user_salary():
    """Jointure user ↔ salary ne doit pas être autorisée"""
    assert ("m38h_user", "m38h_salary") not in ALLOWED_JOINS

def test_joins_reference_allowed_tables_only():
    """Toutes les jointures doivent référencer uniquement des tables autorisées"""
    for t1, t2 in ALLOWED_JOINS:
        assert t1 in ALLOWED_TABLES, \
            f"Table '{t1}' dans ALLOWED_JOINS mais pas dans ALLOWED_TABLES"
        assert t2 in ALLOWED_TABLES, \
            f"Table '{t2}' dans ALLOWED_JOINS mais pas dans ALLOWED_TABLES"