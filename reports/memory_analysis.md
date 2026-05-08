# Analyse Mémoire — Chatbot NL2SQL V3

**Date :** 2026-04-02
**Auteur :** Bochra Ben Yedder

## Environnement système

| Paramètre | Valeur |
|---|---|
| RAM totale | 23.75 GB |
| RAM disponible | 10.21 GB |
| Utilisation système | 57.0% |

---

## Consommation mémoire par catégorie de requête

| Catégorie | Latence moy. | P95 | Δ Mémoire | Appels |
|---|---|---|---|---|
| template_v1v2 | 153.75 ms | 1103.33 ms | +1.23 MB | 15 |
| template_date | 121.36 ms | 441.92 ms | +0.07 MB | 15 |
| clarification | 0.01 ms | 0.03 ms | +0.00 MB | 15 |
| security_reject | 0.0 ms | 0.02 ms | +0.00 MB | 15 |

> Note : les latences du tableau "par catégorie" (153 ms, 121 ms) sont mesurées 
> en local (DB localhost). Les 2 387 ms correspondent à la DB distante Infomaniak.

### Interprétation

- **template_v1v2** : latence la plus faible, delta mémoire minimal — le routing par regex ne charge aucune ressource externe.
- **template_date** : idem, extraction regex des dates sans overhead.
- **clarification** : delta mémoire quasi nul — détection par pattern matching pur, aucune requête DB.
- **security_reject** : latence très faible (~0.1 ms) — rejet avant toute opération coûteuse. Seule la fonction `detect_injection()` est appelée.

---

## Impact du cache sur les performances

| Question | Sans cache (cold) | Avec cache (warm) | Gain |
|---|---|---|---|
| factures non payees | 435.73 ms | 0.07 ms | 100.0% |
| produits en rupture de stock | 368.13 ms | 0.06 ms | 100.0% |
| clients fideles avec plus de 3 commandes | 267.09 ms | 0.08 ms | 100.0% |

### Stratégie d'invalidation

Le cache utilise une stratégie **TTL variable selon la criticité** :

| Template | TTL | Justification |
|---|---|---|
| `get_factures_non_payees` | 60 s | Données très dynamiques (paiements en temps réel) |
| `get_factures_partiellement_payees` | 60 s | Données très dynamiques |
| `get_total_ventes_mois` | 300 s | Données mensuelles, évolution lente |
| `get_factures_between` | 300 s | Données historiques, stables |
| `get_produits_stock_faible` | 600 s | Stock peu fréquemment mis à jour |
| `get_clients_multiple_commandes` | 600 s | Données clients, évolution lente |

L'éviction utilise la stratégie **LFU (Least Frequently Used)** : les entrées les moins accédées sont supprimées en premier lors du remplissage du cache (MAX = 100 entrées).

---

## Conclusion

- **Empreinte mémoire** : le système consomme une RAM très faible grâce à l'architecture V1/V2 first (pas de chargement LLM en mémoire).
- **Gain cache** : réduction significative de la latence sur les requêtes répétées.
- **Rejet sécurité** : coût mémoire quasi nul — les tentatives d'injection sont rejetées immédiatement sans toucher la DB.
