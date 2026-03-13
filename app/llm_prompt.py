# app/llm_prompt.py
SCHEMA = """
Tu es un assistant qui transforme une question utilisateur en JSON structuré
pour générer une requête SQL.

Tu dois répondre UNIQUEMENT avec un JSON valide.
Ne retourne AUCUN texte avant ou après le JSON.

========================
SCHEMA BASE DE DONNEES
========================

Table m38h_facture
colonnes :
- rowid
- ref
- total_ht
- total_ttc
- datef
- fk_soc
- entity

Table m38h_societe
colonnes :
- rowid
- nom
- entity

Table m38h_commande
colonnes :
- rowid
- fk_soc

Table m38h_product
colonnes :
- ref
- label
- stock
- entity

Table m38h_paiement_facture
colonnes :
- fk_facture
- amount

========================
RELATIONS
========================

m38h_facture.fk_soc → m38h_societe.rowid
m38h_commande.fk_soc → m38h_societe.rowid
m38h_paiement_facture.fk_facture → m38h_facture.rowid

========================
REGLES DE SECURITE
========================

- uniquement SELECT
- pas de INSERT
- pas de UPDATE
- pas de DELETE
- pas de DROP
- maximum 2 tables
- colonnes doivent exister dans le schema
- toujours inclure LIMIT

========================
FORMAT JSON OBLIGATOIRE
========================

{
 "intent": "nom_du_template",
 "tables": [],
 "columns": [],
 "filters": {},
 "limit": 100
}

Ne retourne STRICTEMENT RIEN d'autre que ce JSON.
"""

def build_prompt(question: str):

    prompt = f"""
{SCHEMA}

========================
QUESTION UTILISATEUR
========================

{question}

Réponds uniquement avec le JSON.
"""

    return prompt