# app/suggestion_engine.py
# Génère des propositions contextuelles après chaque réponse du chatbot

def generate_suggestions(intent: str, params: dict) -> list:
    """
    Génère des suggestions d'actions suivantes selon l'intent détecté.
    Chaque suggestion est une question que l'utilisateur peut poser directement.
    """

    year  = params.get("year", "2026")
    month = params.get("month", "")
    client = params.get("client", "")

    if intent == "get_total_ventes_mois":
        # Déterminer le mois précédent
        prev_month = str(int(month) - 1).zfill(2) if month and int(month) > 1 else "12"
        prev_year  = year if (month and int(month) > 1) else str(int(year) - 1)
        next_month = str(int(month) + 1).zfill(2) if month and int(month) < 12 else "01"
        next_year  = year if (month and int(month) < 12) else str(int(year) + 1)

        return [
            f"Chiffre d'affaires de {_month_name(prev_month)} {prev_year}",
            f"Chiffre d'affaires de {_month_name(next_month)} {next_year}",
            f"Évolution des ventes pour l'année {year}",
            f"Factures entre {year}-01-01 et {year}-12-31",
        ]

    elif intent == "get_factures_non_payees":
        return [
            "Factures partiellement payées",
            "Clients avec plus de 2 commandes",
            f"Factures entre {year}-01-01 et {year}-12-31",
            "Factures négatives",
        ]

    elif intent == "get_factures_partiellement_payees":
        return [
            "Factures non payées",
            "Factures entre 2026-01-01 et 2026-03-31",
            "Clients avec plus de 2 commandes",
            "Top clients par CA",  
        ]

    elif intent == "get_factures_between":
        start = params.get("start_date", "")
        end   = params.get("end_date", "")
        return [
            "Factures non payées",
            "Factures partiellement payées",
            f"Chiffre d'affaires de janvier {year}",
            "Factures négatives",
        ]

    elif intent == "get_factures_par_client":
        return [
            f"Clients avec plus de 2 commandes",
            "Factures non payées",
            f"Factures entre 2026-01-01 et 2026-03-31",
            "Top clients par CA",  
        ]

    elif intent == "get_factures_negatives":
        return [
            "Factures non payées",
            "Factures partiellement payées",
            f"Chiffre d'affaires de janvier {year}",
            "Top clients par CA",  
        ]

    elif intent == "get_clients_multiple_commandes":
        return [
            "Factures non payées",
            "Factures entre 2026-01-01 et 2026-03-31",
            f"Chiffre d'affaires de janvier {year}",
            "Top clients par CA",  
        ]

    elif intent == "get_produits_stock_faible":
        return [
            "Produits avec stock inférieur à 3",
            "Produits avec stock inférieur à 10",
            "Clients avec plus de 2 commandes",
            "Top clients par CA",
        ]

    elif intent == "get_total_paiements":
        return [
            "Factures non payées",
            f"Chiffre d'affaires de janvier {year}",
            "Factures partiellement payées",
            "Top clients par CA",  
        ]
    
    elif intent == "get_factures_payees":
        return [
            "Factures non payées",
            "Factures partiellement payées",
            "Top clients par CA",
            "Chiffre d'affaires de janvier 2026",           
        ]
    
    elif intent == "get_avoirs":
            return [
                "Factures non payées",
                "Factures partiellement payées",
                "Factures négatives",
                "Top clients par CA",  
            ]

    else:
        return [
            "Factures non payées",
            "Produits avec stock inférieur à 5",
            "Clients avec plus de 2 commandes",
            f"Chiffre d'affaires de janvier {year}",
        ]

def _month_name(month: str) -> str:
    """Convertit un numéro de mois en nom français"""
    names = {
        "01": "janvier", "02": "février", "03": "mars",
        "04": "avril",   "05": "mai",     "06": "juin",
        "07": "juillet", "08": "août",    "09": "septembre",
        "10": "octobre", "11": "novembre","12": "décembre"
    }
    return names.get(month, month)