WHITELIST_VERSION = "v1.1"

ALLOWED_TABLES = {
    "m38h_facture", "m38h_facturedet", "m38h_facture_fourn",
    "m38h_facture_fourn_det",
    "m38h_commande", "m38h_commandedet", "m38h_commande_fournisseur",
    "m38h_commande_fournisseur_det",
    "m38h_societe", "m38h_socpeople",
    "m38h_product", "m38h_product_stock", "m38h_product_price",
    "m38h_stock_mouvement", "m38h_entrepot",
    "m38h_paiement", "m38h_paiement_facture",
    "m38h_projet", "m38h_projet_task",
    "m38h_categorie", "m38h_categorie_product",
    "m38h_accounting_account", "m38h_accounting_bookkeeping",
    "m38h_bank", "m38h_bank_account",
    "m38h_user", "m38h_salary",
    "m38h_bom_bom", "m38h_bom_bom_line",
    "m38h_mrp_mo",
    "m38h_holiday", "m38h_usergroup",
    "m38h_const", "m38h_cashdaily", "m38h_cashcontrol"
}

ALLOWED_COLUMNS = {
"m38h_commande_fournisseur": {
    "rowid", "ref", "fk_soc", "date_commande", "total_ht", "total_ttc", "entity"
},
"m38h_commande_fournisseur_det": {
    "rowid", "fk_commande_fournisseur", "fk_product", "qty", "total_ht", "total_ttc", "entity"
},
"m38h_facture_fourn": {
    "rowid", "ref", "fk_soc", "datef", "total_ht", "total_ttc", "entity"
},
"m38h_facture_fourn_det": {
    "rowid", "fk_facture_fourn", "fk_product", "qty", "total_ht", "total_ttc", "entity"
},
"m38h_bom_bom": {
    "rowid", "ref", "fk_product", "qty", "entity"
},
"m38h_bom_bom_line": {
    "rowid", "fk_bom", "fk_product", "qty", "entity"
},
"m38h_mrp_mo": {
    "rowid", "ref", "fk_product", "qty", "planned_qty", "entity"
},
"m38h_holiday": {
    "rowid", "fk_user", "date_start", "date_end", "status", "entity"
},
"m38h_usergroup": {
    "rowid", "name", "entity"
},
"m38h_const": {
    "rowid", "name", "value", "entity"
},
"m38h_product_price": {
    "rowid", "fk_product", "price", "price_ttc", "entity"
},
"m38h_bank_account": {
    "rowid", "ref", "label", "bank", "code", "currency", "entity"
},
"m38h_accounting_account": {
    "rowid", "account_number", "label", "entity"
},
"m38h_accounting_bookkeeping": {
    "rowid", "doc_type", "doc_id", "account", "debit", "credit", "entity"
},
"m38h_user": {
    "rowid", "login", "name", "entity"
},
"m38h_salary": {
    "rowid", "fk_user", "amount", "date", "entity"
},
"m38h_commande_fournisseur": {
    "rowid", "ref", "fk_soc", "date_commande", "total_ht", "total_ttc", "entity"
},
"m38h_commande_fournisseur_det": {
    "rowid", "fk_commande_fournisseur", "fk_product", "qty", "total_ht", "total_ttc", "entity"
},
"m38h_facture_fourn": {
    "rowid", "ref", "fk_soc", "datef", "total_ht", "total_ttc", "entity"
},
"m38h_facture_fourn_det": {
    "rowid", "fk_facture_fourn", "fk_product", "qty", "total_ht", "total_ttc", "entity"
},
"m38h_product_price": {
    "rowid", "fk_product", "price", "price_ttc", "entity"
},
"m38h_holiday": {
    "rowid", "fk_user", "date_start", "date_end", "status", "entity"
},
"m38h_usergroup": {
    "rowid", "name", "entity"
},
"m38h_const": {
    "rowid", "name", "value", "entity"
},
"m38h_bank": {
    "rowid", "ref", "label", "bank", "code", "currency", "entity"
},
    "m38h_facture_fourn": {
        "rowid", "ref", "total_ht", "total_ttc",
        "fk_soc", "entity", "datef"
    },
    "m38h_cashdaily": {
        "rowid", "fk_user", "date_cash", "label", "amount", "fk_bank",
        "f_type", "account_type", "payment_method", "currency_code"
    },
    "m38h_cashcontrol": {
        "rowid", "fk_user", "date_start", "date_end", "start_amount",
        "end_amount", "total_sell", "total_paid", "total_change"
    },
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
    ("m38h_cashdaily", "m38h_bank"),
    ("m38h_cashdaily", "m38h_user"),
    ("m38h_cashcontrol", "m38h_user"),
    ("m38h_facture_fourn", "m38h_societe"),
    ("m38h_societe", "m38h_facture_fourn"),
    ("m38h_facture",    "m38h_societe"),
    ("m38h_societe",    "m38h_commande"),
    ("m38h_facture",    "m38h_paiement_facture"),
    ("m38h_product",    "m38h_commandedet"),
    ("m38h_commande",   "m38h_commandedet"),
    ("m38h_facture",    "m38h_facturedet"),
    ("m38h_product",    "m38h_facturedet"),
    ("m38h_commandedet", "m38h_product"),
    ("m38h_product",    "m38h_categorie_product"),
    ("m38h_categorie_product", "m38h_categorie"),
}
