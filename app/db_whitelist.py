# app/db_whitelist.py
WHITELIST_VERSION = "v1.1"

ALLOWED_TABLES = {
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
    # ── FIX 1 : colonnes complètes pour m38h_commande ──
    "m38h_commande": {
        "rowid", "fk_soc", "entity",
        "date_commande",   # ← manquait — utilisé dans WHERE YEAR/MONTH
        "total_ht",        # ← manquait — utilisé dans SUM
        "total_ttc",       # ← manquait — utilisé dans SUM
        "statut",
        "ref",
    },
    # ── FIX 2 : colonnes pour m38h_commandedet ──
    "m38h_commandedet": {
    "rowid", "fk_commande", "fk_product",
    "qty",
    "total_ht", "total_ttc",
    "entity",
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
    "rowid",
    "ref",
    "title",
    "dateo",
    "fk_soc",
    "entity"
    },
}
ALLOWED_COLUMNS["m38h_socpeople"] = {
    "rowid", "fk_soc", "lastname", "firstname", "email"
}

ALLOWED_COLUMNS["m38h_product_stock"] = {
    "rowid", "fk_product", "fk_entrepot", "reel"
}

ALLOWED_COLUMNS["m38h_stock_mouvement"] = {
    "rowid", "fk_product", "qty", "datem"
}

ALLOWED_COLUMNS["m38h_entrepot"] = {
    "rowid", "label", "entity"
}

ALLOWED_COLUMNS["m38h_projet_task"] = {
    "rowid", "fk_projet", "label", "dateo"
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
}