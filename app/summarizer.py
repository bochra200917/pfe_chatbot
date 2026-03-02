#app/summarizer.py
def generate_summary(template_name: str, row_count: int):
    if row_count == 0:
        return "Aucun résultat trouvé."
    elif row_count == 1:
        return "1 résultat trouvé."
    else:
        return f"{row_count} résultats trouvés."