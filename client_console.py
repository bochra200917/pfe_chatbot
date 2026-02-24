# client_console.py
from app.chatbot import get_response

print("=== Console Chatbot V2 ===")
print("Tape 'exit' pour quitter.\n")

while True:
    query = input("Question: ").strip()
    if query.lower() == "exit":
        break
    result = get_response(query)
    print("\n--- Résultat ---")
    print(f"Résumé : {result['summary']}")
    print(f"Template : {result['metadata'].get('template')}")
    print(f"Logs ID : {result['metadata'].get('logs_id')}")
    print("Rows :", result['table'])
    print("----------------\n")