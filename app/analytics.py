# app/analytics.py
# Analytics sur les requêtes utilisateurs
# Données calculées depuis chatbot_logs.json

import json
import os
import statistics
from collections import Counter
from datetime import datetime, timedelta

LOG_FILE = "chatbot_logs.json"
MAX_LOGS = 5000


def _load_logs() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    logs = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return logs[-MAX_LOGS:]


def get_analytics() -> dict:
    """
    Calcule les analytics complètes sur les requêtes utilisateurs.
    Retourne toutes les données nécessaires aux graphiques du dashboard.
    """
    logs = _load_logs()

    if not logs:
        return {"empty": True}

    # ── 1. Répartition par template ──
    template_counts = Counter(
        log.get("template") for log in logs if log.get("template")
    )

    # ── 2. Répartition par statut ──
    status_counts = Counter(
        log.get("status") for log in logs if log.get("status")
    )

    # ── 3. Volume par heure (dernières 24h) ──
    now    = datetime.now()
    cutoff = now - timedelta(hours=24)
    hourly = Counter()
    for log in logs:
        try:
            ts = datetime.strptime(log.get("timestamp", ""), "%Y-%m-%d %H:%M:%S")
            if ts >= cutoff:
                hourly[ts.strftime("%H:00")] += 1
        except Exception:
            pass
    # Remplir les heures manquantes avec 0
    for h in range(24):
        key = f"{h:02d}:00"
        hourly.setdefault(key, 0)
    hourly_sorted = dict(sorted(hourly.items()))

    # ── 4. Volume par jour (derniers 7 jours) ──
    daily = Counter()
    for log in logs:
        ts_str = log.get("timestamp", "")
        if isinstance(ts_str, str) and " " in ts_str:
            day = ts_str.split(" ")[0]
            daily[day] += 1
    daily_sorted = dict(sorted(daily.items())[-7:])

    # ── 5. Latence par template ──
    latency_by_tpl = {}
    for log in logs:
        tpl = log.get("template")
        dur = log.get("execution_time")
        if tpl and isinstance(dur, (int, float)) and not log.get("from_cache"):
            latency_by_tpl.setdefault(tpl, []).append(dur)

    latency_stats = {}
    for tpl, durs in latency_by_tpl.items():
        if durs:
            sorted_durs = sorted(durs)
            n = len(sorted_durs)
            latency_stats[tpl] = {
                "mean":  round(statistics.mean(durs), 1),
                "p95":   round(sorted_durs[int(n * 0.95)], 1),
                "count": n
            }

    # ── 6. Taux de succès global et par template ──
    success_rate = round(
        status_counts.get("success", 0) / len(logs) * 100, 1
    ) if logs else 0

    success_by_tpl = {}
    tpl_logs = {}
    for log in logs:
        tpl = log.get("template")
        if tpl:
            tpl_logs.setdefault(tpl, []).append(log.get("status"))
    for tpl, statuses in tpl_logs.items():
        ok = sum(1 for s in statuses if s == "success")
        success_by_tpl[tpl] = round(ok / len(statuses) * 100, 1)

    # ── 7. Questions les plus posées (top 10) ──
    top_questions = dict(
        Counter(log.get("question") for log in logs if log.get("question"))
        .most_common(10)
    )

    # ── 8. Cache performance ──
    cache_hits   = sum(1 for log in logs if log.get("from_cache") is True)
    cache_misses = len(logs) - cache_hits
    cache_hit_rate = round(cache_hits / len(logs) * 100, 1) if logs else 0

    # Latence cache vs sans cache
    durations_cold  = [log.get("execution_time", 0) for log in logs
                       if not log.get("from_cache")
                       and isinstance(log.get("execution_time"), (int, float))]
    durations_warm  = [log.get("execution_time", 0) for log in logs
                       if log.get("from_cache")
                       and isinstance(log.get("execution_time"), (int, float))]

    cache_comparison = {
        "cold_mean": round(statistics.mean(durations_cold), 1) if durations_cold else 0,
        "warm_mean": round(statistics.mean(durations_warm), 1) if durations_warm else 0,
        "hit_rate":  cache_hit_rate,
        "hits":      cache_hits,
        "misses":    cache_misses,
    }

    # ── 9. Évolution du taux de succès (par jour) ──
    daily_success = {}
    daily_total   = {}
    for log in logs:
        ts_str = log.get("timestamp", "")
        if isinstance(ts_str, str) and " " in ts_str:
            day = ts_str.split(" ")[0]
            daily_total[day]   = daily_total.get(day, 0) + 1
            if log.get("status") == "success":
                daily_success[day] = daily_success.get(day, 0) + 1

    daily_success_rate = {
        day: round(daily_success.get(day, 0) / total * 100, 1)
        for day, total in daily_total.items()
    }
    daily_success_rate = dict(sorted(daily_success_rate.items())[-7:])

    # ── 10. Résumé ──
    total = len(logs)
    durations_all = [
        log.get("execution_time", 0) for log in logs
        if isinstance(log.get("execution_time"), (int, float))
    ]

    return {
        "empty":               False,
        "total_requests":      total,
        "success_rate":        success_rate,
        "template_counts":     dict(template_counts.most_common(10)),
        "status_counts":       dict(status_counts),
        "hourly_volume":       hourly_sorted,
        "daily_volume":        daily_sorted,
        "latency_by_template": latency_stats,
        "success_by_template": success_by_tpl,
        "top_questions":       top_questions,
        "cache":               cache_comparison,
        "daily_success_rate":  daily_success_rate,
        "global_mean_ms":      round(statistics.mean(durations_all), 1) if durations_all else 0,
    }