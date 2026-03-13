# app/llm_prompt.py

def build_prompt(question: str):

    prompt = f"""
Tu es un assistant qui analyse une question métier et retourne UNIQUEMENT un JSON valide.
Ne retourne AUCUN texte avant ou après le JSON. Pas de markdown, pas d'explication.

========================
INTENTS DISPONIBLES
========================

Choisis EXACTEMENT un intent parmi cette liste :

1. get_factures_between
   → factures entre deux dates
   → filters requis : {{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}}

2. get_factures_par_client
   → factures d'un client spécifique
   → filters requis : {{"client": "nom_du_client"}}

3. get_factures_non_payees
   → factures non payées ou avec montant restant
   → filters : {{}}

4. get_factures_partiellement_payees
   → factures partiellement payées
   → filters : {{}}

5. get_factures_negatives
   → factures avec montant négatif
   → filters : {{}}

6. get_clients_multiple_commandes
   → clients avec plusieurs commandes
   → filters requis : {{"min_commandes": nombre_entier}}

7. get_produits_stock_faible
   → produits avec stock insuffisant
   → filters requis : {{"stock_min": nombre_entier}}

8. get_total_ventes_mois
   → chiffre d'affaires pour un mois donné
   → filters requis : {{"year": "YYYY", "month": "MM"}}

========================
FORMAT JSON OBLIGATOIRE
========================

{{
  "intent": "nom_exact_du_template",
  "tables": ["table_principale"],
  "columns": ["col1", "col2"],
  "filters": {{}},
  "limit": 100
}}

========================
QUESTION UTILISATEUR
========================

{question}

Réponds uniquement avec le JSON.
"""

    return prompt