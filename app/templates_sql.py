# app/templates_sql.py

def get_factures_between():
    return """
    SELECT
        f.rowid         AS id,
        f.ref           AS facture_ref,
        s.nom           AS client,
        f.total_ht,
        f.total_ttc,
        f.datef         AS date_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.datef BETWEEN :start_date AND :end_date
      AND f.entity = 1
    ORDER BY f.datef ASC
    LIMIT 200
    """


def get_factures_par_client():
    return """
    SELECT
        f.rowid         AS id,
        f.ref           AS facture_ref,
        f.total_ht,
        f.total_ttc,
        f.datef         AS date_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE s.nom = :client
      AND f.entity = 1
    ORDER BY f.datef ASC
    LIMIT 100
    """


def get_factures_negatives():
    return """
    SELECT
        f.rowid         AS id,
        f.ref           AS facture_ref,
        s.nom           AS client,
        f.total_ht,
        f.total_ttc,
        f.datef         AS date_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.total_ht < 0
      AND f.entity = 1
    ORDER BY f.datef ASC
    LIMIT 100
    """


def get_clients_multiple_commandes():
    return """
    SELECT
        c.rowid         AS id,
        c.nom           AS client_nom,
        COUNT(co.rowid) AS nb_commandes
    FROM m38h_societe c
    JOIN m38h_commande co ON co.fk_soc = c.rowid
    WHERE c.entity = 1
    GROUP BY c.rowid, c.nom
    HAVING nb_commandes > :min_commandes
    ORDER BY nb_commandes DESC
    LIMIT 100
    """


def get_produits_stock_faible():
    return """
    SELECT
        p.rowid         AS id,
        p.ref           AS produit_ref,
        p.label         AS produit_nom,
        p.stock         AS stock_disponible
    FROM m38h_product p
    WHERE p.stock < :stock_min
      AND p.entity = 1
    ORDER BY p.stock ASC
    LIMIT 100
    """

def get_total_ventes_mois():
    return """
    SELECT
        DATE_FORMAT(f.datef, '%Y-%m') AS mois,
        SUM(f.total_ht) AS CA_HT,
        SUM(f.total_ttc) AS CA_TTC
    FROM m38h_facture f
    WHERE YEAR(f.datef) = :year
      AND MONTH(f.datef) = :month
      AND f.entity = 1
    GROUP BY mois
    LIMIT 100
    """


def get_factures_non_payees():
    return """
    SELECT
        f.rowid         AS id,
        f.ref           AS facture_ref,
        s.nom           AS client,
        f.total_ht,
        f.total_ttc,
        f.datef         AS date_facture,
        COALESCE(SUM(pf.amount), 0) AS montant_paye,
        (f.total_ttc - COALESCE(SUM(pf.amount), 0)) AS montant_restant
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    LEFT JOIN m38h_paiement_facture pf ON pf.fk_facture = f.rowid
    WHERE f.entity = 1
      AND f.datef BETWEEN :start_date AND :end_date
    GROUP BY f.rowid, f.ref, s.nom, f.total_ht, f.total_ttc, f.datef
    HAVING (f.total_ttc - COALESCE(SUM(pf.amount), 0)) > 0
    ORDER BY f.datef ASC
    LIMIT 100
    """

def get_factures_partiellement_payees():
    return """
    SELECT
        f.rowid         AS id,
        f.ref           AS facture_ref,
        s.nom           AS client,
        f.total_ht,
        f.total_ttc,
        f.datef         AS date_facture,
        COALESCE(SUM(pf.amount), 0)                           AS montant_paye,
        (f.total_ttc - COALESCE(SUM(pf.amount), 0))          AS montant_restant
    FROM m38h_facture f
    LEFT JOIN m38h_societe s         ON f.fk_soc      = s.rowid
    LEFT JOIN m38h_paiement_facture pf ON pf.fk_facture = f.rowid
    WHERE f.entity = 1
      AND f.datef BETWEEN :start_date AND :end_date
    GROUP BY f.rowid, f.ref, s.nom, f.total_ht, f.total_ttc, f.datef
    HAVING COALESCE(SUM(pf.amount), 0) > 0
       AND (f.total_ttc - COALESCE(SUM(pf.amount), 0)) > 0
    ORDER BY f.datef ASC
    LIMIT :limit
    """

def get_total_paiements():
    return """
    SELECT
        s.nom AS client,
        SUM(pf.amount) AS total_paiements
    FROM m38h_paiement_facture pf
    LEFT JOIN m38h_facture f ON pf.fk_facture = f.rowid
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.datef BETWEEN :start_date AND :end_date
      AND f.entity = 1
    GROUP BY s.nom
    ORDER BY total_paiements DESC
    LIMIT 100
    """

def get_paiements_par_client():
    return """
    SELECT
        s.nom AS client,
        SUM(p.amount) AS total_paiements
    FROM m38h_paiement p
    JOIN m38h_paiement_facture pf ON pf.fk_paiement = p.rowid
    JOIN m38h_facture f ON f.rowid = pf.fk_facture
    JOIN m38h_societe s ON s.rowid = f.fk_soc
    WHERE p.datep BETWEEN :start_date AND :end_date
    GROUP BY s.nom
    ORDER BY total_paiements DESC
    LIMIT :limit
    """

def get_commandes_par_mois():
    return """
    SELECT
        COUNT(c.rowid)                        AS nb_commandes,
        DATE_FORMAT(c.date_commande, '%Y-%m') AS mois,
        ROUND(SUM(c.total_ht), 3)             AS total_ht,
        ROUND(SUM(c.total_ttc), 3)            AS total_ttc
    FROM m38h_commande c
    WHERE YEAR(c.date_commande)  = :annee
      AND MONTH(c.date_commande) = :mois
      AND c.entity = 1
    GROUP BY mois
    LIMIT 200
    """


def get_top_clients_ca():
    return """
    SELECT
        s.rowid                      AS id,
        s.nom                        AS client,
        COUNT(f.rowid)               AS nb_factures,
        ROUND(SUM(f.total_ht), 3)    AS CA_HT,
        ROUND(SUM(f.total_ttc), 3)   AS CA_TTC
    FROM m38h_facture f
    JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.entity = 1
      AND f.fk_statut != 0
    GROUP BY s.rowid, s.nom
    ORDER BY CA_TTC DESC
    LIMIT 200
    """

def get_liste_clients_simple():
    return """
    SELECT
        s.rowid         AS id,
        s.nom           AS client,
        s.email,
        s.phone         AS telephone
    FROM m38h_societe s
    WHERE s.entity = 1
      AND s.client = 1
    ORDER BY s.nom ASC
    LIMIT 200
    """

def get_produits_non_commandes():
    return """
    SELECT
        p.rowid         AS id,
        p.ref           AS produit_ref,
        p.label         AS produit_nom,
        p.stock
    FROM m38h_product p
    LEFT JOIN m38h_commandedet cd ON cd.fk_product = p.rowid
    WHERE cd.fk_product IS NULL
      AND p.entity = 1
    ORDER BY p.label ASC
    LIMIT 100
    """

def get_factures_non_payees_30j():
    return """
    SELECT
        f.rowid         AS id,
        f.ref           AS facture_ref,
        s.nom           AS client,
        f.total_ht,
        f.total_ttc,
        f.datef         AS date_facture,
        COALESCE(SUM(pf.amount), 0)                           AS montant_paye,
        (f.total_ttc - COALESCE(SUM(pf.amount), 0))          AS montant_restant,
        DATEDIFF(CURDATE(), f.datef)                          AS jours_retard
    FROM m38h_facture f
    LEFT JOIN m38h_societe s         ON f.fk_soc      = s.rowid
    LEFT JOIN m38h_paiement_facture pf ON pf.fk_facture = f.rowid
    WHERE f.entity = 1
      AND f.datef <= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
    GROUP BY f.rowid, f.ref, s.nom, f.total_ht, f.total_ttc, f.datef
    HAVING (f.total_ttc - COALESCE(SUM(pf.amount), 0)) > 0
    ORDER BY f.datef ASC
    LIMIT 100
    """

def get_top_produits_commandes():
    return """
    SELECT
        p.rowid                  AS id,
        p.ref                    AS produit_ref,
        p.label                  AS produit_nom,
        SUM(cd.qty)              AS quantite_commandee,
        COUNT(cd.rowid)          AS nb_lignes_commande
    FROM m38h_product p
    JOIN m38h_commandedet cd ON cd.fk_product = p.rowid
    WHERE p.entity = 1
    GROUP BY p.rowid, p.ref, p.label
    ORDER BY quantite_commandee DESC
    LIMIT 200
    """

def get_ca_par_trimestre():
    """CA total par trimestre pour une année donnée."""
    return """
    SELECT
        QUARTER(f.datef)               AS trimestre,
        CONCAT('T', QUARTER(f.datef))  AS libelle,
        ROUND(SUM(f.total_ht), 3)      AS total_ht,
        ROUND(SUM(f.total_ttc), 3)     AS total_ttc,
        COUNT(f.rowid)                 AS nb_factures
    FROM m38h_facture f
    WHERE YEAR(f.datef) = :annee
      AND f.entity = 1
    GROUP BY QUARTER(f.datef)
    ORDER BY trimestre ASC
    LIMIT 4
    """

def get_factures_payees():
    return """
    SELECT
        f.rowid         AS id,
        f.ref           AS facture_ref,
        s.nom           AS client,
        f.total_ht,
        f.total_ttc,
        f.datef         AS date_facture,
        COALESCE(SUM(pf.amount), 0)                      AS montant_paye,
        (f.total_ttc - COALESCE(SUM(pf.amount), 0))     AS montant_restant
    FROM m38h_facture f
    LEFT JOIN m38h_societe s           ON f.fk_soc      = s.rowid
    LEFT JOIN m38h_paiement_facture pf ON pf.fk_facture = f.rowid
    WHERE f.entity = 1
    GROUP BY f.rowid, f.ref, s.nom, f.total_ht, f.total_ttc, f.datef
    HAVING COALESCE(SUM(pf.amount), 0) >= f.total_ttc
       AND COALESCE(SUM(pf.amount), 0) > 0
    ORDER BY f.datef DESC
    LIMIT 100
    """

def get_avoirs():
    return """
    SELECT
        f.rowid         AS id,
        f.ref           AS avoir_ref,
        s.nom           AS client,
        f.total_ht,
        f.total_ttc,
        f.datef         AS date_avoir,
        f.type          AS type_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.entity = 1
      AND f.type = 2
    ORDER BY f.datef DESC
    LIMIT 100
    """

# ─── Mapping template_name → fonction SQL ─────────────────────────────────────
TEMPLATE_MAPPING = {
    "get_factures_payees":            get_factures_payees,
    "get_factures_between":           get_factures_between,
    "get_factures_par_client":        get_factures_par_client,
    "get_factures_negatives":         get_factures_negatives,
    "get_clients_multiple_commandes": get_clients_multiple_commandes,
    "get_produits_stock_faible":      get_produits_stock_faible,
    "get_total_ventes_mois":          get_total_ventes_mois,
    "get_factures_non_payees":        get_factures_non_payees,
    "get_factures_partiellement_payees": get_factures_partiellement_payees,
    "get_total_paiements":            get_total_paiements,
    "get_commandes_par_mois":         get_commandes_par_mois,
    "get_top_clients_ca":             get_top_clients_ca,
    "liste_clients_simple":           get_liste_clients_simple,
    "get_produits_non_commandes": get_produits_non_commandes,
    "get_factures_non_payees_30j": get_factures_non_payees_30j,
    "get_top_produits_commandes": get_top_produits_commandes,
    "get_ca_par_trimestre": get_ca_par_trimestre,
    "get_low_stock_products": get_produits_stock_faible,
    "get_produits_stock_faible": get_produits_stock_faible,
    "get_produits_non_commandes": get_produits_non_commandes,
    "get_top_clients_ca": get_top_clients_ca,
    "get_avoirs": get_avoirs,
    "get_paiements_par_client": get_paiements_par_client,
}