# app/llm_prompt.py

def build_prompt(question: str):

    prompt = f"""
Tu es un assistant qui analyse une question métier et retourne UNIQUEMENT un JSON valide.
Ne retourne AUCUN texte avant ou après le JSON. Pas de markdown, pas d'explication.

========================
INTENTS DISPONIBLES (OBLIGATOIRE)
========================

- get_factures_between
- get_factures_par_client
- get_factures_non_payees
- get_factures_partiellement_payees
- get_factures_negatives
- get_clients_multiple_commandes
- get_produits_stock_faible
- get_total_ventes_mois
- get_total_paiements
- get_commandes_par_mois

RÈGLES STRICTES :
- Tu DOIS choisir un intent uniquement dans cette liste
- INTERDIT d'inventer un nouvel intent

========================
TABLES AUTORISÉES
========================

- m38h_facture
- m38h_societe
- m38h_commande
- m38h_product
- m38h_paiement_facture

RÈGLES :
- Tu DOIS utiliser EXACTEMENT ces noms
- "produit" est INTERDIT → utiliser "m38h_product"

========================
DÉTAIL DES INTENTS
========================

1. get_factures_between
   filters : {{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }}

2. get_factures_par_client
   filters : {{ "client": "nom_du_client" }}

3. get_factures_non_payees
   filters : {{}}

4. get_factures_partiellement_payees
   filters : {{}}

5. get_factures_negatives
   filters : {{}}

6. get_clients_multiple_commandes
   filters : {{ "min_commandes": nombre }}

7. get_produits_stock_faible
   filters : {{ "stock_min": nombre }}

8. get_total_ventes_mois
   filters : {{ "year": "YYYY", "month": "MM" }}

9. get_total_paiements
   filters : {{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }}

10. get_commandes_par_mois
   filters : {{ "year": "YYYY", "month": "MM" }}

11. get_produits_non_commandes
   → produits jamais commandés
   → filters : {{}}

========================
FORMAT JSON OBLIGATOIRE
========================

{{
  "intent": "...",
  "tables": ["..."],
  "columns": ["..."],
  "filters": {{}},
  "limit": 100
}}

========================
EXEMPLE IMPORTANT
========================

Question: combien de commandes ont été passées au mois de mars 2026 ?

Réponse:
{{
  "intent": "get_commandes_par_mois",
  "tables": ["m38h_commande"],
  "columns": ["count(*)"],
  "filters": {{
    "year": "2026",
    "month": "03"
  }},
  "limit": 100
}}

========================
QUESTION UTILISATEUR
========================

{question}

Réponds uniquement avec le JSON.
"""
    return prompt