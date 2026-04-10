# Rapport de Performance — Chatbot V3

## Environnement
- Modèle LLM : google/gemini-2.0-flash-lite-001 (via OpenRouter)
- Golden set : 60 questions (V3 étendu)
- Base de données : MariaDB (Infomaniak)

## Résultats Globaux

| Métrique | Valeur |
|---|---|
| Total questions | 60 |
| Réussies | 60 |
| Accuracy | 100.0% |

## Latences (ms)

| Métrique | Valeur |
|---|---|
| Moyenne (mean) | 116.12 ms |
| Médiane | 0.07 ms |
| Écart-type | 212.1 ms |
| P95 | 393.65 ms |
| P99 | 1218.1 ms |
| Minimum | 0.0 ms |
| Maximum | 1218.1 ms |

## Répartition des appels

| Niveau | Nb appels | % |
|---|---|---|
| V1/V2 templates (sans LLM) | 30 | 50.0% |
| LLM (Gemini) | 0 | 0.0% |
| Sécurité / Clarification | 30 | 50.0% |

## Overhead LLM
- **0.0%** des requêtes nécessitent un appel LLM
- **100.0%** sont servies directement par V1/V2 (sans coût LLM)

## Conclusion
- Latence moyenne : **116.12 ms** — très acceptable pour un usage métier
- P95 : **393.65 ms** — 95% des requêtes répondent en moins de 393.65 ms
- La stratégie V1/V2 first réduit efficacement les appels LLM
