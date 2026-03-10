
#test/test_api.py
import requests

url = "http://127.0.0.1:8000/ask"  # endpoint correct
questions = [
    "factures non payées",
    "factures client ahmed",
    "factures 2026-01-01; DROP TABLE m38h_facture",
    "SELECT * FROM m38h_facture",
    "factures UNION SELECT password FROM users"
]

for q in questions:
    print("\nQUESTION:", q)
    r = requests.post(url, json={"question": q}, auth=("admin", "secret"))
    print("RESPONSE:", r.json())