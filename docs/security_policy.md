# Security Policy — Chatbot ZAI Informatique

**Version :** v1.0  
**Date :** 2026-03-23  
**Auteur :** Bochra Ben Yedder

---

## 1. Architecture de Sécurité

Le chatbot repose sur une architecture de sécurité **multi-couches** garantissant qu'aucune requête dangereuse ne peut atteindre la base de données.

```
Question utilisateur
        ↓
[Couche 1] Détection d'injection SQL
        ↓
[Couche 2] Vérification ambiguïté
        ↓
[Couche 3] Routing V1/V2/V3 (LLM en dernier recours)
        ↓
[Couche 4] Validation AST (sqlglot)
        ↓
[Couche 5] Vérification whitelist tables/colonnes/jointures
        ↓
[Couche 6] Enforcement LIMIT
        ↓
[Couche 7] Exécution sur compte DB read-only
        ↓
[Couche 8] Logging audit complet
```

---

## 2. Règles de Rejet

### 2.1 Mots-clés interdits
Toute question contenant l'un des patterns suivants est immédiatement rejetée :

| Pattern | Raison |
|---|---|
| `UNION`, `UNION SELECT` | Extraction de données non autorisées |
| `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE` | Modification/suppression de données |
| `OR 1=1`, `OR '1'='1'` | Tautologie SQL |
| `--`, `/*`, `*/` | Commentaires SQL malveillants |
| `SELECT` en début de question | Requête SQL brute |
| `;` | Multi-statements |
| `information_schema` | Lecture du schéma |

### 2.2 Validation AST (sqlglot)
Avant exécution, chaque requête SQL est analysée via AST :

| Règle | Action si violation |
|---|---|
| Uniquement SELECT autorisé | Rejet |
| Pas de sous-requêtes | Rejet |
| Pas de UNION | Rejet |
| LIMIT obligatoire | Rejet |
| Maximum 3 tables | Rejet |

### 2.3 Whitelist tables/colonnes/jointures
Toute référence à une table, colonne ou jointure non présente dans la whitelist `v1.0` est rejetée.

---

## 3. Messages Utilisateur (Plan de Fallback)

| Situation | Message retourné | Status |
|---|---|---|
| Injection SQL détectée | `"Requête rejetée pour des raisons de sécurité."` | `rejected` |
| Question ambiguë | `"Veuillez préciser votre demande."` | `clarification_required` |
| Intent LLM inconnu | `"Je ne peux pas répondre à cette question."` | `rejected` |
| JSON LLM invalide | `"Je ne peux pas répondre à cette question."` | `rejected` |
| Template non trouvé | `"Template non trouvé."` | `rejected` |
| Erreur SQL | `"Erreur lors de l'exécution."` | `error` |

---

## 4. Politique PII (Données Personnelles)

### 4.1 Colonnes inaccessibles
Les colonnes suivantes ne sont **jamais** exposées dans les réponses :

- `password`, `pass`, `pass_crypted`
- `salary`, `iban`, `bic`
- Toute colonne bancaire ou financière personnelle

### 4.2 Tables exclues
Les tables suivantes sont **exclues** de la whitelist et ne peuvent jamais être interrogées :

| Table | Raison |
|---|---|
| `m38h_user` | Données utilisateurs (login, password) |
| `m38h_usergroup` | Groupes et permissions |
| `m38h_salary` | Données salariales |
| `m38h_holiday` | Données RH |
| `m38h_accounting_account` | Données comptables sensibles |
| `m38h_accounting_bookkeeping` | Données comptables sensibles |
| `m38h_bank` | Données bancaires |
| `m38h_bank_account` | Données bancaires |

### 4.3 Confirmation PII dans les résumés
Le champ `summary` retourné à l'utilisateur ne contient **jamais** de données personnelles — il affiche uniquement le nombre de résultats :
> *"43 résultat(s) trouvé(s)."*

---

## 5. Compte Base de Données

| Paramètre | Valeur |
|---|---|
| Permissions | `GRANT SELECT` uniquement |
| Écriture | Impossible (INSERT/UPDATE/DELETE/DROP bloqués) |
| Timeout requêtes | 5 secondes |
| Limite lignes | 100 lignes maximum |

---

## 6. Rate Limiting LLM

| Paramètre | Valeur |
|---|---|
| Quota journalier | 100 appels/jour |
| Max tokens | 200 |
| Température | 0 (déterministe) |
| Modèle | `google/gemini-2.0-flash-lite-001` |
| Priorité | LLM appelé uniquement si V1/V2 échouent |

---

## 7. Audit et Traçabilité

Chaque requête est enregistrée dans `chatbot_logs.json` avec :

| Champ | Description |
|---|---|
| `uuid` | Identifiant unique de la requête |
| `timestamp` | Date et heure d'exécution |
| `question` | Question posée par l'utilisateur |
| `sql_query` | Requête SQL exécutée |
| `template` | Template utilisé |
| `duration_ms` | Durée d'exécution en ms |
| `row_count` | Nombre de lignes retournées |
| `status` | `success` / `rejected` / `error` |

Le dashboard d'audit est accessible via `GET /audit`.

---

## 8. Versionnement de la Whitelist

| Version | Date | Changements |
|---|---|---|
| `v1.0` | 2026-03-23 | Version initiale — 5 tables, 3 jointures, politique PII |