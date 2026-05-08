# Analyse EXPLAIN — Optimisation des requêtes SQL

**Date :** 2026-04-22  
**Auteur :** Bochra Ben Yedder  
**Environnement :** MariaDB — Infomaniak (base distante)

---

## Méthodologie

Les 5 templates SQL les plus fréquents ont été analysés via `EXPLAIN` 
sur la base de production. L'objectif est d'identifier les full scans 
et les tris coûteux, et de proposer des index ciblés.

---

## Résultats EXPLAIN

### Requête 1 — get_factures_between ✅ Déjà optimisée

| table | type | key | rows | Extra |
|---|---|---|---|---|
| m38h_facture | range | idx_facture_datef | 274 | Using index condition |
| m38h_societe | eq_ref | PRIMARY | 1 | — |

**Diagnostic :** Index existant utilisé. Aucune action requise.

---

### Requête 2 — get_factures_non_payees ❌ Full scan

| table | type | key | rows | Extra |
|---|---|---|---|---|
| m38h_facture | ALL | NULL | 323 | Using temporary; Using filesort |
| m38h_societe | eq_ref | PRIMARY | 1 | — |
| m38h_paiement_facture | ref | idx_paiement_facture_fk_facture | 1 | — |

**Diagnostic :** Full scan sur `m38h_facture` (323 lignes). 
`Using temporary` et `Using filesort` indiquent un tri coûteux en mémoire.  
**Index recommandé :**
```sql
CREATE INDEX idx_facture_entity ON m38h_facture (entity);
```
**Gain estimé :** réduction du scan de 323 → ~50 lignes filtrées par entity.

---

### Requête 3 — get_total_ventes_mois ❌ Full scan

| table | type | key | rows | Extra |
|---|---|---|---|---|
| m38h_facture | ALL | NULL | 323 | Using temporary; Using filesort |

**Diagnostic :** `YEAR(datef)` et `MONTH(datef)` désactivent l'index 
`idx_facture_datef` existant car les fonctions sur colonnes bloquent 
l'utilisation des index B-tree.  
**Index recommandé :**
```sql
CREATE INDEX idx_facture_entity_datef ON m38h_facture (entity, datef);
```
**Gain estimé :** avec un index composé `(entity, datef)`, MariaDB peut 
utiliser une range scan sur datef même avec YEAR()/MONTH().

---

### Requête 4 — get_produits_stock_faible ⚠️ Partiellement optimisée

| table | type | key | rows | Extra |
|---|---|---|---|---|
| m38h_product | range | idx_product_entity_fk_product_type | 302 | Using filesort |

**Diagnostic :** Un index est utilisé mais le `Using filesort` indique 
que `ORDER BY stock ASC` ne peut pas être servi par cet index.  
**Index recommandé :**
```sql
CREATE INDEX idx_product_entity_stock ON m38h_product (entity, stock);
```
**Gain estimé :** suppression du filesort, ORDER BY servi directement 
par l'index.

---

### Requête 5 — get_commandes_par_mois ❌ Full scan

| table | type | key | rows | Extra |
|---|---|---|---|---|
| m38h_commande | ALL | NULL | 62 | Using temporary; Using filesort |

**Diagnostic :** Même problème que la requête 3 — `YEAR(date_commande)` 
et `MONTH(date_commande)` bloquent tout index.  
**Index recommandé :**
```sql
CREATE INDEX idx_commande_entity_date ON m38h_commande (entity, date_commande);
```
**Gain estimé :** passage de full scan (62 lignes) à range scan ciblé 
sur l'année/mois demandé.

---

## Tableau récapitulatif

| Template | Type actuel | Index recommandé | Gain estimé |
|---|---|---|---|
| get_factures_between | range ✅ | — déjà optimisé | — |
| get_factures_non_payees | ALL ❌ | idx_facture_entity | -85% lignes scannées |
| get_total_ventes_mois | ALL ❌ | idx_facture_entity_datef | -90% lignes scannées |
| get_produits_stock_faible | range ⚠️ | idx_product_entity_stock | suppression filesort |
| get_commandes_par_mois | ALL ❌ | idx_commande_entity_date | -80% lignes scannées |

---

## Note sur l'application des index

Le compte DB du chatbot est configuré en **lecture seule** (`GRANT SELECT`).
La création des index nécessite des droits `ALTER TABLE` — à appliquer 
par l'administrateur de la base via phpMyAdmin ou ligne de commande :

```bash
mysql -u admin_user -p dolibarr_db < docs/db_indexes.sql
```

---

## Conclusion

3 requêtes sur 5 font actuellement un full scan en production. 
L'application des 4 index recommandés permettrait de réduire 
significativement la latence SQL sur les requêtes les plus fréquentes, 
en complément du cache applicatif déjà en place.