# Breakdown des temps de reponse par template

**Genere le** : 02/04/2026 a 11:57:07
**Total mesures** : 90 (14 sans cache, 76 avec cache)

## Resume global (sans cache)

| Metrique | Valeur |
|---|---|
| Latence moyenne globale | **2378.9 ms** |
| Latence P95 globale     | **2683.0 ms** |
| Latence P99 globale     | **2761.5 ms** |
| Template le plus rapide | **get_factures_between** (2276 ms) |
| Template le plus lent   | **get_factures_partiellement_payees** (2433 ms) |
| Gain du cache | **13.4%** de reduction de latence |

## Detail par template

| Template | N | Moy. (ms) | Med. (ms) | P95 (ms) | P99 (ms) | Ecart-type | Performance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| get_factures_between | 3 | 2276.2 | 2277.4 | 2280.3 | 2280.5 | 5.0 | [!] Lent |
| get_factures_non_payees | 3 | 2392.2 | 2424.2 | 2483.1 | 2488.3 | 116.7 | [!] Lent |
| get_factures_partiellement_payees | 3 | 2432.6 | 2375.8 | 2604.7 | 2625.0 | 176.1 | [!] Lent |
| get_total_ventes_mois | 5 | 2400.3 | 2341.0 | 2697.6 | 2764.4 | 218.2 | [!] Lent |

## Visualisation

![Latence par template](latency_by_template.png)

## Analyse

### Observations principales

- La latence moyenne globale est de **2379 ms**, ce qui inclut le round-trip HTTP local + traitement NLP + execution SQL.
- Le template **get_factures_partiellement_payees** est le plus lent en raison du volume de donnees retournees et/ou de la complexite de la jointure SQL.
- Le template **get_factures_between** est le plus rapide car il necessite une requete SQL simple sans jointure complexe.
- Le cache reduit la latence de **13.4%** en moyenne — valide l'interet du mecanisme de cache pour les requetes repetitives.

### Recommandations

- **Connexion persistante DB** : remplacer la creation de connexion a chaque requete par un pool (SQLAlchemy `pool_size=5`) — gain estime : -300 a -500 ms.
- **Cache chaud** : pre-charger les templates les plus utilises au demarrage pour eliminer la latence de la premiere requete.
- **Timeout adaptatif** : fixer un timeout par template en fonction du P99 observe (ex: 5s pour `get_factures_between`, 3s pour les autres).
- **Objectif V3+** : descendre sous 800 ms en moyenne avec pool de connexions et cache chaud.

---
*Chatbot ZAI Informatique — NL2SQL V3 — 02/04/2026*