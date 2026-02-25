# README.md
# PFE Chatbot – V1 Baseline (Sans LLM)

## 📌 Objectif

Cette V1 implémente un **chatbot SQL sécurisé** qui **répond à des questions en langage naturel** en utilisant des **templates SQL prédéfinis**.  

L’objectif est de garantir :  
- **Sécurité** (anti-injection, SELECT only, read-only)  
- **Robustesse** (gestion des erreurs, questions ambiguës)  
- **Auditabilité et traçabilité** (logs complets)  
- **Mesurabilité** (golden set de tests pour valider exactitude et cohérence)

---

## 🏗️ Architecture

- **FastAPI** : API REST  
- **Templates SQL prédéfinis** (`app/templates_sql.py`)  
- **Routing NLP léger** (regex + règles simples) pour détecter l’intention et extraire les paramètres  
- **Exécution SQL read-only** sur MariaDB/MySQL  
- **Logs JSON** pour audit et monitoring  
- **Golden set** de tests pour valider les résultats  

### Schéma simplifié

```
Utilisateur → /ask → NL→Template → SQL paramétré → DB read-only → Formatter → Réponse texte + table
```

---

## 🚀 Lancer le projet

### 1️⃣ Activer l’environnement virtuel

```bash
venv\Scripts\activate
```

### 2️⃣ Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3️⃣ Lancer l’API

```bash
uvicorn app.main:app --reload
```

L’API est disponible sur :  

```
http://127.0.0.1:8000/docs
```

---

## 📡 Endpoint principal

### POST `/ask`

#### Input exemple :

```json
{
  "question": "factures entre 2026-01-01 et 2026-01-31"
}
```

#### Output exemple :

```json
{
  "table": [
    {
      "facture_ref": "FA2512-0001",
      "client": "Mondher",
      "total_ht": 50.42,
      "total_ttc": 60.0,
      "date_facture": "2025-12-22"
    },
    {
      "facture_ref": "TC2-2601-0016",
      "client": "ZAYNEB",
      "total_ht": 131.8,
      "total_ttc": 131.8,
      "date_facture": "2026-01-06"
    }
  ],
  "summary": "2 résultat(s) trouvé(s).",
  "metadata": {
    "template": "get_factures_between",
    "duration_ms": 12.4,
    "row_count": 2,
    "params": {
      "start_date": "2026-01-01",
      "end_date": "2026-01-31"
    }
  }
}
```

---

## 📦 Templates SQL et exemples de réponse

### 1️⃣ Factures entre deux dates (`get_factures_between`)

**Question** :  
> "Montre-moi les factures entre le 2026-01-01 et le 2026-01-31"  

**Réponse exemple** :

| facture_ref   | client  | total_ht | total_ttc | date_facture |
|---------------|--------|----------|-----------|--------------|
| FA2512-0001   | Mondher| 50.42    | 60.0      | 2025-12-22   |
| TC2-2601-0016 | ZAYNEB | 131.8    | 131.8     | 2026-01-06   |

---

### 2️⃣ Factures par client (`get_factures_par_client`)

**Question** :  
> "Factures de ZAYNEB"  

**Réponse exemple** :

| facture_ref   | total_ht | total_ttc | date_facture |
|---------------|----------|-----------|--------------|
| TC2-2601-0016 | 131.8    | 131.8     | 2026-01-06   |
| TC2-2601-0017 | 540.0    | 540.0     | 2026-01-06   |

---

### 3️⃣ Factures non payées (`get_factures_non_payees`)

**Question** :  
> "Liste des factures non payées"  

**Réponse exemple** :

| facture_ref   | client  | total_ht | total_ttc | date_facture |
|---------------|--------|----------|-----------|--------------|
| FA2512-0001   | Mondher| 50.42    | 60.0      | 2025-12-22   |
| TC2-2601-0016 | ZAYNEB | 131.8    | 131.8     | 2026-01-06   |

---

### 4️⃣ Factures partiellement payées (`get_factures_partiellement_payees`)

**Question** :  
> "Factures partiellement payées"  

**Réponse exemple** :

| facture_ref   | client  | total_ht | total_ttc | date_facture |
|---------------|--------|----------|-----------|--------------|
| FA2512-0001   | Mondher| 50.42    | 60.0      | 2025-12-22   |
| TC2-2601-0016 | ZAYNEB | 131.8    | 131.8     | 2026-01-06   |

---

### 5️⃣ Clients avec plusieurs commandes (`get_clients_multiple_commandes`)

**Question** :  
> "Clients ayant plus de 2 commandes"  

**Réponse exemple** :

| client_id | client_nom | nb_commandes |
|-----------|-----------|--------------|
| 101       | ZAYNEB    | 5            |
| 102       | Mondher   | 3            |

---

### 6️⃣ Produits en stock faible (`get_produits_stock_faible`)

**Question** :  
> "Produits avec stock inférieur à 5"  

**Réponse exemple** :

| produit_ref | produit_nom | stock_disponible |
|------------|------------|-----------------|
| P001      | Stylo Bleu | 3               |
| P002      | Carnet A5  | 2               |

---

### 7️⃣ Total ventes par mois (`get_total_ventes_mois`)

**Question** :  
> "Chiffre d’affaires janvier 2026"  

**Réponse exemple** :

| mois      | CA_HT  | CA_TTC |
|-----------|-------|--------|
| 2026-01   | 1202.6 | 1300.0 |

---

## 🧪 Lancer les tests (Golden Set)

```bash
python test/test_golden_set.py
```

Le golden set vérifie :  

- Exactitude du template choisi  
- Extraction correcte des paramètres (dates, client, seuils)  
- Robustesse aux variantes de formulation  
- Limitation du nombre de lignes (max 200)  

---

## 🔒 Sécurité

1️⃣ **Requêtes paramétrées**  
- Toutes les requêtes SQL utilisent des paramètres (`:param`) pour éviter l’injection.

2️⃣ **Whitelist SELECT uniquement**  
- Seules les requêtes `SELECT` sont autorisées.

3️⃣ **Blocage DDL / DML**  
- Mots-clés interdits : INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE.

4️⃣ **Limitation du nombre de lignes**  
- Toutes les requêtes sont limitées à **200 lignes** si aucun LIMIT n’est présent.

5️⃣ **Compte DB en lecture seule**  
- Utiliser un utilisateur MariaDB/MySQL en **read-only**.

---

## 📊 Logs & Audit

Les logs sont enregistrés dans :

```
chatbot_logs.json
```

Informations loguées :  

- `timestamp` : date et heure de la requête  
- `question` : texte de la question  
- `sql_query` : SQL exécuté  
- `execution_time` : durée d’exécution (ms)  
- `row_count` : nombre de lignes retournées  
- `status` : succès/erreur  
- `error` : message d’erreur éventuel  

---

## 🧭 Roadmap

### ✅ V1 (livrable actuel)

- Templates SQL sécurisés et testés  
- Endpoint `/ask` fonctionnel  
- Golden set (tests pour 10–20 questions)  
- Logging minimal (question, SQL, durée, row_count, statut)  
- Sécurité read-only / anti-injection / limitation lignes  

### 🔜 V2 (améliorations futures)

- NLP plus avancé (extraction entités : dates, clients, seuils)  
- Extraction de mois en texte (ex : "janvier 2026")  
- Gestion des erreurs et questions ambiguës  
- Authentification API simple (token ou Basic Auth)  
- Dashboard audit (top questions, temps moyen, nb requêtes, templates utilisés)