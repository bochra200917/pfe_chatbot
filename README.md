# PFE Chatbot – V1 Baseline (Sans LLM)

## 📌 Objectif

Cette V1 implémente un chatbot SQL sécurisé sans génération libre de requêtes.  
Le système route des questions en langage naturel vers des templates SQL prédéfinis.

L’objectif est de garantir :
- Sécurité (anti-injection, SELECT only)
- Robustesse
- Auditabilité
- Mesurabilité

---

## 🏗️ Architecture

- FastAPI (API REST)
- Templates SQL prédéfinis
- Routing NLP léger (regex + règles)
- Exécution SQL read-only
- Logs JSON
- Golden set de tests

---

## 🚀 Lancer le projet

### 1️⃣ Activer l’environnement virtuel

```bash
venv\Scripts\activate
```

### 2️⃣ Lancer l’API

```bash
uvicorn app.main:app --reload
```

API disponible sur :

```
http://127.0.0.1:8000/docs
```

---

## 📡 Endpoint principal

### POST `/ask`

### Input :

```json
{
  "question": "factures entre 2026-01-01 et 2026-01-31"
}
```

### Output :

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
    }
  }
}
```

---

## 🧪 Lancer les tests (Golden Set)

```bash
python test/test_golden_set.py
```

Le golden set permet de vérifier :

- Exactitude du template choisi
- Extraction correcte des paramètres
- Robustesse aux variantes de formulation

---

## 🔒 Sécurité

### 1️⃣ Requêtes paramétrées
Toutes les requêtes utilisent des paramètres SQLAlchemy (`:param`).

### 2️⃣ Whitelist SELECT uniquement
Seules les requêtes `SELECT` sont autorisées.

### 3️⃣ Blocage DDL / DML
Les mots-clés suivants sont interdits :

- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- CREATE
- TRUNCATE

### 4️⃣ Limitation du nombre de lignes
Un `LIMIT 200` est ajouté automatiquement si absent.

### 5️⃣ Utilisateur base de données en lecture seule (recommandé)

---

## 📊 Logs & Audit

Chaque requête est enregistrée dans :

```
chatbot_logs.json
```

Informations loguées :

- timestamp
- question
- sql_query
- execution_time
- row_count
- status
- error

Cela permet :
- Audit
- Monitoring
- Analyse des performances

---

## 📦 Templates disponibles

- Factures entre deux dates
- Factures par client
- Factures non payées
- Factures partiellement payées
- Clients avec plusieurs commandes
- Produits en stock faible
- Total ventes par mois

---

## 🧭 Roadmap

### ✅ V1
- Templates SQL sécurisés
- Endpoint `/ask`
- Golden set
- Logs
- Sécurité

### 🔜 V2
- Amélioration NLP
- Extraction mois texte (ex: "janvier 2026")
- Gestion erreurs améliorée
- Authentification
- Dashboard audit