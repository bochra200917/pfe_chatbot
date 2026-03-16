# PFE Chatbot – SQL Sécurisé (V1 + V2 + V3)

---

# 📌 Objectif

Ce projet implémente un **chatbot sécurisé permettant d’interroger une base SQL en langage naturel**.

Le système est conçu comme une **évolution progressive en trois versions** :

| Version | Description |
|------|------|
| **V1** | Templates SQL sécurisés |
| **V2** | NLP sans LLM (regex + extraction entités) |
| **V3** | Pipeline LLM sécurisé avec validation SQL |

L'objectif est de construire un système :

- 🔐 **hautement sécurisé**
- 🧠 **capable de comprendre le langage naturel**
- 📊 **mesurable via Golden Set**
- 🧱 **modulaire et maintenable**

---

# 🏗️ Architecture

Structure du projet :

```
app/

main.py
chatbot.py
chatbot_v3.py

templates_sql.py
sql_builder.py
sql_security.py
db_whitelist.py

db.py
logger.py
audit.py
summarizer.py

llm_prompt.py
llm_parser.py
llm_client.py
```

Tests :

```
test/

golden_set.json
golden_set_v2.json
golden_set_v3.json
```

---

# 🚀 Lancer le projet

## 1️⃣ Activer l'environnement

```bash
venv\Scripts\activate
```

---

## 2️⃣ Installer dépendances

```bash
pip install -r requirements.txt
```

---

## 3️⃣ Lancer API

```bash
uvicorn app.main:app --reload
```
## 4 Démarrer Streamlit 
```bash
streamlit run ui/app.py
```

Swagger :

```
http://127.0.0.1:8000/docs
```

---

# 📡 Endpoint Principal

### POST `/ask`

Input :

```json
{
 "question": "factures entre 2026-01-01 et 2026-01-31"
}
```

Output :

```json
{
 "table": [...],
 "summary": "5 résultat(s)",
 "metadata": {
   "template": "get_factures_between",
   "duration_ms": 15,
   "row_count": 5,
   "params": {}
 }
}
```

---

# 🔐 Architecture de Sécurité

Le système applique **plusieurs couches de sécurité**.

## 1️⃣ Validation entrée utilisateur

Blocage de patterns SQL dangereux :

```
;
--
/*
OR 1=1
UNION
```

---

## 2️⃣ SQL paramétré

Toutes les requêtes utilisent :

```
%(param)s
```

Ce qui empêche les injections SQL.

---

## 3️⃣ Whitelist Tables

Tables autorisées :

```
m38h_facture
m38h_societe
m38h_commande
m38h_product
m38h_paiement_facture
```

---

## 4️⃣ Whitelist Colonnes

Chaque table possède une liste de colonnes autorisées.

---

## 5️⃣ Validation AST SQL

Les requêtes sont analysées via :

```
sqlglot
```

Contrôles :

- SELECT uniquement
- tables autorisées
- colonnes autorisées
- JOIN autorisés
- blocage UNION
- blocage sous-requêtes

---

## 6️⃣ LIMIT obligatoire

Toute requête possède :

```
LIMIT 100
```

maximum.

---

## 7️⃣ Base de données read-only

Le compte MySQL possède uniquement :

```
SELECT
```

---

# 🧠 Version 2 – NLP sans LLM

La V2 implémente un **routing NLP basé sur regex**.

Fonctionnalités :

✔ détection dates  
✔ mois texte  
✔ seuil dynamique commandes  
✔ seuil dynamique stock  
✔ normalisation accents  

Exemples :

```
factures entre 2026-01-01 et 2026-01-31
clients avec plus de 3 commandes
produits avec stock inférieur à 5
```

---

# 🤖 Version 3 – Pipeline LLM

La V3 utilise un **LLM via OPENROUTER**.

Pipeline :

```
Question
↓
Prompt structuré
↓
LLM
↓
JSON structuré
↓
Validation Pydantic
↓
SQL Builder
↓
Validation SQL
↓
Execution
```

Exemple JSON :

```json
{
 "intent": "get_factures",
 "tables": ["m38h_facture"],
 "columns": ["ref", "total_ttc"],
 "filters": {},
 "limit": 10
}
```

---

# 🧪 Golden Set

Le projet utilise des **tests Golden Set** pour mesurer la performance.

## V1

20 requêtes :

```
factures
clients
stock
```

---

## V2

Tests NLP :

```
dates
mois texte
seuils dynamiques
```

---

## V3

Tests pipeline LLM :

```
validation JSON
validation SQL
robustesse LLM
```

---

# 📊 Logging

Toutes les requêtes sont enregistrées dans :

```
chatbot_logs.json
```

Structure :

```
log_id
timestamp
question
template
params
sql_query
execution_time
row_count
status
```

---

# 📈 Dashboard Audit

Endpoint :

```
GET /audit
```

Statistiques :

```
total_requests
success_rate
average_duration
top_templates
top_questions
```

---

# 🔐 Authentification

Protection API :

```
HTTP Basic Auth
```

Variables `.env` :

```
API_USER=admin
API_PASS=secret
```

---

# ⚙️ Configuration LLM

Le projet utilise **OPENROUTER**.

Variable :

```
OPENROUTER_API_KEY=...
```

---

# 🎯 Conformité Cahier des Charges

| Exigence | Statut |
|------|------|
| Endpoint /ask | ✅ |
| Golden Set ≥20 | ✅ |
| SQL paramétré | ✅ |
| Read-only DB | ✅ |
| SELECT only | ✅ |
| Anti-injection | ✅ |
| Logs obligatoires | ✅ |
| Dashboard audit | ✅ |
| Auth API | ✅ |
| Pipeline LLM sécurisé | ✅ |

---

# 🏆 Conclusion

Ce projet implémente un **chatbot SQL sécurisé et évolutif** combinant :

- NLP classique
- LLM
- sécurité SQL avancée

Le système est **modulaire, testé et sécurisé**, adapté à un **projet de fin d’études en Data Engineering / NLP appliqué**.