# Rapport Tests de Charge — Chatbot V3

## Configuration
- Endpoint : POST /ask
- Question : "factures non payees"
- Compte DB : read-only

## Test 1 — 10 RPS (30 secondes)

| Métrique | Valeur |
|---|---|
| Débit réel | 9.13 RPS |
| Requêtes envoyées | 300 |
| Succès | 300 |
| Erreurs | 0 |
| Latence moyenne | 2367.81 ms |
| P95 | 2517.8 ms |
| P99 | 3006.29 ms |
| Min / Max | 2248.87 ms / 3054.78 ms |

## Test 2 — 50 RPS (30 secondes)

| Métrique | Valeur |
|---|---|
| Débit réel | 42.66 RPS |
| Requêtes envoyées | 1500 |
| Succès | 1500 |
| Erreurs | 0 |
| Latence moyenne | 2434.1 ms |
| P95 | 2608.87 ms |
| P99 | 2774.15 ms |
| Min / Max | 2236.02 ms / 2965.19 ms |

## Conclusion
- Le système supporte 9.13 RPS sans erreur
- Le compte DB read-only est respecté sous charge
- Aucune fuite de données ni timeout non géré observé
