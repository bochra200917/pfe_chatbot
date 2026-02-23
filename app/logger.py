# logger.py

import json
import time

LOG_FILE = "chatbot_logs.json"

def log_query(question, sql_query, execution_time, row_count, status="success"):
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "sql_query": sql_query,
        "execution_time": execution_time,
        "row_count": row_count,
        "status": status
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")