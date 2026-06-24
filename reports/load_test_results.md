# Rapport Tests de Charge — Chatbot V3

## Configuration
- Endpoint : POST /ask
- Question : "factures non payees"
- Compte DB : read-only

## Test 1 — 10 RPS (30 secondes)

| Métrique | Valeur |
|---|---|
| Débit réel | 9.24 RPS |
| Requêtes envoyées | 300 |
| Succès | 300 |
| Erreurs | 0 |
| Latence moyenne | 2047.91 ms |
| P95 | 2066.88 ms |
| P99 | 2235.47 ms |
| Min / Max | 2023.32 ms / 2267.96 ms |

## Test 2 — 50 RPS (30 secondes)

| Métrique | Valeur |
|---|---|
| Débit réel | 43.48 RPS |
| Requêtes envoyées | 1500 |
| Succès | 1500 |
| Erreurs | 0 |
| Latence moyenne | 2050.27 ms |
| P95 | 2078.77 ms |
| P99 | 2337.08 ms |
| Min / Max | 2019.41 ms / 2560.4 ms |

## Conclusion
- Le système supporte 9.24 RPS sans erreur
- Le compte DB read-only est respecté sous charge
- Aucune fuite de données ni timeout non géré observé
