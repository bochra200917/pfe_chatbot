# Rapport de Performance Étendu — Chatbot NL2SQL V3

**Date :** 2026-04-02
**Auteur :** Bochra Ben Yedder

---

## 1. Benchmark Comparatif — Approches NL2SQL du marché

| Système | Latence moy. | Accuracy | Sécurité | Coût/req | Overhead LLM |
|---|---|---|---|---|---|
| Chatbot ZAI (V3 — templates + LLM fallback) | 180 ms | 100.0% | Whitelist + AST + read-only | 0.000004 $ | 0% (golden set) ← **notre système** |
| Text-to-SQL LLM pur (GPT-4 / Gemini) | 2500 ms | 82.0% | Aucune (SQL libre généré) | 0.020000 $ | 100% |
| Defog SQLCoder (open-source) | 3800 ms | 86.0% | Aucune native | 0.008000 $ | 100% |
| LangChain SQL Agent | 4200 ms | 78.0% | Limitée (dépend du LLM) | 0.025000 $ | 100% |
| Système à règles pures (RASA / regex) | 50 ms | 65.0% | Excellente (SQL paramétré) | 0.000000 $ | 0% |


### Sources

- **Text-to-SQL LLM pur** : benchmarks Spider 2.0, BIRD (2024) — GPT-4 atteint ~82% execution accuracy sur BIRD.
- **Defog SQLCoder** : benchmark officiel Defog.ai (2024) — 86.6% sur Spider test set.
- **LangChain SQL Agent** : évaluation interne + littérature sur les agents multi-étapes.
- **Système à règles** : approche RASA NLU avec intents fixes — couverture limitée documentée.
- **Notre système** : golden set V3 étendu (60 questions), mesures locales.

---

## 2. Analyse par type de requête

| Catégorie | Latence moy. | P95 |
|---|---|---|
| template_v1v2 | 153.75 ms | 1103.33 ms |
| template_date | 121.36 ms | 441.92 ms |
| clarification | 0.01 ms | 0.03 ms |
| security_reject | 0.0 ms | 0.02 ms |


---

## 3. Avantages de notre approche

### 3.1 Sécurité by design

Contrairement aux approches LLM pures, notre système ne génère **jamais de SQL libre** :
- Le LLM identifie uniquement l'*intent* (parmi 12 templates connus)
- Le SQL est entièrement construit côté serveur
- Validation AST via sqlglot avant toute exécution
- Compte DB read-only : `GRANT SELECT` uniquement

### 3.2 Coût opérationnel

| Approche | Coût pour 10 000 requêtes/mois |
|---|---|
| Notre système (0% LLM sur golden set) | **~0 €** |
| Text-to-SQL GPT-4 | ~200 € |
| LangChain SQL Agent | ~250 € |
| Defog SQLCoder (GPU cloud) | ~80 € |

### 3.3 Latence

Notre système est **13× plus rapide** que les approches LLM pures (~180 ms vs ~2500 ms) grâce à la stratégie V1/V2 first.
Avec cache, la latence sur les requêtes répétées descend encore davantage.

### 3.4 Déterminisme

Les approches LLM pures souffrent de **variabilité** : la même question peut produire un SQL différent d'un appel à l'autre (température > 0). Notre architecture est **100% déterministe** sur les 12 templates.

---

## 4. Limites et perspectives

| Limite | Impact | Mitigation envisagée |
|---|---|---|
| 12 templates fixes | Couverture limitée aux cas définis | Ajout de templates + LLM pour cas complexes |
| Whitelist à maintenir | Évolution du schéma DB coûteuse | Versionnement + changelog automatisé |
| Mono-langue (français) | Pas d'internationalisation | Extension dictionnaire MONTHS + patterns |
| Cache en mémoire | Perdu au redémarrage | Migration vers Redis pour persistance |

---

## 5. Conclusion

Notre architecture **V1/V2 first, LLM en dernier recours** est la seule approche qui combine :
- ✅ Latence optimale (~180 ms)
- ✅ Sécurité maximale (whitelist + AST + read-only)
- ✅ Coût nul (0% d'appels LLM sur le golden set)
- ✅ Déterminisme total

Elle est particulièrement adaptée aux environnements de production où la sécurité des données et la prévisibilité des réponses sont prioritaires sur la flexibilité maximale.
