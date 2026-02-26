# app/audit.py

import json
import os
from collections import Counter

LOG_FILE = "chatbot_logs.json"


def get_audit_dashboard():

    if not os.path.exists(LOG_FILE):
        return {"message": "Aucun log disponible."}

    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                logs.append(json.loads(line))
            except:
                continue

    if not logs:
        return {"message": "Logs vides."}

    total_requests = len(logs)

    # 🔹 Durée moyenne sécurisée
    durations = [
        log.get("execution_time", 0)
        for log in logs
        if isinstance(log.get("execution_time", 0), (int, float))
    ]

    avg_duration = round(sum(durations) / len(durations), 2) if durations else 0

    # 🔹 Comptage succès / erreurs
    success_count = sum(1 for log in logs if log.get("status") == "success")
    error_count = sum(1 for log in logs if log.get("status") == "error")

    error_rate = (
        round((error_count / total_requests) * 100, 2)
        if total_requests > 0
        else 0
    )

    # 🔹 Requêtes par jour
    per_day_counter = Counter()
    for log in logs:
        timestamp = log.get("timestamp")
        if timestamp:
            day = timestamp.split(" ")[0]
            per_day_counter[day] += 1

    # 🔹 Top templates
    template_counter = Counter(
        log.get("template")
        for log in logs
        if log.get("template")
    )

    # 🔹 Top questions
    question_counter = Counter(
        log.get("question")
        for log in logs
        if log.get("question")
    )

    return {
        "total_requests": total_requests,
        "average_duration_ms": avg_duration,
        "success_count": success_count,
        "error_count": error_count,
        "error_rate_percent": error_rate,
        "requests_per_day": dict(per_day_counter),
        "top_templates": dict(template_counter),
        "top_questions": dict(question_counter)
    }