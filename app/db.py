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

FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "create", "truncate"]

def validate_query(sql_query: str):
    lower = sql_query.lower()
    pattern = r"\b(" + "|".join(FORBIDDEN) + r")\b"
    if re.search(pattern, lower):
        raise Exception("Requête interdite détectée (mot clé SQL interdit).")


def execute_query(sql_query: str, params: dict = {}, limit: int = 200):
    validate_query(sql_query)

    if "limit" not in sql_query.lower():
        sql_query += f"\nLIMIT {limit}"

    with engine.connect() as connection:
        result = connection.execute(text(sql_query), params)
        rows = result.fetchall()
        columns = result.keys()
        return columns, rows