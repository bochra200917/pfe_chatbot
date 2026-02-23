# test_chatbot.py
from app.chatbot import get_response

def print_limited(result, limit=5):
    table = result.get("table", [])
    summary = result.get("summary", "")
    print(summary)
    for row in table[:limit]:  # affiche seulement un échantillon
        print(row)
    if len(table) > limit:
        print(f"... ({len(table) - limit} lignes supplémentaires non affichées)")
    print("-"*50)

def test_factures_entre_dates():
    print("\n=== Test : Factures entre deux dates ===")
    query = "factures entre 2026-01-01 et 2026-01-07"
    result = get_response(query)
    print_limited(result)

def test_factures_par_client():
    print("\n=== Test : Factures pour un client spécifique ===")
    clients = ["Mickael", "ZAYNEB", "Client Passager"]
    for client in clients:
        query = f"factures pour le client {client}"
        result = get_response(query)
        print(f"Client : {client}")
        print_limited(result)

def test_total_ventes():
    print("\n=== Test : Total ventes par période ===")
    queries = [
        "total ventes janvier 2026",
        "total ventes février 2026",
    ]
    for q in queries:
        result = get_response(q)
        print(f"Question : {q}")
        print_limited(result)

def test_factures_negatives():
    print("\n=== Test : Factures avec montants négatifs ===")
    query = "factures avec total_ht négatif"
    result = get_response(query)
    print_limited(result)

if __name__ == "__main__":
    test_factures_entre_dates()
    test_factures_par_client()
    test_total_ventes()
    test_factures_negatives()
    print("\n✅ Tous les tests ont été exécutés.")