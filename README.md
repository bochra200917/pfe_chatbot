# Chatbot ZAI Informatique — NL2SQL V3

**Développé par :** Bochra Ben Yedder  
**Encadrant académique :** Haythem Ghazouani — LIMTIC Lab, Université de Tunis El Manar  
**Entreprise :** ZAI Informatique  
**Version :** 3.1.0  

---

## Présentation

Chatbot d'interrogation de base de données Dolibarr en langage naturel (français).  
L'utilisateur pose une question → le système génère et exécute une requête SQL sécurisée → résultat affiché en tableau + résumé.

**Architecture hybride V3 :**
```
Question → Sécurité → Routing V1/V2 (regex) → [LLM fallback] → SQL validé → DB read-only → Réponse
```

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| NL → SQL | Traduction langage naturel → SQL via regex + LLM fallback |
| 8 templates SQL | Requêtes prédéfinies paramétrées (SELECT uniquement) |
| Sécurité multi-couches | Whitelist + AST sqlglot + injection SQL + read-only |
| Export CSV / Excel | Téléchargement direct des résultats depuis l'UI |
| Graphiques automatiques | Visualisation adaptée selon le type de requête |
| Analyse prédictive | Prévision CA, alertes stock, scores fidélité clients |
| Cache intelligent | LFU + TTL variable selon criticité des données |
| Feedback utilisateur | 👍/👎 par réponse → apprentissage continu |
| Audit complet | Logs UUID + dashboard /audit |
| CI/CD | GitHub Actions — lint + tests + golden set |

---

## Installation

### Prérequis

- Python 3.11+
- MariaDB / MySQL (accès read-only)
- Clé API OpenRouter (pour le LLM fallback)

### 1. Cloner le dépôt

```bash
git clone https://github.com/bochra200917/pfe_chatbot.git
cd pfe_chatbot
```

### 2. Créer l'environnement virtuel

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
pip install openpyxl matplotlib psutil
```

### 4. Configurer les variables d'environnement

Créer un fichier `.env` à la racine :

```env
DB_HOST=votre_host
DB_PORT=3306
DB_USER=votre_user_readonly
DB_PASSWORD=votre_password
DB_NAME=votre_base

API_USER=admin
API_PASS=votre_mot_de_passe_api

OPENROUTER_API_KEY=votre_cle_openrouter
```

---

## Lancement

### API FastAPI

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger UI disponible sur : `http://localhost:8000/docs`

### Interface Streamlit

```bash
streamlit run app/ui.py
```

Interface disponible sur : `http://localhost:8501`

---

## Exemples d'entrées / sorties

### Exemple 1 — Factures entre deux dates

**Requête POST `/ask`**
```json
{
  "question": "factures entre 2026-01-01 et 2026-02-28"
}
```

**Réponse**
```json
{
  "table": [
    {
      "facture_ref": "FA2026-001",
      "client": "Mondher SARL",
      "total_ht": 1500.00,
      "total_ttc": 1785.00,
      "date_facture": "2026-01-15"
    }
  ],
  "summary": "43 résultat(s) trouvé(s).",
  "metadata": {
    "template": "get_factures_between",
    "duration_ms": 180.5,
    "row_count": 43,
    "params": {"start_date": "2026-01-01", "end_date": "2026-02-28"},
    "logs_id": "a1b2c3d4-...",
    "sql_query": "SELECT f.ref AS facture_ref, ...",
    "from_cache": false
  }
}
```

---

### Exemple 2 — Question ambiguë → clarification

**Requête POST `/ask`**
```json
{
  "question": "factures du client"
}
```

**Réponse**
```json
{
  "table": [],
  "summary": "Veuillez préciser votre demande.",
  "metadata": {
    "status": "clarification_required"
  }
}
```

---

### Exemple 3 — Tentative d'injection SQL → rejet

**Requête POST `/ask`**
```json
{
  "question": "factures UNION SELECT password FROM users"
}
```

**Réponse**
```json
{
  "table": [],
  "summary": "Requête rejetée pour des raisons de sécurité.",
  "metadata": {
    "status": "rejected"
  }
}
```

---

### Exemple 4 — Chiffre d'affaires mensuel

**Requête POST `/ask`**
```json
{
  "question": "chiffre d affaires de janvier 2026"
}
```

**Réponse**
```json
{
  "table": [
    {
      "mois": "2026-01",
      "CA_HT": 45230.00,
      "CA_TTC": 53823.70
    }
  ],
  "summary": "1 résultat(s) trouvé(s).",
  "metadata": {
    "template": "get_total_ventes_mois",
    "duration_ms": 165.2,
    "row_count": 1,
    "params": {"year": "2026", "month": "01"},
    "logs_id": "b2c3d4e5-..."
  }
}
```

---

### Exemple 5 — Analyse prédictive

**Requête POST `/predict`**
```json
{
  "template": "get_total_ventes_mois",
  "data": [
    {"mois": "2025-10", "CA_HT": 40000},
    {"mois": "2025-11", "CA_HT": 42000},
    {"mois": "2025-12", "CA_HT": 38000},
    {"mois": "2026-01", "CA_HT": 45000},
    {"mois": "2026-02", "CA_HT": 47000}
  ]
}
```

**Réponse**
```json
{
  "predicted_ca_ht": 49200.00,
  "predicted_ca_ttc": 58548.00,
  "trend": "hausse",
  "confidence": "high",
  "method": "linear_regression",
  "variation_pct": 4.7,
  "based_on_months": 5,
  "message": "Prévision basée sur 5 mois · Tendance : hausse (+4.7%)"
}
```

---

## Templates SQL disponibles

| Template | Description | Paramètres |
|---|---|---|
| `get_factures_between` | Factures entre deux dates | `start_date`, `end_date` |
| `get_factures_par_client` | Factures d'un client | `client` |
| `get_factures_non_payees` | Factures non payées | aucun |
| `get_factures_partiellement_payees` | Factures partiellement payées | aucun |
| `get_factures_negatives` | Factures négatives / avoirs | aucun |
| `get_clients_multiple_commandes` | Clients avec N+ commandes | `min_commandes` |
| `get_produits_stock_faible` | Produits sous seuil de stock | `stock_min` |
| `get_total_ventes_mois` | CA total d'un mois | `year`, `month` |

---

## Endpoints API

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/ask` | Question en langage naturel |
| GET | `/audit` | Dashboard statistiques |
| GET | `/cache/stats` | Statistiques du cache |
| POST | `/cache/clear` | Vider le cache |
| POST | `/predict` | Analyse prédictive |
| POST | `/feedback` | Soumettre un retour utilisateur |
| GET | `/learning` | Insights apprentissage continu |
| GET | `/learning/candidates` | Questions candidates golden set |
| GET | `/health` | Status de l'API |

Tous les endpoints (sauf `/health`) requièrent une authentification **HTTP Basic**.

---

## Sécurité

### Architecture multi-couches

```
[1] detect_injection()      — mots-clés DDL/DML, UNION, OR 1=1, commentaires SQL
[2] ambiguity_check()       — questions trop vagues → clarification
[3] match_question()        — routing V1/V2 (regex) vers templates
[4] validate_sql_query()    — AST sqlglot : SELECT-only, pas de sous-requêtes, LIMIT obligatoire
[5] whitelist check         — tables/colonnes/jointures autorisées uniquement
[6] execute_query()         — compte DB GRANT SELECT uniquement, timeout 5s, LIMIT 100
[7] log_query()             — audit complet de chaque requête
```

### Whitelist v1.0

**Tables autorisées :** `m38h_facture`, `m38h_societe`, `m38h_commande`, `m38h_product`, `m38h_paiement_facture`

**Tables exclues (PII) :** `m38h_user`, `m38h_salary`, `m38h_bank`, `m38h_accounting_*`, ...

Voir `whitelist/v1.0/whitelist.json` pour la liste complète.

---

## Tests

### Tests unitaires

```bash
# Tous les tests (hors DB)
pytest test/ --ignore=test/test_golden_set.py --ignore=test/test_api.py -v

# Tests spécifiques
pytest test/test_pydantic.py -v
pytest test/test_whitelist.py -v
pytest test/test_sql_validation.py -v
```

### Golden set (60 questions)

```bash
pytest test/test_golden_set.py -v
```

### Benchmark performances

```bash
python scripts/benchmark_golden.py
python scripts/benchmark_memory_comparative.py
```

### Tests de charge

```bash
python scripts/load_test.py
```

---

## Structure du projet

```
pfe_chatbot/
├── app/
│   ├── chatbot.py              # Routing principal V1/V2
│   ├── chatbot_v3.py           # Pipeline LLM
│   ├── cache.py                # Cache LFU + TTL
│   ├── predictor.py            # Analyse prédictive + apprentissage
│   ├── db.py                   # Connexion DB sécurisée
│   ├── db_whitelist.py         # Whitelist tables/colonnes/jointures
│   ├── sql_security.py         # Validation SQL (AST + injection)
│   ├── templates_sql.py        # 8 templates SQL paramétrés
│   ├── models_v3.py            # Modèles Pydantic V2
│   ├── llm_client.py           # Client OpenRouter/Gemini
│   ├── llm_parser.py           # Parser JSON LLM
│   ├── llm_prompt.py           # Prompt engineering
│   ├── logger.py               # Audit logs
│   ├── audit.py                # Dashboard statistiques
│   ├── summarizer.py           # Génération résumés
│   ├── main.py                 # FastAPI — tous les endpoints
│   └── ui.py                   # Interface Streamlit
├── test/
│   ├── test_pydantic.py
│   ├── test_whitelist.py
│   ├── test_sql_validation.py
│   ├── test_golden_set.py
│   └── golden_set/
│       ├── golden_set.json                  # V1 (20 questions)
│       ├── golden_set_v2.json               # V2 (20 questions)
│       ├── golden_set_v3.json               # V3 (30 questions)
│       └── golden_set_v3_extended.json      # V3 étendu (60 questions)
├── scripts/
│   ├── benchmark_golden.py
│   ├── benchmark_memory_comparative.py
│   ├── load_test.py
│   └── generate_figures.py
├── reports/
│   ├── perf_summary.md
│   ├── perf_latency_v3.csv
│   ├── perf_summary_extended.md
│   └── memory_analysis.md
├── docs/
│   ├── security_policy.md
│   └── report/sections/experiments.md
├── whitelist/
│   └── v1.0/whitelist.json
├── figs/
│   ├── accuracy_vs_version.png
│   └── latency_distribution.png
├── logs/
│   ├── audit.log
│   └── feedback.jsonl
├── schema/
│   └── llm_query.json
├── models/
│   └── pydantic_models.py
├── .github/workflows/ci.yml
├── .env.example
├── requirements.txt
└── README.md
```

---

## Résultats expérimentaux

| Version | Golden set | Accuracy | Latence moy. | Overhead LLM |
|---|---|---|---|---|
| V1 — Templates fixes | 20 questions | 100% | ~180 ms | 0% |
| V2 — NLP regex | 20 questions | 100% | ~180 ms | 0% |
| V3 — LLM + templates | 60 questions | 100% | ~180 ms | 0% |

Voir `docs/report/sections/experiments.md` pour le détail complet.

---

## Roadmap

| Statut | Fonctionnalité |
|---|---|
| ✅ | V1 Templates SQL |
| ✅ | V2 NLP léger (regex) |
| ✅ | V3 LLM fallback (Gemini) |
| ✅ | Cache intelligent (LFU + TTL) |
| ✅ | Export CSV / Excel |
| ✅ | Graphiques automatiques |
| ✅ | Analyse prédictive (CA, stock, fidélité) |
| ✅ | Feedback utilisateur + apprentissage continu |
| 🔜 | Migration cache vers Redis |
| 🔜 | Internationalisation (arabe, anglais) |
| 🔜 | Intégration multi-sources (Excel, API externe) |

---

## Licence

Projet académique — PFE Ingénierie Data Science & IA  
TEK-UP University · ZAI Informatique · 2026