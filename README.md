# PFE Chatbot – SQL Sécurisé (V1 + V2 + V3 LLM)

---

# 📌 Objectif

Ce projet implémente un **chatbot SQL sécurisé** capable de répondre à des questions en **langage naturel** sur une base de données.

Le système évolue en **trois versions successives** :

| Version | Description |
|------|------|
| **V1** | Templates SQL sécurisés |
| **V2** | NLP sans LLM (regex + extraction entités) |
| **V3** | Pipeline LLM sécurisé avec validation SQL |

Le système garantit :

- ✅ Sécurité SQL forte (anti-injection)
- ✅ Architecture modulaire propre
- ✅ Audit complet des requêtes
- ✅ Mesurabilité (Golden Set ≥ 20 tests)
- ✅ Robustesse NLP sans LLM
- ✅ Pipeline LLM sécurisé
- ✅ Dashboard d’analyse des performances

---

# 🏗️ Architecture

Structure modulaire claire :

```
app/

main.py
chatbot.py
chatbot_v3.py
templates_sql.py
sql_builder.py
sql_security.py
db.py
db_whitelist.py
logger.py
audit.py
summarizer.py
llm_prompt.py
llm_parser.py

test/
golden_set_v1.py
golden_set_v2.py
golden_set_v3.py
```

Responsabilités :

| Fichier | Rôle |
|------|------|
| `main.py` | API FastAPI |
| `chatbot.py` | NLP + routing templates |
| `chatbot_v3.py` | Pipeline LLM |
| `templates_sql.py` | Templates SQL paramétrés |
| `sql_builder.py` | Construction SQL depuis JSON |
| `sql_security.py` | Validation SQL AST |
| `db.py` | Exécution requêtes |
| `logger.py` | Logging structuré |
| `audit.py` | Dashboard statistiques |
| `summarizer.py` | Génération résumé réponse |

Architecture **fortement découplée et maintenable**.

---

# 🚀 Lancer le projet

## 1️⃣ Activer l’environnement

```bash
venv\Scripts\activate
```

## 2️⃣ Installer les dépendances

```bash
pip install -r requirements.txt
```

Le fichier `requirements.txt` doit contenir :

```
pymysql
python-dotenv
fastapi
uvicorn
pydantic
sqlalchemy
sqlglot
requests
```

## 3️⃣ Lancer l’API

```bash
uvicorn app.main:app --reload
```

Swagger :

```
http://127.0.0.1:8000/docs
```

---

# 📡 Endpoint Principal

### POST `/ask`

## Input

```json
{
 "question": "factures entre 2026-01-01 et 2026-01-31"
}
```

## Output

```json
{
 "table": [...],
 "summary": "5 résultat(s) trouvé(s).",
 "metadata": {
   "template": "get_factures_between",
   "duration_ms": 12.4,
   "row_count": 5,
   "params": {
     "start_date": "2026-01-01",
     "end_date": "2026-01-31"
   },
   "logs_id": "uuid"
 }
}
```

---

# 🔐 Sécurité SQL

Le système applique plusieurs niveaux de protection.

### 1️⃣ SELECT uniquement

Toute requête non SELECT est rejetée.

---

### 2️⃣ Blocage DDL / DML

Commandes interdites :

```
INSERT
UPDATE
DELETE
DROP
ALTER
CREATE
TRUNCATE
```

---

### 3️⃣ Blocage injections SQL

Interdiction de :

```
;
--
/* */
OR 1=1
```

---

### 4️⃣ Whitelist Tables

Tables autorisées :

```
m38h_facture
m38h_societe
m38h_commande
m38h_product
m38h_paiement_facture
```

---

### 5️⃣ Whitelist Colonnes

Chaque table possède une liste de colonnes autorisées.

---

### 6️⃣ Validation AST SQL

Les requêtes sont analysées avec :

```
sqlglot
```

Vérifications :

- type SELECT
- tables autorisées
- colonnes autorisées
- JOIN autorisés
- nombre maximum de tables

---

### 7️⃣ LIMIT automatique

Si la requête ne contient pas de LIMIT :

```
LIMIT 200
```

est ajouté automatiquement.

---

### 8️⃣ Blocage UNION

Les requêtes contenant `UNION` sont rejetées.

---

### 9️⃣ Blocage sous-requêtes

Les sous-requêtes SQL sont interdites.

---

### 🔟 Base de données en lecture seule

Le compte MySQL/MariaDB utilisé est configuré en **read-only**.

---

# 🧠 Version 2 — NLP Sans LLM

Le chatbot implémente un routing NLP basé sur **regex**.

Fonctionnalités :

✔ dates ISO  
✔ mois texte  
✔ extraction client  
✔ seuil dynamique commandes  
✔ seuil dynamique stock  
✔ normalisation accents  
✔ variantes linguistiques  

Exemples :

```
factures entre 2026-01-01 et 2026-01-31
clients avec plus de 3 commandes
stock inférieur à 5
```

---

# 🤖 Version 3 — Pipeline LLM Sécurisé

Une version expérimentale utilise un **LLM via OpenRouter**.

Pipeline :

```
Question utilisateur
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
Validation SQL (sqlglot)
      ↓
Execution
```

### Exemple JSON LLM

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

# 📦 Templates SQL Supportés

```
get_factures_between
get_factures_par_client
get_factures_non_payees
get_factures_partiellement_payees
get_clients_multiple_commandes
get_produits_stock_faible
get_total_ventes_mois
get_factures_negatives
```

Toutes les requêtes sont :

- paramétrées  
- sécurisées  
- validées  

---

# 🧪 Golden Set

## V1

20 tests couvrant :

```
factures
clients
dates
stock
```

---

## V2

20 tests supplémentaires :

```
mois texte
seuil dynamique
variantes linguistiques
```

---

## V3

Tests pour pipeline LLM :

```
validation JSON
validation SQL
robustesse pipeline
```

---

## Lancer les tests

```bash
python test/test_golden_set.py
```

Chaque test vérifie :

- template sélectionné  
- paramètres extraits  
- cohérence du routing  

---

# 📊 Logging

Les logs sont stockés dans :

```
chatbot_logs.json
```

Chaque entrée contient :

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
error
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
average_duration_ms
success_count
error_count
error_rate
requests_per_day
top_templates
top_questions
```

---

# 🔐 Authentification

Les endpoints sont protégés par :

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

Le projet utilise **OpenRouter**.

Variable environnement :

```
OPENROUTER_API_KEY=your_key_here
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
| Limitation lignes | ✅ |
| Logs obligatoires | ✅ |
| Dashboard audit | ✅ |
| Auth API | ✅ |
| Pipeline LLM sécurisé | ✅ |

---

# 🏆 Conclusion

Ce projet implémente un **chatbot SQL avancé** :

🔐 Sécurisé  
🧱 Modulaire  
📊 Mesurable  
🧪 Testé  
🤖 Compatible LLM  

Le système combine **NLP classique et LLM sécurisé**, tout en maintenant un **haut niveau de sécurité SQL**, adapté à un **projet de fin d’études en data engineering / NLP appliqué**.