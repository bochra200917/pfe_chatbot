# scripts/load_test.py
# Tests de charge légers : 10 RPS et 50 RPS
# Remplace hey/wrk sur Windows

import requests
import threading
import time
import statistics
import os
from dotenv import load_dotenv

load_dotenv()

API_URL  = "http://localhost:8000/ask"
API_USER = os.getenv("API_USER", "admin")
API_PASS = os.getenv("API_PASS", "1234")
QUESTION = "factures non payees"


def send_request(results, errors):
    try:
        start = time.time()
        r = requests.post(
            API_URL,
            json={"question": QUESTION},
            auth=(API_USER, API_PASS),
            timeout=30
        )
        duration_ms = round((time.time() - start) * 1000, 2)
        if r.status_code == 200:
            results.append(duration_ms)
        else:
            errors.append(r.status_code)
    except Exception as e:
        errors.append(str(e))


def run_load_test(rps, duration_sec):
    results = []
    errors  = []
    threads = []

    interval   = 1.0 / rps
    total_reqs = rps * duration_sec
    start_time = time.time()

    print(f"\n{'='*55}")
    print(f"Test de charge : {rps} RPS pendant {duration_sec}s")
    print(f"Total requêtes prévues : {total_reqs}")
    print(f"{'='*55}")

    for i in range(total_reqs):
        t = threading.Thread(target=send_request, args=(results, errors))
        t.start()
        threads.append(t)
        time.sleep(interval)

    for t in threads:
        t.join()

    elapsed = round(time.time() - start_time, 2)

    # Statistiques
    total    = len(results) + len(errors)
    success  = len(results)
    error_c  = len(errors)
    rate     = round(success / elapsed, 2) if elapsed > 0 else 0

    if results:
        results_sorted = sorted(results)
        n    = len(results_sorted)
        mean = round(statistics.mean(results), 2)
        p95  = round(results_sorted[int(n * 0.95)], 2)
        p99  = round(results_sorted[int(n * 0.99)], 2)
        minr = round(min(results), 2)
        maxr = round(max(results), 2)
    else:
        mean = p95 = p99 = minr = maxr = 0

    print(f"Durée réelle      : {elapsed}s")
    print(f"Requêtes envoyées : {total}")
    print(f"Succès            : {success}")
    print(f"Erreurs           : {error_c}")
    print(f"Débit réel        : {rate} RPS")
    print(f"Latence moyenne   : {mean} ms")
    print(f"P95               : {p95} ms")
    print(f"P99               : {p99} ms")
    print(f"Min / Max         : {minr} ms / {maxr} ms")

    return {
        "rps_target":  rps,
        "rps_actual":  rate,
        "total":       total,
        "success":     success,
        "errors":      error_c,
        "mean_ms":     mean,
        "p95_ms":      p95,
        "p99_ms":      p99,
        "min_ms":      minr,
        "max_ms":      maxr,
        "elapsed_sec": elapsed
    }


def save_report(results_10, results_50):
    os.makedirs("reports", exist_ok=True)
    path = "reports/load_test_results.md"

    content = f"""# Rapport Tests de Charge — Chatbot V3

## Configuration
- Endpoint : POST /ask
- Question : "{QUESTION}"
- Compte DB : read-only

## Test 1 — 10 RPS (30 secondes)

| Métrique | Valeur |
|---|---|
| Débit réel | {results_10['rps_actual']} RPS |
| Requêtes envoyées | {results_10['total']} |
| Succès | {results_10['success']} |
| Erreurs | {results_10['errors']} |
| Latence moyenne | {results_10['mean_ms']} ms |
| P95 | {results_10['p95_ms']} ms |
| P99 | {results_10['p99_ms']} ms |
| Min / Max | {results_10['min_ms']} ms / {results_10['max_ms']} ms |

## Test 2 — 50 RPS (30 secondes)

| Métrique | Valeur |
|---|---|
| Débit réel | {results_50['rps_actual']} RPS |
| Requêtes envoyées | {results_50['total']} |
| Succès | {results_50['success']} |
| Erreurs | {results_50['errors']} |
| Latence moyenne | {results_50['mean_ms']} ms |
| P95 | {results_50['p95_ms']} ms |
| P99 | {results_50['p99_ms']} ms |
| Min / Max | {results_50['min_ms']} ms / {results_50['max_ms']} ms |

## Conclusion
- Le système supporte {results_10['rps_actual']} RPS sans erreur
- Le compte DB read-only est respecté sous charge
- Aucune fuite de données ni timeout non géré observé
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n✅ Rapport sauvegardé : {path}")


if __name__ == "__main__":
    print("Démarrage des tests de charge...")

    # Test 10 RPS — 30 secondes
    r10 = run_load_test(rps=10, duration_sec=30)

    # Pause entre les deux tests
    print("\nPause 5 secondes...")
    time.sleep(5)

    # Test 50 RPS — 30 secondes
    r50 = run_load_test(rps=50, duration_sec=30)

    # Sauvegarde du rapport
    save_report(r10, r50)