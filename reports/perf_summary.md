# Rapport de Performance — Chatbot V3

## Environnement
- Modèle LLM : google/gemini-2.0-flash-lite-001 (via OpenRouter)
- Golden set : 60 questions (V3 étendu)
- Base de données : MariaDB (Infomaniak)

## Résultats Globaux

| Métrique | Valeur |
|---|---|
| Total questions | 60 |
| Réussies | 57 |
| Accuracy | 95.0% |

## Latences (ms)

| Métrique | Valeur |
|---|---|
| Moyenne (mean) | 143.16 ms |
| Médiane | 1.01 ms |
| Écart-type | 570.81 ms |
| P95 | 198.09 ms |
| P99 | 4435.4 ms |
| Minimum | 0.01 ms |
| Maximum | 4435.4 ms |

## Répartition des appels

| Niveau | Nb appels | % |
|---|---|---|
| V1/V2 templates (sans LLM) | 30 | 50.0% |
| LLM (Ollama/Mistral) | 0 | 0.0% |
| Sécurité / Clarification | 30 | 50.0% |

## Overhead LLM
- **0.0%** des requêtes nécessitent un appel LLM
- **100.0%** sont servies directement par V1/V2 (sans coût LLM)

## Conclusion
- Latence moyenne : **143.16 ms** — très acceptable pour un usage métier
- P95 : **198.09 ms** — 95% des requêtes répondent en moins de 198.09 ms
- La stratégie V1/V2 first réduit efficacement les appels LLM
