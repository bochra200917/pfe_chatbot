# Recommandations d'indexation DB — Chatbot NL2SQL V3

## Pourquoi ces index ?

La latence mesurée (~2 200 ms via HTTP) est principalement due à l'exécution
SQL sur la base distante. L'analyse des 9 templates révèle 4 types d'opérations
coûteuses sans index :

| Opération | Template | Colonne | Index recommandé |
|---|---|---|---|
| `WHERE datef BETWEEN` | get_factures_between | datef | idx_facture_datef_entity |
| `YEAR(datef) = :year AND MONTH(datef) = :month` | get_total_ventes_mois | datef | idx_facture_datef |
| `LEFT JOIN ON pf.fk_facture = f.rowid` | get_factures_non_payees | fk_facture | idx_paiement_fk_facture |
| `WHERE s.nom = :client` | get_factures_par_client | nom | idx_societe_nom |
| `WHERE p.stock < :stock_min` | get_produits_stock_faible | stock | idx_product_stock |
| `JOIN ON co.fk_soc = c.rowid` | get_clients_multiple_commandes | fk_soc | idx_commande_fk_soc |

## Gain estimé

Sans index, MariaDB fait un **full table scan** sur chaque requête.
Avec ces index, les requêtes les plus fréquentes passeront en **index scan** :

| Template | Avant (estimé) | Après (estimé) |
|---|---|---|
| get_factures_between | ~800 ms SQL | ~100 ms SQL |
| get_factures_non_payees | ~600 ms SQL | ~80 ms SQL |
| get_total_ventes_mois | ~400 ms SQL | ~50 ms SQL |
| get_produits_stock_faible | ~300 ms SQL | ~30 ms SQL |

## Comment appliquer

Le compte DB du chatbot est configuré en **lecture seule** (`GRANT SELECT`).
La création d'index nécessite des droits `ALTER` — à appliquer par l'administrateur
de la base de données via phpMyAdmin ou en ligne de commande :
```bash
mysql -u admin_user -p dolibarr_db < docs/db_indexes.sql
```