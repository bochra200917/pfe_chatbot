# app/audit.py
import json
import os
import statistics
from collections import Counter
from datetime import datetime, timedelta

LOG_FILE  = "chatbot_logs.json"
MAX_LOGS  = 5000
TOP_LIMIT = 10

# Seuils d'alerte (ms) — déclenchent une alerte si dépassés
ALERT_THRESHOLDS = {
    "latency_p95_ms":    3000,   # P95 > 3s = dégradation
    "latency_p99_ms":    5000,   # P99 > 5s = dégradation sévère
    "error_rate_pct":    10.0,   # taux d'erreur > 10%
    "cache_hit_rate_pct": 20.0,  # cache hit < 20% = cache sous-utilisé
}


def _load_logs() -> list:
    """Charge les N derniers logs depuis le fichier JSONL."""
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


def _compute_percentile(values: list, pct: float) -> float:
    """Calcule un percentile sur une liste de valeurs."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * pct / 100)
    idx = min(idx, len(sorted_vals) - 1)
    return round(sorted_vals[idx], 2)


def _compute_latency_metrics(durations: list) -> dict:
    """Calcule mean, median, P95, P99 sur une liste de durées."""
    if not durations:
        return {
            "mean_ms":   0,
            "median_ms": 0,
            "p95_ms":    0,
            "p99_ms":    0,
            "min_ms":    0,
            "max_ms":    0,
        }
    return {
        "mean_ms":   round(statistics.mean(durations), 2),
        "median_ms": round(statistics.median(durations), 2),
        "p95_ms":    _compute_percentile(durations, 95),
        "p99_ms":    _compute_percentile(durations, 99),
        "min_ms":    round(min(durations), 2),
        "max_ms":    round(max(durations), 2),
    }


def _compute_cache_metrics(logs: list) -> dict:
    """Calcule le taux de cache hit/miss."""
    total     = len(logs)
    hits      = sum(1 for log in logs if log.get("from_cache") is True)
    misses    = total - hits
    hit_rate  = round(hits / total * 100, 2) if total > 0 else 0

    return {
        "total_requests": total,
        "cache_hits":     hits,
        "cache_misses":   misses,
        "hit_rate_pct":   hit_rate,
        "miss_rate_pct":  round(100 - hit_rate, 2),
    }


def _compute_alerts(latency: dict, error_rate: float, cache: dict) -> list:
    """
    Génère des alertes si les métriques dépassent les seuils définis.
    Retourne une liste d'alertes avec niveau (warning / critical).
    """
    alerts = []

    if latency["p95_ms"] > ALERT_THRESHOLDS["latency_p95_ms"]:
        alerts.append({
            "level":   "warning",
            "metric":  "latency_p95",
            "value":   f"{latency['p95_ms']} ms",
            "seuil":   f"{ALERT_THRESHOLDS['latency_p95_ms']} ms",
            "message": f"P95 élevé ({latency['p95_ms']} ms) — vérifier la connexion DB",
        })

    if latency["p99_ms"] > ALERT_THRESHOLDS["latency_p99_ms"]:
        alerts.append({
            "level":   "critical",
            "metric":  "latency_p99",
            "value":   f"{latency['p99_ms']} ms",
            "seuil":   f"{ALERT_THRESHOLDS['latency_p99_ms']} ms",
            "message": f"P99 critique ({latency['p99_ms']} ms) — dégradation sévère détectée",
        })

    if error_rate > ALERT_THRESHOLDS["error_rate_pct"]:
        alerts.append({
            "level":   "critical",
            "metric":  "error_rate",
            "value":   f"{error_rate}%",
            "seuil":   f"{ALERT_THRESHOLDS['error_rate_pct']}%",
            "message": f"Taux d'erreur élevé ({error_rate}%) — vérifier les templates SQL",
        })

    if (cache["hit_rate_pct"] < ALERT_THRESHOLDS["cache_hit_rate_pct"]
            and cache["total_requests"] > 20):
        alerts.append({
            "level":   "warning",
            "metric":  "cache_hit_rate",
            "value":   f"{cache['hit_rate_pct']}%",
            "seuil":   f"{ALERT_THRESHOLDS['cache_hit_rate_pct']}%",
            "message": f"Cache sous-utilisé ({cache['hit_rate_pct']}% hits) — requêtes très variées",
        })

    return alerts


def _compute_trends(logs: list) -> dict:
    """
    Compare les métriques des dernières 24h vs les 24h précédentes.
    Permet de détecter une dégradation récente.
    """
    now    = datetime.now()
    cutoff = now - timedelta(hours=24)
    prev   = now - timedelta(hours=48)

    recent   = []
    previous = []

    for log in logs:
        ts_str = log.get("timestamp", "")
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            if ts >= cutoff:
                recent.append(log)
            elif ts >= prev:
                previous.append(log)
        except Exception:
            pass

    def mean_duration(subset):
        durations = [
            l.get("execution_time", 0)
            for l in subset
            if isinstance(l.get("execution_time"), (int, float))
        ]
        return round(statistics.mean(durations), 2) if durations else 0

    recent_mean   = mean_duration(recent)
    previous_mean = mean_duration(previous)

    if previous_mean > 0:
        delta_pct = round((recent_mean - previous_mean) / previous_mean * 100, 1)
    else:
        delta_pct = 0

    return {
        "recent_24h":   {"count": len(recent),   "mean_ms": recent_mean},
        "previous_24h": {"count": len(previous), "mean_ms": previous_mean},
        "delta_pct":    delta_pct,
        "trend":        "hausse" if delta_pct > 10 else "baisse" if delta_pct < -10 else "stable",
    }


def get_audit_dashboard() -> dict:
    """
    Dashboard d'audit enrichi avec :
    - Métriques de latence : mean, median, P95, P99, min, max
    - Taux de cache hit/miss
    - Alertes automatiques sur dégradation
    - Tendances 24h vs 24h précédentes
    - Top templates et top questions
    - Répartition par statut
    """
    logs = _load_logs()

    if not logs:
        return {
            "message":       "Aucun log disponible.",
            "total_requests": 0,
            "alerts":        [],
        }

    total_requests = len(logs)

    # ── Durées ──
    durations = [
        log.get("execution_time", 0)
        for log in logs
        if isinstance(log.get("execution_time"), (int, float))
    ]

    latency = _compute_latency_metrics(durations)

    # ── Statuts ──
    success_count  = sum(1 for log in logs if log.get("status") == "success")
    error_count    = sum(1 for log in logs if log.get("status") == "error")
    rejected_count = sum(1 for log in logs if log.get("status") == "rejected")
    clarif_count   = sum(1 for log in logs
                         if log.get("status") == "clarification_required")

    error_rate = round(error_count / total_requests * 100, 2) if total_requests > 0 else 0

    # ── Cache hit/miss ──
    cache_metrics = _compute_cache_metrics(logs)

    # ── Alertes ──
    alerts = _compute_alerts(latency, error_rate, cache_metrics)

    # ── Tendances ──
    trends = _compute_trends(logs)

    # ── Top templates ──
    template_counter = Counter(
        log.get("template") for log in logs if log.get("template")
    )
    top_templates = dict(template_counter.most_common(TOP_LIMIT))

    # ── Top questions ──
    question_counter = Counter(
        log.get("question") for log in logs if log.get("question")
    )
    top_questions = dict(question_counter.most_common(TOP_LIMIT))

    # ── Répartition par jour ──
    per_day_counter = Counter()
    for log in logs:
        ts = log.get("timestamp", "")
        if isinstance(ts, str) and " " in ts:
            per_day_counter[ts.split(" ")[0]] += 1

    # ── Latence par template ──
    latency_by_template = {}
    for log in logs:
        tpl = log.get("template")
        dur = log.get("execution_time")
        if tpl and isinstance(dur, (int, float)):
            latency_by_template.setdefault(tpl, []).append(dur)

    latency_per_tpl = {
        tpl: _compute_latency_metrics(durs)
        for tpl, durs in latency_by_template.items()
    }

    return {
        # ── Résumé global ──
        "total_requests":   total_requests,
        "success_count":    success_count,
        "error_count":      error_count,
        "rejected_count":   rejected_count,
        "clarif_count":     clarif_count,
        "error_rate_pct":   error_rate,

        # ── Latence enrichie ──
        "latency":          latency,
        "latency_by_template": latency_per_tpl,

        # ── Cache ──
        "cache":            cache_metrics,

        # ── Alertes ──
        "alerts":           alerts,
        "alert_count":      len(alerts),

        # ── Tendances ──
        "trends":           trends,

        # ── Top listes ──
        "top_templates":    top_templates,
        "top_questions":    top_questions,
        "requests_per_day": dict(per_day_counter),
    }