# app/db.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
import re

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL non définie dans .env")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = sessionmaker(bind=engine)

# 🔒 Mots interdits (écriture/modification)
FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop",
    "alter", "create", "truncate",
    "grant", "revoke"
]

# 🔒 Patterns dangereux
FORBIDDEN_PATTERNS = [
    ";",          # multi-queries
    "--",         # SQL comments
    "/*", "*/"    # block comments
]


def validate_query(sql_query: str):
    lower = sql_query.lower().strip()

    # 1️⃣ Autoriser uniquement SELECT
    if not lower.startswith("select"):
        raise Exception("Seules les requêtes SELECT sont autorisées.")

    # 2️⃣ Bloquer mots dangereux
    keyword_pattern = r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b"
    if re.search(keyword_pattern, lower):
        raise Exception("Mot-clé SQL interdit détecté.")

    # 3️⃣ Bloquer patterns suspects
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in lower:
            raise Exception("Pattern SQL suspect détecté.")

    # ❌ SUPPRESSION DU BLOCAGE DES SOUS-REQUÊTES
    # On autorise les sous-SELECT car nécessaires en analyse BI

    return True


def execute_query(sql_query: str, params: dict = None, limit: int = 200):
    if params is None:
        params = {}

    validate_query(sql_query)

    # 4️⃣ Ajouter LIMIT si absent
    if "limit" not in sql_query.lower():
        sql_query += f"\nLIMIT {limit}"

    try:
        with engine.connect() as connection:
            result = connection.execute(text(sql_query), params)
            rows = result.fetchall()
            columns = result.keys()
            return columns, rows

    except Exception as e:
        raise Exception(f"Erreur base de données : {str(e)}")