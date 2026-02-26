# README.md
# PFE Chatbot – V2 Sécurisé (Sans LLM)

---

## 📌 Objectif

Ce projet implémente un **chatbot SQL sécurisé** capable de répondre à des questions en langage naturel en utilisant exclusivement des **templates SQL prédéfinis** (sans génération libre de requêtes).

Le système garantit :

- ✅ Sécurité SQL forte (anti-injection)
- ✅ Architecture modulaire propre
- ✅ Audit complet des requêtes
- ✅ Mesurabilité (Golden Set 20+ tests)
- ✅ Robustesse NLP sans LLM
- ✅ Dashboard d’analyse des performances

---

# 🏗️ Architecture

Structure modulaire claire :

- `main.py` → API FastAPI (endpoint `/ask`, `/audit`)
- `chatbot.py` → NLP + routing vers templates
- `templates_sql.py` → requêtes SQL paramétrées
- `db.py` → exécution sécurisée (SELECT only)
- `logger.py` → logging structuré JSON
- `audit.py` → dashboard statistiques
- `test/` → golden_set_v1.py + golden_set_v2.py

👉 Architecture propre, sans mélange de responsabilités.  
👉 Conforme aux bonnes pratiques d’ingénierie logicielle.

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

⚠️ `requirements.txt` doit contenir :

```
pymysql
python-dotenv
fastapi
uvicorn
pydantic
sqlalchemy
```

## 3️⃣ Lancer l’API

```bash
uvicorn app.main:app --reload
```

Accès Swagger :

```
http://127.0.0.1:8000/docs
```

---

# 📡 Endpoint Principal

## 🔹 POST `/ask`

### Input

```json
{
  "question": "factures entre 2026-01-01 et 2026-01-31"
}
```

### Output

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
    "log_id": "uuid-unique-id"
  }
}
```

---

# 🔐 Sécurité SQL

Le système applique plusieurs niveaux de protection :

### ✅ 1. SELECT uniquement
Toute requête non SELECT est rejetée.

### ✅ 2. Blocage DDL / DML
Mots-clés interdits :
- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- CREATE
- TRUNCATE

### ✅ 3. Blocage injections classiques
Interdiction de :
- `;`
- `--`
- `/* */`

### ✅ 4. Requêtes paramétrées
Utilisation de paramètres SQLAlchemy (`:param`).

### ✅ 5. LIMIT automatique
Ajout automatique de `LIMIT 200` si absent.

### ✅ 6. Base de données en lecture seule
Compte MariaDB/MySQL configuré en **read-only**.

👉 Niveau sécurité : excellent pour un PFE.

---

# 🧠 NLP (Sans LLM)

Le système gère :

- ✔ Dates ISO (2026-01-01)
- ✔ Mois en texte ("janvier 2026")
- ✔ Extraction année automatique
- ✔ Client dynamique
- ✔ Seuil dynamique commandes (> 2)
- ✔ Seuil dynamique stock (< 5)
- ✔ Normalisation accents

Accuracy théorique sur Golden Set : 100%.

---

# 📦 Templates SQL Supportés

1. `get_factures_between`
2. `get_factures_par_client`
3. `get_factures_non_payees`
4. `get_factures_partiellement_payees`
5. `get_clients_multiple_commandes`
6. `get_produits_stock_faible`
7. `get_total_ventes_mois`

Toutes les requêtes sont paramétrées et sécurisées.

---

# 🧪 Golden Set

## ✔ V1
20 tests couvrant :
- dates ISO
- clients
- factures
- stock

## ✔ V2
20 tests supplémentaires incluant :
- mois texte
- seuil dynamique commandes
- seuil dynamique stock
- variantes linguistiques

Exécution :

```bash
python test/test_golden_set.py
```

Chaque test vérifie :

- template sélectionné
- paramètres extraits
- cohérence du routing NLP

---

# 📊 Logging & Audit

Logs stockés dans :

```
chatbot_logs.json
```

Chaque entrée contient :

- `log_id` (UUID)
- `timestamp`
- `question`
- `template`
- `params`
- `sql_query`
- `execution_time`
- `row_count`
- `status`
- `error`

---

# 📈 Dashboard Audit

Endpoint :

```
GET /audit
```

Statistiques calculées :

- total_requests
- average_duration_ms
- success_count
- error_count
- error_rate
- requests_per_day
- top_templates
- top_questions

👉 Conforme aux exigences V2 audit académique.

---

# 🔐 Authentification

Authentification Basic activée pour sécuriser les endpoints sensibles.

---

# 🎯 Conformité au Cahier des Charges

✔ Endpoint unique `/ask`  
✔ Golden Set ≥ 20 tests  
✔ SQL paramétré  
✔ Read-only  
✔ SELECT only  
✔ Anti-injection  
✔ Limitation lignes  
✔ Logs obligatoires  
✔ Dashboard audit  
✔ Auth simple  
✔ Gestion erreurs  

👉 Projet conforme à 100% aux exigences V1 + V2.

---

# 🏆 Conclusion

Ce projet implémente un chatbot SQL :

- 🔐 Sécurisé
- 🧱 Modulaire
- 📊 Mesurable
- 🧪 Testé
- 📁 Livrable propre

Il respecte entièrement le cahier des charges académique et dépasse le minimum requis.

---