#app/audit.py 
import json
import os
from collections import Counter
from datetime import datetime

LOG_FILE = "chatbot_logs.json"


def get_audit_dashboard():

    if not os.path.exists(LOG_FILE):
        return {"message": "Aucun log disponible."}

    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            logs.append(json.loads(line))

    total_requests = len(logs)

    durations = [log["execution_time"] for log in logs]
    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0

    per_day_counter = Counter(
        log["timestamp"].split(" ")[0] for log in logs
    )

    template_counter = Counter(
        log["template"] for log in logs if log["template"]
    )

    question_counter = Counter(
        log["question"] for log in logs
    )

    return {
        "total_requests": total_requests,
        "average_duration_ms": avg_duration,
        "requests_per_day": dict(per_day_counter),
        "top_templates": dict(template_counter),
        "top_questions": dict(question_counter)
    }