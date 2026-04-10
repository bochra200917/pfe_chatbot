# scripts/test_api.py
# Remplace curl pour tester l'API depuis PowerShell Windows
# Usage : python scripts/test_api.py

import requests

API_URL  = "http://localhost:8000/ask"
API_USER = "admin"
API_PASS = "1234"

QUESTIONS = [
    "quelles factures n ont pas ete reglees",
    "factures dont le solde restant est positif",
    "factures non payees",
    "CA total par mois pour 2026",
    "chiffre d affaires de janvier 2026",
]

print(f"\n{'='*60}")
print("  Test API — questions cibles")
print(f"{'='*60}\n")

for q in QUESTIONS:
    try:
        r = requests.post(
            API_URL,
            json={"question": q},
            auth=(API_USER, API_PASS),
            timeout=10
        )
        data     = r.json()
        meta     = data.get("metadata", {})
        template = meta.get("template", "unknown")
        status   = meta.get("status", "?")
        ok       = "OK" if template != "unknown" else "XX"
        print(f"  [{ok}] {q}")
        print(f"        → template={template}  status={status}\n")
    except Exception as e:
        print(f"  [ERR] {q}")
        print(f"        → {e}\n")