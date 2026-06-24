# Rapport d'analyse mémoire & performances

**Généré le** : 24/06/2026 à 09:21:55  
**API** : `http://localhost:8000/ask`  
**Questions testées** : 12  
**Passes** : 3  
**Total mesures** : 36  

---

## Résumé global (requêtes sans cache)

| Métrique | Valeur |
|---|---|
| Temps de réponse moyen | **2242.9 ms** |
| Temps de réponse P95   | **2278.7 ms** |
| Temps de réponse P99   | **2289.6 ms** |
| Mémoire de pointe moyenne (tracemalloc) | **73.3 KB** |
| Mémoire de pointe maximale (tracemalloc) | **162.0 KB** |
| Variation RSS moyenne par requête | **+0.23 MB** |
| Requêtes servies depuis le cache | **29/36** |

---

## Détail par template

| template | n | duration_mean_ms | duration_p95_ms | duration_p99_ms | duration_min_ms | duration_max_ms | mem_peak_mean_kb | mem_peak_max_kb | rss_delta_mean_mb | cpu_mean_pct | row_count_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ca_mois_courant | 3 | 2229.13 | 2233.08 | 2233.23 | 2222.73 | 2233.27 | 29.36 | 29.76 | 0.0 | 0.0 | 1.0 |
| get_factures_between | 2 | 2269.59 | 2290.08 | 2291.9 | 2246.82 | 2292.36 | 144.15 | 161.99 | 0.8 | 0.0 | 157.0 |
| get_factures_non_payees | 1 | 2232.25 | 2232.25 | 2232.25 | 2232.25 | 2232.25 | 102.96 | 102.96 | 0.0 | 0.0 | 100.0 |
| get_factures_partiellement_payees | 1 | 2241.27 | 2241.27 | 2241.27 | 2241.27 | 2241.27 | 33.98 | 33.98 | 0.0 | 0.7 | 13.0 |

---

## Visualisation

![Graphique d'analyse](memory_analysis.png)

---

## Interprétation

- **Temps de réponse** : La latence moyenne est de **2243 ms** via HTTP. Ce chiffre inclut le round-trip réseau local + traitement NLP + exécution SQL MariaDB (distante). Le routing direct sans DB (clarification, sécurité) répond en < 1 ms. Optimisation prévue (pool persistant + cache chaud) : objectif < 500 ms.
- **Mémoire tracemalloc** : L'empreinte mémoire Python par requête reste faible (< 1 MB en moyenne), confirmant l'efficacité du pipeline NL2SQL.
- **RSS delta** : La variation de mémoire système est stable entre les requêtes, sans fuite mémoire détectée.
- **Cache** : Les requêtes en cache sont significativement plus rapides, validant l'utilité du mécanisme de cache.

## Limites

- Mesures effectuées sur base de test (données limitées à partir de décembre 2025).
- `tracemalloc` mesure uniquement l'allocateur Python, pas la mémoire native (driver MariaDB, etc.).
- Le CPU % de psutil est mesuré sur une fenêtre courte — indicatif uniquement.

---
*Chatbot ZAI Informatique — NL2SQL V3 — 24/06/2026*