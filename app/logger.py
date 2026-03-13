#app/logger.py
import json
import time
import uuid
import os
from threading import Lock

LOG_FILE = "chatbot_logs.json"

log_lock = Lock()

MAX_LOG_SIZE_MB = 10

def log_query(question, sql_query, execution_time, row_count,
              template_name, params,
              status="success", error=None):

    if os.path.exists(LOG_FILE):

        size_mb = os.path.getsize(LOG_FILE) / (1024 * 1024)

        if size_mb > MAX_LOG_SIZE_MB:
            os.rename(LOG_FILE, LOG_FILE + ".backup")

    log_id = str(uuid.uuid4())

    log_entry = {
        "log_id": log_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "template": template_name,
        "params": params,
        "sql_query": sql_query,
        "execution_time": execution_time,
        "row_count": row_count,
        "status": status,
        "error": error
    }

    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return log_id