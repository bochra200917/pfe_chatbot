-- ============================================================
-- Recommandations d'indexation — Chatbot ZAI Informatique
-- À appliquer par l'administrateur DB (accès écriture requis)
-- Basé sur l'analyse des templates SQL les plus utilisés
-- ============================================================

-- ─────────────────────────────────────────────
-- Table : m38h_facture
-- Requêtes concernées : get_factures_between, get_factures_non_payees,
--                       get_total_ventes_mois, get_factures_negatives
-- ─────────────────────────────────────────────

-- Index sur la date (get_factures_between + get_total_ventes_mois)
CREATE INDEX IF NOT EXISTS idx_facture_datef
    ON m38h_facture (datef);

-- Index composé date + entity (toutes les requêtes filtrent sur entity=1)
CREATE INDEX IF NOT EXISTS idx_facture_datef_entity
    ON m38h_facture (datef, entity);

-- Index sur fk_soc (jointure avec m38h_societe)
CREATE INDEX IF NOT EXISTS idx_facture_fk_soc
    ON m38h_facture (fk_soc);

-- Index sur total_ht (get_factures_negatives : WHERE total_ht < 0)
CREATE INDEX IF NOT EXISTS idx_facture_total_ht
    ON m38h_facture (total_ht);

-- ─────────────────────────────────────────────
-- Table : m38h_paiement_facture
-- Requêtes concernées : get_factures_non_payees,
--                       get_factures_partiellement_payees
-- ─────────────────────────────────────────────

-- Index sur fk_facture (jointure avec m38h_facture — très fréquente)
CREATE INDEX IF NOT EXISTS idx_paiement_fk_facture
    ON m38h_paiement_facture (fk_facture);

-- ─────────────────────────────────────────────
-- Table : m38h_societe
-- Requêtes concernées : get_factures_par_client
-- ─────────────────────────────────────────────

-- Index sur nom (WHERE s.nom = :client)
CREATE INDEX IF NOT EXISTS idx_societe_nom
    ON m38h_societe (nom);

-- ─────────────────────────────────────────────
-- Table : m38h_commande
-- Requêtes concernées : get_clients_multiple_commandes
-- ─────────────────────────────────────────────

-- Index sur fk_soc (jointure + GROUP BY)
CREATE INDEX IF NOT EXISTS idx_commande_fk_soc
    ON m38h_commande (fk_soc);

-- ─────────────────────────────────────────────
-- Table : m38h_product
-- Requêtes concernées : get_produits_stock_faible
-- ─────────────────────────────────────────────

-- Index sur stock (WHERE p.stock < :stock_min ORDER BY p.stock)
CREATE INDEX IF NOT EXISTS idx_product_stock
    ON m38h_product (stock);


-- ═══════════════════════════════════════════════════════════
-- Index manquants identifiés par EXPLAIN — avril 2026
-- ═══════════════════════════════════════════════════════════

-- ── Requête 2 : factures_non_payees ──
-- Problème : full scan sur m38h_facture (323 lignes, no index)
-- Solution : index sur (entity) pour filtrer d'abord
CREATE INDEX IF NOT EXISTS idx_facture_entity
    ON m38h_facture (entity);

-- ── Requête 3 : ca_mensuel ──
-- Problème : YEAR(datef) désactive idx_facture_datef existant
-- Solution : index composé (entity, datef) pour couvrir les deux filtres
CREATE INDEX IF NOT EXISTS idx_facture_entity_datef
    ON m38h_facture (entity, datef);

-- ── Requête 5 : commandes_mois ──
-- Problème : full scan sur m38h_commande (62 lignes, no index)
-- Solution : index sur (entity, date_commande) pour WHERE + GROUP BY
CREATE INDEX IF NOT EXISTS idx_commande_entity_date
    ON m38h_commande (entity, date_commande);

-- ── Requête 4 : stock_faible (amélioration) ──
-- Problème : filesort résiduel sur ORDER BY stock
-- Solution : index composé (entity, stock) pour couvrir WHERE + ORDER BY
CREATE INDEX IF NOT EXISTS idx_product_entity_stock
    ON m38h_product (entity, stock);

    
-- ============================================================
-- Vérification après application
-- ============================================================
SHOW INDEX FROM m38h_facture;
SHOW INDEX FROM m38h_paiement_facture;
SHOW INDEX FROM m38h_societe;
SHOW INDEX FROM m38h_commande;
SHOW INDEX FROM m38h_product;