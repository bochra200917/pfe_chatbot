# db.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = "mysql+pymysql://c137d_bochra:Bochra%40123@c137d.myd.infomaniak.com/c137d_app_dolibarr_42"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = sessionmaker(bind=engine)

FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "create", "truncate"]

def validate_query(sql_query: str):
    lower = sql_query.lower()
    for word in FORBIDDEN:
        if word in lower:
            raise Exception(f"Requête interdite détectée: {word}")

def execute_query(sql_query: str, params: dict = {}, limit: int = 200):
    validate_query(sql_query)

    # Ajout LIMIT automatique si absent
    if "limit" not in sql_query.lower():
        sql_query += f"\nLIMIT {limit}"

    with engine.connect() as connection:
        result = connection.execute(text(sql_query), params)
        rows = result.fetchall()
        columns = result.keys()
        return columns, rows