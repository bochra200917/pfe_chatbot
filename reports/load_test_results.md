# Rapport Tests de Charge — Chatbot V3

## Configuration
- Endpoint : POST /ask
- Question : "factures non payees"
- Compte DB : read-only

## Test 1 — 10 RPS (30 secondes)

| Métrique | Valeur |
|---|---|
| Débit réel | 9.27 RPS |
| Requêtes envoyées | 300 |
| Succès | 300 |
| Erreurs | 0 |
| Latence moyenne | 2061.88 ms |
| P95 | 2084.13 ms |
| P99 | 2287.21 ms |
| Min / Max | 2019.24 ms / 2595.01 ms |

## Test 2 — 50 RPS (30 secondes)

| Métrique | Valeur |
|---|---|
| Débit réel | 43.73 RPS |
| Requêtes envoyées | 1500 |
| Succès | 1500 |
| Erreurs | 0 |
| Latence moyenne | 2058.75 ms |
| P95 | 2073.9 ms |
| P99 | 2341.64 ms |
| Min / Max | 2021.18 ms / 2827.1 ms |

## Conclusion
- Le système supporte jusqu'à **43.73 RPS effectifs** (cible 50 RPS) sans erreur
- 0 erreur sur 1 800 requêtes au total (300 + 1 500)
- Le compte DB read-only est respecté sous charge
- Aucune fuite de données ni timeout non géré observé
