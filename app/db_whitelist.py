# app/db_whitelist.py
WHITELIST_VERSION = "v1.0"

ALLOWED_TABLES = {
    "m38h_facture",
    "m38h_societe",
    "m38h_commande",
    "m38h_product",
    "m38h_paiement_facture"
}

ALLOWED_COLUMNS = {
    "m38h_facture": {
        "ref", "total_ht", "total_ttc", "datef",
        "fk_soc", "entity", "rowid"
    },
    "m38h_societe": {
        "rowid", "nom", "entity"
    },
    "m38h_commande": {
        "rowid", "fk_soc"
    },
    "m38h_product": {
        "ref", "label", "stock", "entity"
    },
    "m38h_paiement_facture": {
        "fk_facture", "amount"
    }
}

ALLOWED_JOINS = {
    ("m38h_facture", "m38h_societe"),
    ("m38h_societe", "m38h_commande"),
    ("m38h_facture", "m38h_paiement_facture")
}