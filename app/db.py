# app/db.py
from sqlalchemy import create_engine, text, event
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os
import time
from urllib.parse import quote_plus
from app.sql_security import enforce_limit

load_dotenv()

DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = os.getenv("DB_PORT")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = quote_plus(os.getenv("DB_PASSWORD"))
DB_NAME     = os.getenv("DB_NAME")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ─────────────────────────────────────────────
# Connection Pool — paramètres optimisés
# ─────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    # Pool de connexions persistantes
    poolclass        = QueuePool,
    pool_size        = 5,          # connexions maintenues ouvertes en permanence
    max_overflow     = 10,         # connexions supplémentaires sous forte charge
    pool_pre_ping    = True,       # vérifie la connexion avant utilisation
    pool_recycle     = 1800,       # recycle les connexions toutes les 30 min
    pool_timeout     = 10,         # timeout d'attente pour obtenir une connexion
    # Connexion individuelle
    connect_args     = {
        "connect_timeout":    5,
        "read_timeout":       10,
        "write_timeout":      10,
    }
)

# ─────────────────────────────────────────────
# Warm-up — pré-charger le pool au démarrage
# ─────────────────────────────────────────────

def warmup_pool():
    """
    Ouvre pool_size connexions dès le démarrage pour éliminer
    la latence de la première requête utilisateur.
    """
    connections = []
    try:
        for _ in range(engine.pool.size()):
            conn = engine.connect()
            conn.execute(text("SELECT 1"))
            connections.append(conn)
        print(f"✅ Pool warmup : {len(connections)} connexions pré-chargées")
    except Exception as e:
        print(f"⚠️ Pool warmup partiel : {e}")
    finally:
        for conn in connections:
            try:
                conn.close()
            except Exception:
                pass


# ─────────────────────────────────────────────
# Exécution sécurisée
# ─────────────────────────────────────────────

def execute_query(sql_query: str, params: dict = None):
    """
    Exécute une requête SQL en lecture seule via le pool de connexions.
    - enforce_limit : plafonne automatiquement à 200 lignes
    - statement_timeout : coupe la requête si elle dépasse 5s côté DB
    """
    if params is None:
        params = {}

    start = time.time()

    try:
        sql_query = enforce_limit(sql_query, 200)

        with engine.connect() as connection:
            connection.execute(text("SET SESSION max_statement_time=5"))
            result = connection.execute(text(sql_query), params)
            rows    = result.fetchall()
            columns = result.keys()

        execution_time = round((time.time() - start) * 1000, 2)
        return columns, rows, execution_time

    except Exception as e:
        execution_time = round((time.time() - start) * 1000, 2)
        raise Exception(f"Erreur DB sécurisée : {str(e)}")


# ─────────────────────────────────────────────
# Stats du pool — exposées dans /cache/stats
# ─────────────────────────────────────────────

def get_pool_stats() -> dict:
    """Retourne l'état actuel du pool de connexions."""
    try:
        pool = engine.pool
        return {
            "pool_size":       pool.size(),
            "checked_in":      pool.checkedin(),
            "checked_out":     pool.checkedout(),
            "overflow":        pool.overflow(),
            "invalid":         pool.invalid if hasattr(pool, 'invalid') else 0,
        }
    except Exception:
        return {}