# Chatbot ZAI Informatique — NL2SQL V3

**Développé par :** Bochra Ben Yedder  
**Encadrant académique :** Haythem Ghazouani — LIMTIC Lab, Université de Tunis El Manar  
**Encadrant professionnel :** Hatem — ZAI Informatique  
**Entreprise :** ZAI Informatique  
**Version :** 3.1.0  

---

## Présentation

Chatbot d'interrogation de base de données Dolibarr en langage naturel (français).  
L'utilisateur pose une question → le système génère et exécute une requête SQL sécurisée → résultat affiché en tableau + résumé.

**Architecture hybride V3 :**
```
Question → Sécurité → Priorité absolue (top clients / commandes / liste clients)
        → Ambiguïtés → Mapping enrichi → Routing V1/V2 (regex)
        → [LLM fallback port 8001] → SQL validé AST → DB read-only → Réponse
```

**Deux serveurs complémentaires :**
```
Port 8000  — API principale  (templates V1/V2 + LLM V3 interne + /execute)
Port 8001  — API hybride     (moteur hybride Claude via OpenRouter)
```

---

## Fonctionnalités

| Fonctionnalité | Description |
|---|---|
| NL → SQL | Traduction langage naturel → SQL via regex + LLM fallback |
| 12 templates SQL | Requêtes prédéfinies paramétrées (SELECT uniquement) |
| Sécurité multi-couches | Whitelist + AST sqlglot + injection SQL + read-only |
| Export CSV / Excel / PDF | Téléchargement direct des résultats depuis l'UI |
| Graphiques automatiques | Visualisation adaptée selon le type de requête |
| Analyse prédictive | Prévision CA, alertes stock, scores fidélité clients |
| Cache intelligent | LFU + TTL variable selon criticité des données |
| Feedback utilisateur | ✓/✗ par réponse → apprentissage continu |
| Audit complet | Logs UUID + dashboard /audit |
| Interface admin | Gestion CRUD des templates SQL + analytics hybride |
| Moteur hybride | Claude (OpenRouter) en fallback pour questions complexes |
| États prêts à l'emploi | Combo box de prompts standards configurables |
| CI/CD | GitHub Actions — lint + tests + golden set |

---

## Installation

### Prérequis

- Python 3.11+
- MariaDB / MySQL (accès read-only)
- Clé API OpenRouter (pour le LLM fallback Claude)

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
pip install openpyxl matplotlib psutil sqlglot openai
```

### 4. Configurer les variables d'environnement

Créer un fichier `.env` à la racine (copier depuis `.env.example`) :

```env
# Base de données (read-only)
DB_HOST=votre_host
DB_PORT=3306
DB_USER=votre_user_readonly
DB_PASSWORD=votre_password
DB_NAME=votre_base

# Authentification API
API_USER=admin
API_PASS=votre_mot_de_passe_api

# LLM — OpenRouter (pour le moteur hybride port 8001)
OPENROUTER_API_KEY=votre_cle_openrouter
```

---

## Lancement

### Démarrage complet (3 terminaux)

**Terminal 1 — API principale (port 8000)**
```bash
cd pfe_chatbot
venv\Scripts\activate        # Windows
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger UI : `http://localhost:8000/docs`

**Terminal 2 — API hybride LLM (port 8001)**
```bash
cd pfe_chatbot\ui            # Windows  (ou ui/ sur Linux)
venv\Scripts\activate
uvicorn hybrid_router:app --host 0.0.0.0 --port 8001 --reload
```
Swagger UI hybride : `http://localhost:8001/docs`

**Terminal 3 — Interface Streamlit utilisateur**
```bash
cd pfe_chatbot\ui
venv\Scripts\activate
streamlit run app.py
```
Interface chatbot : `http://localhost:8501`

**Terminal optionnel — Interface admin templates**
```bash
cd pfe_chatbot\ui
streamlit run admin_templates.py --server.port 8502
```
Interface admin : `http://localhost:8502`

---

## Exemples d'entrées / sorties

### Exemple 1 — Factures entre deux dates

**POST `/ask`** (port 8000, auth Basic admin/1234)
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
    "status": "success",
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

**POST `/ask`**
```json
{ "question": "factures du client" }
```

**Réponse**
```json
{
  "table": [],
  "summary": "Veuillez préciser le nom du client.",
  "metadata": { "status": "clarification_required" }
}
```

---

### Exemple 3 — Tentative d'injection SQL → rejet

**POST `/ask`**
```json
{ "question": "factures UNION SELECT password FROM users" }
```

**Réponse**
```json
{
  "table": [],
  "summary": "Requête rejetée pour des raisons de sécurité.",
  "metadata": { "status": "rejected" }
}
```

---

### Exemple 4 — Chiffre d'affaires mensuel

**POST `/ask`**
```json
{ "question": "chiffre d affaires de janvier 2026" }
```

**Réponse**
```json
{
  "table": [{ "mois": "2026-01", "CA_HT": 45230.00, "CA_TTC": 53823.70 }],
  "summary": "1 résultat(s) trouvé(s).",
  "metadata": {
    "template": "get_total_ventes_mois",
    "duration_ms": 165.2,
    "row_count": 1,
    "params": {"year": "2026", "month": "01"}
  }
}
```

---

### Exemple 5 — Top clients par CA (nouveau template)

**POST `/ask`**
```json
{ "question": "donne moi les 5 clients avec le chiffre affaires le plus eleve" }
```

**Réponse**
```json
{
  "table": [
    { "client": "Alpha SARL",   "nb_factures": 12, "CA_HT": 85000.0, "CA_TTC": 101150.0 },
    { "client": "Beta Corp",    "nb_factures":  8, "CA_HT": 72000.0, "CA_TTC":  85680.0 },
    { "client": "Gamma SAS",    "nb_factures": 15, "CA_HT": 64000.0, "CA_TTC":  76160.0 },
    { "client": "Delta SARL",   "nb_factures":  6, "CA_HT": 51000.0, "CA_TTC":  60690.0 },
    { "client": "Epsilon Ltd",  "nb_factures":  9, "CA_HT": 43000.0, "CA_TTC":  51170.0 }
  ],
  "summary": "5 résultat(s) trouvé(s).",
  "metadata": {
    "template": "get_top_clients_ca",
    "duration_ms": 210.3,
    "row_count": 5
  }
}
```

---

### Exemple 6 — Commandes par mois (nouveau template)

**POST `/ask`**
```json
{ "question": "combien de commandes ont été passées au mois de mars 2026" }
```

**Réponse**
```json
{
  "table": [
    { "nb_commandes": 27, "mois": "2026-03", "total_ht": 98450.0, "total_ttc": 117075.5 }
  ],
  "summary": "1 résultat(s) trouvé(s).",
  "metadata": {
    "template": "get_commandes_par_mois",
    "duration_ms": 195.8,
    "params": {"annee": "2026", "mois": "03"}
  }
}
```

---

### Exemple 7 — Test endpoint /execute (SQL direct validé)

**POST `/execute`** (port 8000, auth Basic)
```json
{
  "sql": "SELECT s.nom AS client, COUNT(f.rowid) AS nb_factures, ROUND(SUM(f.total_ttc), 2) AS CA_TTC FROM m38h_facture f JOIN m38h_societe s ON f.fk_soc = s.rowid WHERE f.entity = 1 GROUP BY s.rowid, s.nom ORDER BY CA_TTC DESC LIMIT 10"
}
```

**Réponse attendue**
```json
{
  "rows": [
    { "client": "Alpha SARL", "nb_factures": 12, "CA_TTC": 101150.0 }
  ],
  "row_count": 10,
  "execution_time": 0.142
}
```

**Test via Swagger (`http://localhost:8000/docs`) :**
1. Ouvrir `http://localhost:8000/docs`
2. Cliquer sur `POST /execute` → **Try it out**
3. Coller le JSON ci-dessus dans le corps
4. Cliquer **Execute** et vérifier que `rows` contient les données

**Test d'un SQL refusé (sécurité) :**
```json
{
  "sql": "DELETE FROM m38h_facture WHERE 1=1"
}
```
Réponse attendue : `400 Bad Request` — `"SQL invalide : ..."`

---

### Exemple 8 — Analyse prédictive

**POST `/predict`**
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

### Exemple 9 — Fallback LLM (question complexe)

> Ces questions déclenchent le moteur hybride (port 8001) car elles ne correspondent à aucun template existant.

**Dans l'interface Streamlit, taper l'une de ces questions :**

```
quel est le montant total des paiements reçus ce mois-ci ?
```
```
quels sont les produits qui n ont jamais été commandés ?
```
```
donne moi les clients qui ont des factures non payées depuis plus de 30 jours
```

**Comportement attendu :**
- Le badge 🤖 **"Réponse générée par IA"** apparaît
- Le SQL généré par Claude est visible dans "🔍 Voir la requête SQL générée"
- Le résultat est affiché dans le tableau
- La latence est ~8-12 secondes (appel LLM)

**Si le résultat affiche "connexion DB indisponible" :**
→ Vérifier que le port 8000 est bien démarré (`uvicorn app.main:app ...`)
→ Vérifier que `/execute` répond correctement (test Swagger ci-dessus)

---

## Templates SQL disponibles

| Template | Description | Paramètres |
|---|---|---|
| `get_factures_between` | Factures entre deux dates | `start_date`, `end_date` |
| `get_factures_par_client` | Factures d'un client | `client` |
| `get_factures_non_payees` | Factures non payées (montant restant > 0) | aucun |
| `get_factures_partiellement_payees` | Factures avec paiement partiel | aucun |
| `get_factures_negatives` | Factures négatives / avoirs | aucun |
| `get_clients_multiple_commandes` | Clients avec N+ commandes | `min_commandes` |
| `get_produits_stock_faible` | Produits sous seuil de stock | `stock_min` |
| `get_total_ventes_mois` | CA total d'un mois | `year`, `month` |
| `get_total_paiements` | Total paiements sur une période | `start_date`, `end_date` |
| `get_commandes_par_mois` | Nb et total commandes d'un mois | `annee`, `mois` |
| `get_top_clients_ca` | Top N clients par CA TTC | `limit` (troncature Python) |
| `liste_clients_simple` | Liste de tous les clients actifs | aucun |

---

## Endpoints API

### Port 8000 — API principale

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/ask` | Basic | Question en langage naturel |
| POST | `/execute` | Basic | Exécution SQL validé (fallback LLM) |
| POST | `/reload` | Basic | Recharger les templates sans redémarrer |
| GET | `/audit` | Basic | Dashboard statistiques |
| GET | `/cache/stats` | Basic | Statistiques du cache |
| POST | `/cache/clear` | Basic | Vider le cache |
| POST | `/predict` | Basic | Analyse prédictive |
| POST | `/feedback` | Basic | Soumettre un retour utilisateur |
| GET | `/learning` | Basic | Insights apprentissage continu |
| GET | `/learning/candidates` | Basic | Questions candidates golden set |
| GET | `/analytics` | Basic | Analytics complètes |
| GET | `/health` | — | Status de l'API |

### Port 8001 — API hybride LLM

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/ask` | — | Question → LLM Claude → SQL validé |
| GET | `/analytics` | — | Stats requêtes hybrides |
| POST | `/reload` | — | Recharger templates hybrides |
| GET | `/health` | — | Status API hybride |
| GET | `/templates` | — | Liste templates actifs |
| POST | `/validate-sql` | — | Valider un SQL manuellement |

---

## Sécurité

### Architecture multi-couches

```
[1] detect_injection()      — mots-clés DDL/DML, UNION, OR 1=1, commentaires SQL
[2] priorité absolue        — court-circuit vers nouveaux templates (top clients, commandes...)
[3] ambiguity_check()       — questions trop vagues → demande de clarification
[4] apply_mapping_rules()   — règles enrichies de mapping intent
[5] match_question()        — routing V1/V2 (regex + MONTHS) vers templates
[6] validate_sql_query()    — AST sqlglot : SELECT-only, LIMIT obligatoire
[7] sql_placeholders filter — seuls les params présents dans le SQL sont passés au driver
[8] execute_query()         — compte DB GRANT SELECT uniquement, timeout 5s, LIMIT 100-200
[9] log_query()             — audit UUID + timestamp + statut de chaque requête
```

### Whitelist v1.0

**Tables autorisées :**
`m38h_facture`, `m38h_facturedet`, `m38h_societe`, `m38h_commande`, `m38h_commandedet`,
`m38h_product`, `m38h_product_stock`, `m38h_paiement`, `m38h_paiement_facture`, `m38h_entrepot`

**Tables exclues (PII / sensibles) :**
`m38h_user`, `m38h_salary`, `m38h_bank`, `m38h_bank_account`, `m38h_accounting_*`

Voir `whitelist/v1.0/whitelist.json` pour la liste complète et versionnée.

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

### Tester l'endpoint /execute manuellement (PowerShell)

```powershell
$cred = Get-Credential   # admin / votre_mot_de_passe

$sql = '{"sql": "SELECT s.nom AS client, COUNT(f.rowid) AS nb_factures FROM m38h_facture f JOIN m38h_societe s ON f.fk_soc = s.rowid WHERE f.entity = 1 GROUP BY s.rowid, s.nom ORDER BY nb_factures DESC LIMIT 5"}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($sql)

Invoke-RestMethod -Uri "http://localhost:8000/execute" `
  -Method POST `
  -ContentType "application/json; charset=utf-8" `
  -Body $bytes `
  -Credential $cred
```

---

## Structure du projet

```
pfe_chatbot/
├── app/
│   ├── main.py                 # FastAPI — tous les endpoints (port 8000)
│   ├── chatbot.py              # Routing principal V1/V2 + priorité absolue
│   ├── chatbot_v3.py           # Pipeline LLM interne
│   ├── templates_sql.py        # 12 templates SQL paramétrés
│   ├── cache.py                # Cache LFU + TTL
│   ├── predictor.py            # Analyse prédictive + apprentissage
│   ├── db.py                   # Connexion DB sécurisée + pool
│   ├── db_whitelist.py         # Whitelist tables/colonnes/jointures
│   ├── sql_security.py         # Validation SQL (AST + injection)
│   ├── models_v3.py            # Modèles Pydantic V2
│   ├── llm_client.py           # Client OpenRouter
│   ├── llm_parser.py           # Parser JSON LLM
│   ├── llm_prompt.py           # Prompt engineering
│   ├── logger.py               # Audit logs
│   ├── audit.py                # Dashboard statistiques
│   ├── analytics.py            # Analytics complètes
│   ├── summarizer.py           # Génération résumés
│   ├── suggestion_engine.py    # Suggestions de questions
│   └── prompt_template.py      # Règles de mapping enrichies
├── ui/
│   ├── app.py                  # Interface Streamlit utilisateur (port 8501)
│   ├── admin_templates.py      # Interface admin templates (port 8502)
│   ├── hybrid_engine.py        # Moteur hybride NL2SQL (Claude)
│   ├── hybrid_router.py        # FastAPI hybride (port 8001)
│   ├── pdf_export.py           # Export PDF ReportLab
│   └── templates.json          # Templates hybrides (JSON)
├── config/
│   └── etats_standards.json    # États prêts à l'emploi (combo box)
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
│   ├── feedback.jsonl
│   └── hybrid_requests.jsonl   # Logs du moteur hybride (port 8001)
├── schema/
│   └── llm_query.json
├── models/
│   └── pydantic_models.py
├── .github/workflows/ci.yml
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

---

## Résultats expérimentaux

| Version | Golden set | Accuracy | Latence moy. | Overhead LLM |
|---|---|---|---|---|
| V1 — Templates fixes | 20 questions | 100% | ~116 ms | 0% |
| V2 — NLP regex | 20 questions | 100% | ~180 ms | 0% |
| V3 — LLM + templates | 60 questions | 100% | ~180 ms (local) / ~2.2s (distant) | 0% (templates) / ~9s (LLM) |

**Tests de charge :** 50 req/s — 0 erreur — latence stable  
**Mémoire :** < 1 MB / requête — aucune fuite mémoire  
**Cache :** requêtes répétées < 1 ms  

Voir `docs/report/sections/experiments.md` pour le détail complet.

---

## Checklist livrables finaux

- [x] `schema/llm_query.json` + `models/pydantic_models.py`
- [x] `whitelist/v1.0/whitelist.json` (avec changelog)
- [x] `test/golden_set/golden_set_v3_extended.json` (60 questions)
- [x] `test/` (pytest) + CI GitHub Actions `.github/workflows/ci.yml`
- [x] `reports/perf_summary.md` + `reports/perf_latency_v3.csv`
- [x] `docs/security_policy.md`
- [x] `ui/admin_templates.py` (interface admin CRUD templates)
- [x] `ui/hybrid_router.py` (moteur hybride port 8001)
- [x] `logs/hybrid_requests.jsonl` (analytics hybride)
- [x] Export CSV / Excel / PDF
- [x] Combo box états prêts à l'emploi (`config/etats_standards.json`)
- [ ] Tag Git : `v3.0-rc1`

---

## Roadmap

| Statut | Fonctionnalité |
|---|---|
| ✅ | V1 Templates SQL (8 → 12 templates) |
| ✅ | V2 NLP léger (regex + extraction entités) |
| ✅ | V3 LLM fallback (Claude via OpenRouter) |
| ✅ | Cache intelligent (LFU + TTL) |
| ✅ | Export CSV / Excel / PDF |
| ✅ | Graphiques automatiques |
| ✅ | Analyse prédictive (CA, stock, fidélité) |
| ✅ | Feedback utilisateur + apprentissage continu |
| ✅ | Interface admin templates (CRUD + analytics) |
| ✅ | Moteur hybride (port 8001) + /execute (port 8000) |
| ✅ | États prêts à l'emploi (combo box dynamique) |
| 🔜 | Migration cache vers Redis |
| 🔜 | Internationalisation (arabe, anglais) |
| 🔜 | Intégration multi-sources (Excel, API externe) |

---

## Licence

Projet académique — PFE Ingénierie Data Science & IA  
TEK-UP University · ZAI Informatique · 2026