# app/logger.py
import json
import time
import uuid
import os
from threading import Lock

LOG_FILE   = "chatbot_logs.json"
AUDIT_LOG  = "logs/audit.log"

log_lock = Lock()

MAX_LOG_SIZE_MB = 10


def _ensure_audit_dir():
    """Crée le dossier logs/ si inexistant"""
    os.makedirs("logs", exist_ok=True)


def log_query(question, sql_query, execution_time, row_count,
              template_name, params,
              status="success", error=None):

    # Rotation du fichier JSON si trop grand
    if os.path.exists(LOG_FILE):
        size_mb = os.path.getsize(LOG_FILE) / (1024 * 1024)
        if size_mb > MAX_LOG_SIZE_MB:
            os.rename(LOG_FILE, LOG_FILE + ".backup")

    log_id = str(uuid.uuid4())
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    log_entry = {
        "log_id":         log_id,
        "timestamp":      timestamp,
        "question":       question,
        "template":       template_name,
        "params":         params,
        "sql_query":      sql_query,
        "execution_time": execution_time,
        "row_count":      row_count,
        "status":         status,
        "error":          error
    }

    with log_lock:

        # 1. Écriture dans chatbot_logs.json (JSON lines)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        # 2. Écriture dans logs/audit.log (format lisible)
        _ensure_audit_dir()
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"[{timestamp}] "
                f"uuid={log_id} | "
                f"status={status} | "
                f"template={template_name or 'N/A'} | "
                f"rows={row_count} | "
                f"duration={execution_time}ms | "
                f"question={question[:80]}\n"
            )

    return log_id