def get_factures_between():
    return """
    SELECT
        f.ref AS facture_ref, 
        s.nom AS client,
        f.total_ht,
        f.total_ttc,
        f.datef AS date_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.datef BETWEEN :start_date AND :end_date
      AND f.entity = 1
    ORDER BY f.datef ASC
    """


def get_factures_par_client():
    return """
    SELECT 
        f.ref AS facture_ref,
        f.total_ht,
        f.total_ttc,
        f.datef AS date_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE s.nom = :client
      AND f.entity = 1
    ORDER BY f.datef ASC
    """


def get_factures_negatives():
    return """
    SELECT 
        f.ref AS facture_ref,
        s.nom AS client,
        f.total_ht,
        f.total_ttc,
        f.datef AS date_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.total_ht < 0
      AND f.entity = 1
    ORDER BY f.datef ASC
    """


def get_clients_multiple_commandes():
    return """
    SELECT c.rowid AS client_id,
           c.nom AS client_nom,
           COUNT(co.rowid) AS nb_commandes
    FROM m38h_societe c
    JOIN m38h_commande co ON co.fk_soc = c.rowid
    WHERE c.entity = 1
    GROUP BY c.rowid, c.nom
    HAVING nb_commandes > :min_commandes
    ORDER BY nb_commandes DESC
    """


def get_produits_stock_faible():
    return """
    SELECT p.ref AS produit_ref, 
           p.label AS produit_nom, 
           p.stock AS stock_disponible 
    FROM m38h_product p 
    WHERE p.stock < :stock_min
      AND p.entity = 1
    ORDER BY p.stock ASC
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
    """

def get_factures_non_payees():
    return """
    SELECT 
        f.ref AS facture_ref,
        s.nom AS client,
        f.total_ht,
        f.total_ttc,
        f.datef AS date_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.paye = 0
      AND f.entity = 1
    ORDER BY f.datef ASC
    """

def get_factures_partiellement_payees():
    return """
    SELECT 
        f.ref AS facture_ref,
        s.nom AS client,
        f.total_ht,
        f.total_ttc,
        f.datef AS date_facture
    FROM m38h_facture f
    LEFT JOIN m38h_societe s ON f.fk_soc = s.rowid
    WHERE f.paye = 1
      AND f.total_ht > f.total_ttc
      AND f.entity = 1
    ORDER BY f.datef ASC
    """