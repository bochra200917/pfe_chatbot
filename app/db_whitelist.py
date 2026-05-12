# app/db_whitelist.py
WHITELIST_VERSION = "v1.1"

ALLOWED_TABLES = {
    "m38h_categorie",            
    "m38h_categorie_product",
    "m38h_facture",
    "m38h_facturedet",
    "m38h_societe",
    "m38h_socpeople",
    "m38h_paiement",
    "m38h_paiement_facture",
    "m38h_product",
    "m38h_product_stock",
    "m38h_stock_mouvement",
    "m38h_entrepot",
    "m38h_commande",
    "m38h_commandedet",
    "m38h_projet",
    "m38h_projet_task",
}

ALLOWED_COLUMNS = {
    "m38h_facture": {
        "ref", "total_ht", "total_ttc", "datef",
        "fk_soc", "entity", "rowid", "fk_statut"
    },
    "m38h_societe": {
        "rowid", "nom", "entity", "email", "phone"
    },
    "m38h_commande": {
        "rowid", "fk_soc", "entity",
        "date_commande",
        "total_ht",
        "total_ttc",
        "statut",
        "ref",
    },
    "m38h_commandedet": {
        "rowid", "fk_commande", "fk_product",
        "qty",
        "total_ht", "total_ttc",
        "entity",
    },
    "m38h_categorie": {
        "rowid", "label", "description", "entity", "fk_parent"
    },
    "m38h_categorie_product": {
        "rowid", "fk_categorie", "fk_product"
    },
    "m38h_product": {
        "ref", "label", "stock", "entity", "rowid",
    },
    "m38h_paiement_facture": {
        "fk_facture", "amount", "rowid",
    },
    "m38h_paiement": {
        "rowid", "datep", "amount", "fk_bank", "entity",
    },
    "m38h_facturedet": {
        "rowid", "fk_facture", "fk_product",
        "qty", "total_ht", "total_ttc", "entity",
    },
    "m38h_projet": {
        "rowid", "ref", "title", "dateo", "fk_soc", "entity"
    },
    "m38h_socpeople": {
        "rowid", "fk_soc", "lastname", "firstname", "email"
    },
    "m38h_product_stock": {
        "rowid", "fk_product", "fk_entrepot", "reel"
    },
    "m38h_stock_mouvement": {
        "rowid", "fk_product", "qty", "datem"
    },
    "m38h_entrepot": {
        "rowid", "label", "entity"
    },
    "m38h_projet_task": {
        "rowid", "fk_projet", "label", "dateo"
    },
}

ALLOWED_JOINS = {
    ("m38h_facture",    "m38h_societe"),
    ("m38h_societe",    "m38h_commande"),
    ("m38h_facture",    "m38h_paiement_facture"),
    # ── FIX 2 : jointures pour produits jamais commandés ──
    ("m38h_product",    "m38h_commandedet"),    # ← LEFT JOIN pour produits sans commande
    ("m38h_commande",   "m38h_commandedet"),    # ← jointure commande ↔ détail
    ("m38h_facture",    "m38h_facturedet"),
    ("m38h_product",    "m38h_facturedet"),
    ("m38h_commandedet", "m38h_product"),
    ("m38h_product", "m38h_categorie_product"),
    ("m38h_categorie_product", "m38h_categorie"),
}