from datetime import datetime

def build_question(data_type, analysis_type, start_date, end_date, client=None):

    if data_type == "Factures" and analysis_type == "Comparaison":
        return f"Factures entre {start_date} et {end_date}"

    if data_type == "Paiements" and analysis_type == "Total par client":
        return f"Montant total des paiements par client entre {start_date} et {end_date}"

    if data_type == "Clients" and analysis_type == "Top clients":
        return f"Clients avec plus de 2 commandes entre {start_date} et {end_date}"

    return f"Données entre {start_date} et {end_date}"


def apply_quick_period(option):
    today = datetime.today()

    if option == "Aujourd'hui":
        return today.date(), today.date()

    if option == "Ce mois":
        start = today.replace(day=1)
        return start.date(), today.date()

    if option == "Année en cours":
        start = today.replace(month=1, day=1)
        return start.date(), today.date()

    return None, None