# test/test_sql_validation.py
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.sql_security import validate_sql_query, SQLSecurityError


# ─────────────────────────────────────────────────────────────
# Requêtes valides — doivent passer sans exception
# ─────────────────────────────────────────────────────────────

def test_valid_select_simple():
    """SELECT simple valide"""
    validate_sql_query(
        "SELECT ref, total_ttc FROM m38h_facture LIMIT 10"
    )

def test_valid_select_with_join():
    """SELECT avec JOIN autorisé"""
    validate_sql_query(
        "SELECT f.ref, s.nom FROM m38h_facture f "
        "LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid "
        "WHERE f.entity = 1 LIMIT 100"
    )

def test_valid_select_with_where():
    """SELECT avec clause WHERE"""
    validate_sql_query(
        "SELECT ref, total_ht FROM m38h_facture "
        "WHERE total_ht > 0 LIMIT 100"
    )

def test_valid_select_with_group_by():
    """SELECT avec GROUP BY"""
    validate_sql_query(
        "SELECT MONTH(datef), SUM(total_ht) FROM m38h_facture "
        "WHERE entity = 1 GROUP BY MONTH(datef) LIMIT 100"
    )

def test_valid_select_with_having():
    """SELECT avec HAVING"""
    validate_sql_query(
        "SELECT fk_soc, COUNT(*) as nb FROM m38h_commande "
        "GROUP BY fk_soc HAVING COUNT(*) > 2 LIMIT 100"
    )


# ─────────────────────────────────────────────────────────────
# Requêtes invalides — doivent lever SQLSecurityError
# ─────────────────────────────────────────────────────────────

def test_invalid_delete():
    """DELETE doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query("DELETE FROM m38h_societe")

def test_invalid_drop():
    """DROP TABLE doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query("DROP TABLE m38h_facture")

def test_invalid_insert():
    """INSERT doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query("INSERT INTO m38h_facture VALUES (1,2,3)")

def test_invalid_update():
    """UPDATE doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query("UPDATE m38h_facture SET total_ttc = 0")

def test_invalid_union():
    """UNION SELECT doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query(
            "SELECT ref FROM m38h_facture UNION SELECT password FROM m38h_user"
        )

def test_invalid_select_sensitive_table():
    """SELECT sur table non autorisée doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query("SELECT * FROM m38h_user LIMIT 10")

def test_invalid_select_password_column():
    """SELECT colonne password doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query("SELECT password FROM m38h_user LIMIT 10")

def test_invalid_alter():
    """ALTER TABLE doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query(
            "ALTER TABLE m38h_facture ADD COLUMN hack VARCHAR(255)"
        )

def test_invalid_truncate():
    """TRUNCATE doit être rejeté"""
    with pytest.raises((SQLSecurityError, Exception)):
        validate_sql_query("TRUNCATE TABLE m38h_facture")