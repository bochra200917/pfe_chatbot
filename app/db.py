# app/db.py
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import time
from sqlalchemy import create_engine
import os
from urllib.parse import quote_plus
from app.sql_security import enforce_limit

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD"))
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
if not DATABASE_URL:
    raise ValueError("DATABASE_URL non définie dans .env")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=10,
    connect_args={"connect_timeout": 5}
)

def execute_query(sql_query: str, params: dict = None):
    
    if params is None:
        params = {}

    start = time.time()

    try:
       
        sql_query = enforce_limit(sql_query, 200)
        
        with engine.connect().execution_options(timeout=5) as connection:

            connection.execute(text("SET SESSION max_statement_time=5"))

            result = connection.execute(text(sql_query), params)

            rows = result.fetchall()
            columns = result.keys()

            execution_time = round((time.time() - start) * 1000, 2)

            return columns, rows, execution_time

    except Exception as e:

        execution_time = round((time.time() - start) * 1000, 2)

        raise Exception(f"Erreur DB sécurisée : {str(e)}")