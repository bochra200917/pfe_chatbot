# scripts/benchmark_golden.py
# Mesure les latences du chatbot sur le golden set étendu (60 questions)
# Génère : reports/perf_latency_v3.csv + reports/perf_summary.md

import json
import time
import os
import sys
import csv
import statistics

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.chatbot import get_response

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
GOLDEN_SET_PATH = "test/golden_set/golden_set_v3_extended.json"
CSV_OUTPUT      = "reports/perf_latency_v3.csv"
SUMMARY_OUTPUT  = "reports/perf_summary.md"
REPEAT          = 1  # nombre de fois que chaque question est posée


def load_golden_set(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_benchmark(questions):
    results = []

    print(f"\n{'='*60}")
    print(f"Benchmark démarré — {len(questions)} questions")
    print(f"{'='*60}\n")

    for i, item in enumerate(questions, 1):
        question   = item["question"]
        category   = item.get("category", "unknown")
        expected_r = item.get("expected_reject", False)
        expected_c = item.get("expected_clarification", False)

        for _ in range(REPEAT):
            start = time.time()
            result = get_response(question)
            duration_ms = round((time.time() - start) * 1000, 2)

            status   = result.get("metadata", {}).get("status", "")
            template = result.get("metadata", {}).get("template", "")

            # Déterminer le niveau utilisé
            if expected_r:
                level = "security"
            elif expected_c:
                level = "clarification"
            elif template:
                level = "v1v2_template"
            else:
                level = "llm"

            # Succès ou échec
            if expected_r:
                success = status == "rejected"
            elif expected_c:
                success = status == "clarification_required"
            else:
                success = template is not None and template != ""

            results.append({
                "id":          item.get("id", i),
                "question":    question,
                "category":    category,
                "level":       level,
                "status":      status,
                "template":    template,
                "duration_ms": duration_ms,
                "success":     success
            })

            status_icon = "✅" if success else "❌"
            print(f"{status_icon} [{i:02d}] {question[:50]:<50} | {duration_ms:>8.1f} ms | {level}")

    return results


def compute_stats(results):
    durations = [r["duration_ms"] for r in results]
    durations_sorted = sorted(durations)
    n = len(durations_sorted)

    mean   = round(statistics.mean(durations), 2)
    median = round(statistics.median(durations), 2)
    stdev  = round(statistics.stdev(durations), 2) if n > 1 else 0
    p95    = round(durations_sorted[int(n * 0.95)], 2)
    p99    = round(durations_sorted[int(n * 0.99)], 2)
    min_d  = round(min(durations), 2)
    max_d  = round(max(durations), 2)

    total    = len(results)
    success  = sum(1 for r in results if r["success"])
    accuracy = round((success / total) * 100, 2)

    # Répartition par niveau
    levels = {}
    for r in results:
        lvl = r["level"]
        levels[lvl] = levels.get(lvl, 0) + 1

    llm_calls    = levels.get("llm", 0)
    v1v2_calls   = levels.get("v1v2_template", 0)
    other_calls  = levels.get("security", 0) + levels.get("clarification", 0)
    llm_overhead = round((llm_calls / total) * 100, 2) if total > 0 else 0

    return {
        "total":        total,
        "success":      success,
        "accuracy":     accuracy,
        "mean":         mean,
        "median":       median,
        "stdev":        stdev,
        "p95":          p95,
        "p99":          p99,
        "min":          min_d,
        "max":          max_d,
        "v1v2_calls":   v1v2_calls,
        "llm_calls":    llm_calls,
        "other_calls":  other_calls,
        "llm_overhead": llm_overhead,
        "levels":       levels
    }


def save_csv(results, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "question", "category", "level",
            "status", "template", "duration_ms", "success"
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n✅ CSV sauvegardé : {path}")


def save_summary(stats, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    content = f"""# Rapport de Performance — Chatbot V3

## Environnement
- Modèle LLM : google/gemini-2.0-flash-lite-001 (via OpenRouter)
- Golden set : 60 questions (V3 étendu)
- Base de données : MariaDB (Infomaniak)

## Résultats Globaux

| Métrique | Valeur |
|---|---|
| Total questions | {stats['total']} |
| Réussies | {stats['success']} |
| Accuracy | {stats['accuracy']}% |

## Latences (ms)

| Métrique | Valeur |
|---|---|
| Moyenne (mean) | {stats['mean']} ms |
| Médiane | {stats['median']} ms |
| Écart-type | {stats['stdev']} ms |
| P95 | {stats['p95']} ms |
| P99 | {stats['p99']} ms |
| Minimum | {stats['min']} ms |
| Maximum | {stats['max']} ms |

## Répartition des appels

| Niveau | Nb appels | % |
|---|---|---|
| V1/V2 templates (sans LLM) | {stats['v1v2_calls']} | {round(stats['v1v2_calls']/stats['total']*100, 1)}% |
| LLM (Gemini) | {stats['llm_calls']} | {round(stats['llm_calls']/stats['total']*100, 1)}% |
| Sécurité / Clarification | {stats['other_calls']} | {round(stats['other_calls']/stats['total']*100, 1)}% |

## Overhead LLM
- **{stats['llm_overhead']}%** des requêtes nécessitent un appel LLM
- **{100 - stats['llm_overhead']}%** sont servies directement par V1/V2 (sans coût LLM)

## Conclusion
- Latence moyenne : **{stats['mean']} ms** — très acceptable pour un usage métier
- P95 : **{stats['p95']} ms** — 95% des requêtes répondent en moins de {stats['p95']} ms
- La stratégie V1/V2 first réduit efficacement les appels LLM
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Rapport sauvegardé : {path}")


if __name__ == "__main__":
    # Charger le golden set
    questions = load_golden_set(GOLDEN_SET_PATH)

    # Lancer le benchmark
    results = run_benchmark(questions)

    # Calculer les stats
    stats = compute_stats(results)

    # Afficher le résumé
    print(f"\n{'='*60}")
    print(f"RÉSULTATS BENCHMARK")
    print(f"{'='*60}")
    print(f"Total          : {stats['total']} questions")
    print(f"Accuracy       : {stats['accuracy']}%")
    print(f"Moyenne        : {stats['mean']} ms")
    print(f"Médiane        : {stats['median']} ms")
    print(f"P95            : {stats['p95']} ms")
    print(f"P99            : {stats['p99']} ms")
    print(f"Min / Max      : {stats['min']} ms / {stats['max']} ms")
    print(f"Appels LLM     : {stats['llm_calls']}/{stats['total']} ({stats['llm_overhead']}%)")
    print(f"Appels V1/V2   : {stats['v1v2_calls']}/{stats['total']}")
    print(f"{'='*60}\n")

    # Sauvegarder
    save_csv(results, CSV_OUTPUT)
    save_summary(stats, SUMMARY_OUTPUT)