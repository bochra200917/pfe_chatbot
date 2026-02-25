# app/logger.py
import json
import time
import uuid

LOG_FILE = "chatbot_logs.json"

def log_query(question, sql_query, execution_time, row_count,
              template_name, params,
              status="success", error=None):

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

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return log_id