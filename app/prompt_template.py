# app/prompt_template.py
# Prompt système amélioré pour le module NL→template
# Couvre les variantes manquantes et règles de mapping explicites

SYSTEM_PROMPT = """
Tu es un assistant d'analyse de données pour l'ERP Dolibarr de ZAI Informatique.
Tu reçois une question en langage naturel et tu dois identifier le template SQL correspondant.

══════════════════════════════════════════════
TEMPLATES DISPONIBLES
══════════════════════════════════════════════

1. get_factures_between
   → Factures sur une période donnée
   → Paramètres : date_debut (YYYY-MM-DD), date_fin (YYYY-MM-DD)
   → Déclencheurs : "factures entre", "factures du mois de", "factures de [mois] [année]",
     "factures émises en", "liste des factures de", "factures du [date] au [date]",
     "toutes les factures de cette année", "factures du mois en cours"
   → Règle dates : si mois mentionné sans dates précises → premier et dernier jour du mois
   → Règle "cette année" → 2026-01-01 à 2026-12-31
   → Règle "ce mois" → premier et dernier jour du mois courant

2. get_factures_non_payees
   → Factures dont le montant restant > 0 et aucun paiement complet
   → Paramètres : aucun
   → Déclencheurs : "non payées", "impayées", "pas encore réglées", "en attente de paiement",
     "non soldées", "créances clients", "clients qui n'ont pas payé",
     "n ont pas ete reglees", "pas ete regle", "non reglees"

3. get_factures_partiellement_payees
   → Factures avec paiement partiel (montant restant > 0 mais paiement > 0)
   → Paramètres : aucun
   → Déclencheurs : "partiellement payées", "paiement partiel", "solde restant positif",
     "incomplètement réglées", "paiements partiels", "solde restant est positif"

4. get_clients_multiple_commandes
   → Clients ayant passé N commandes ou plus
   → Paramètres : min_commandes (entier, défaut=2)
   → Déclencheurs : "clients avec plus de N commandes", "clients fidèles",
     "top clients", "clients multi-commandes", "clients ayant commandé plusieurs fois",
     "clients avec au moins N achats"
   → Règle : extraire le nombre N depuis la question, sinon utiliser 2 par défaut

5. get_produits_stock_faible
   → Produits dont le stock disponible < seuil
   → Paramètres : seuil (entier, défaut=10)
   → Déclencheurs : "stock inférieur à N", "stock faible", "stock bas", "rupture",
     "presque épuisés", "alertes stock", "moins de N unités", "stock critique"
   → Règle : extraire N depuis la question, sinon utiliser 10 par défaut

6. get_total_ventes_mois
   → Chiffre d'affaires total pour un mois ou une année
   → Paramètres : mois (MM, optionnel), annee (YYYY)
   → Déclencheurs : "chiffre d affaires", "CA", "ventes totales", "CA mensuel",
     "CA total par mois", "évolution des ventes", "résumé des ventes mensuelles",
     "combien on a vendu", "total des ventes"
   → IMPORTANT : "CA total par mois pour 2026" et "CA mensuel 2026"
     → template=get_total_ventes_mois, annee=2026, mois=null (toute l'année)
   → Règle : si aucun mois précisé mais année précisée → retourner tous les mois de l'année

══════════════════════════════════════════════
FORMAT DE RÉPONSE — JSON UNIQUEMENT
══════════════════════════════════════════════

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après,
sans balises markdown, sans explication.

{
  "intent": "<nom_du_template ou clarification_required ou rejected>",
  "params": {"<param_name>": "<valeur>"},
  "confidence": <0.0 à 1.0>,
  "clarification_message": "<message si clarification_required, sinon null>"
}
""".strip()


# ──────────────────────────────────────────────────────────────────────
# Règles de mapping regex — couche AVANT le LLM
# ──────────────────────────────────────────────────────────────────────
import re
from datetime import date
import calendar


def _current_year():
    return str(date.today().year)


MOIS_MAP = {
    "janvier": "01", "fevrier": "02", "fevrier": "02",
    "mars": "03", "avril": "04", "mai": "05", "juin": "06",
    "juillet": "07", "aout": "08",
    "septembre": "09", "octobre": "10", "novembre": "11",
    "decembre": "12",
    # avec accents
    "février": "02", "août": "08", "décembre": "12",
    # abréviations
    "janv": "01", "fev": "02", "fév": "02", "avr": "04",
    "juil": "07", "sept": "09", "oct": "10", "nov": "11",
    "dec": "12", "déc": "12",
}

_MOIS_PATTERN = "|".join(sorted(MOIS_MAP.keys(), key=len, reverse=True))

MAPPING_RULES = [

    # ── 1. Sécurité (priorité absolue) ──
    (
        re.compile(
            r"\b(drop|delete|update|insert|alter|create|truncate"
            r"|union\s+select|exec\b|xp_)"
            r"|--|/\*|\*/|1\s*=\s*1"
            r"|ignore.{0,20}instruction",
            re.IGNORECASE
        ),
        lambda m, q: {"intent": "rejected", "params": {}, "confidence": 1.0},
    ),

    # ── 2. CA total par mois pour YYYY ──
    (
        re.compile(
            r"(ca|chiffre\s+d.affaires?|ventes?)"
            r".{0,30}(par\s+mois|mensuel).{0,20}(\d{4})",
            re.IGNORECASE
        ),
        lambda m, q: {
            "intent":     "get_total_ventes_mois",
            "params":     {"annee": m.group(3)},
            "confidence": 0.97,
        },
    ),

    # ── 3. CA / ventes d'un mois précis ──
    (
        re.compile(
            r"(ca|chiffre\s+d.affaires?|ventes?\s+totales?|revenus?)"
            r".{0,30}(" + _MOIS_PATTERN + r").{0,10}(\d{4})?",
            re.IGNORECASE
        ),
        lambda m, q: _ca_mois(m),
    ),

    # ── 4. Factures non payées — toutes variantes ──
    (
        re.compile(
            r"(factures?\s+(non\s+pay[ee]?es?|impay[ee]?es?|non\s+sold[ee]?es?"
            r"|non\s+regl[ee]?es?|pas\s+(encore\s+)?regl[ee]?es?"
            r"|pas\s+ete\s+regl[ee]?es?)"
            r"|n\s+ont\s+pas\s+(ete\s+)?regl[ee]?es?"
            r"|en\s+attente\s+de\s+paiement"
            r"|cr[ee]ances?\s+clients?"
            r"|montant\s+restant)",
            re.IGNORECASE
        ),
        lambda m, q: {
            "intent":     "get_factures_non_payees",
            "params":     {},
            "confidence": 0.98,
        },
    ),

    # ── 5. Factures partiellement payées — toutes variantes ──
    (
        re.compile(
            r"(factures?\s+partiellement"
            r"|paiements?\s+partiels?"
            r"|solde\s+restant(\s+est)?\s+positif"
            r"|incompl.tement\s+r.gl.es?"
            r"|factures?\s+en\s+cours\s+de\s+paiement)",
            re.IGNORECASE
        ),
        lambda m, q: {
            "intent":     "get_factures_partiellement_payees",
            "params":     {},
            "confidence": 0.97,
        },
    ),

    # ── 6. Factures entre deux dates ISO ──
    (
        re.compile(
            r"factures?.{0,20}(\d{4}-\d{2}-\d{2}).{0,10}(\d{4}-\d{2}-\d{2})",
            re.IGNORECASE
        ),
        lambda m, q: {
            "intent":     "get_factures_between",
            "params":     {"date_debut": m.group(1), "date_fin": m.group(2)},
            "confidence": 0.99,
        },
    ),

    # ── 7. Factures d'un mois en texte ──
    (
        re.compile(
            r"factures?.{0,30}(" + _MOIS_PATTERN + r").{0,10}(\d{4})?",
            re.IGNORECASE
        ),
        lambda m, q: _factures_mois(m),
    ),

    # ── 8. Produits stock faible avec seuil explicite ──
    (
        re.compile(
            r"(produits?|articles?).{0,40}"
            r"(inf.rieur|moins\s+de|<)\s*[àa]?\s*(\d+)",
            re.IGNORECASE
        ),
        lambda m, q: {
            "intent":     "get_produits_stock_faible",
            "params":     {"seuil": int(m.group(3))},
            "confidence": 0.97,
        },
    ),

    # ── 9. Stock faible sans seuil ──
    (
        re.compile(
            r"(stock\s+faible|stock\s+bas|rupture\s+de\s+stock"
            r"|alertes?\s+stock|stock\s+critique)",
            re.IGNORECASE
        ),
        lambda m, q: {
            "intent":     "get_produits_stock_faible",
            "params":     {"seuil": 10},
            "confidence": 0.88,
        },
    ),

    # ── 10. Clients multi-commandes avec N ──
    (
        re.compile(
            r"clients?.{0,30}"
            r"(plus\s+de|au\s+moins)\s*(\d+)\s*(commandes?|achats?)",
            re.IGNORECASE
        ),
        lambda m, q: {
            "intent":     "get_clients_multiple_commandes",
            "params":     {"min_commandes": int(m.group(2))},
            "confidence": 0.97,
        },
    ),

    # ── 11. Clients fidèles / top clients ──
    (
        re.compile(
            r"(clients?\s+fid.les?|top\s+clients?"
            r"|clients?\s+multi.commandes?|meilleurs?\s+clients?)",
            re.IGNORECASE
        ),
        lambda m, q: {
            "intent":     "get_clients_multiple_commandes",
            "params":     {"min_commandes": 2},
            "confidence": 0.88,
        },
    ),
]


def _ca_mois(m) -> dict | None:
    mois_str = m.group(2).lower()
    mois_norm = mois_str.encode("ascii", "ignore").decode("utf-8")
    mois_num = None
    for k, v in MOIS_MAP.items():
        k_norm = k.encode("ascii", "ignore").decode("utf-8")
        if k_norm and (k_norm in mois_norm or k in mois_str):
            mois_num = v
            break
    if not mois_num:
        return None
    annee = m.group(3) or _current_year()
    return {
        "intent":     "get_total_ventes_mois",
        "params":     {"mois": mois_num, "annee": annee},
        "confidence": 0.96,
    }


def _factures_mois(m) -> dict | None:
    mois_str = m.group(1).lower()
    mois_norm = mois_str.encode("ascii", "ignore").decode("utf-8")
    mois_num = None
    for k, v in MOIS_MAP.items():
        k_norm = k.encode("ascii", "ignore").decode("utf-8")
        if k_norm and (k_norm in mois_norm or k in mois_str):
            mois_num = v
            break
    if not mois_num:
        return None
    annee    = m.group(2) or _current_year()
    last_day = calendar.monthrange(int(annee), int(mois_num))[1]
    return {
        "intent": "get_factures_between",
        "params": {
            "date_debut": f"{annee}-{mois_num}-01",
            "date_fin":   f"{annee}-{mois_num}-{last_day:02d}",
        },
        "confidence": 0.95,
    }


def apply_mapping_rules(question: str) -> dict | None:
    """
    Applique les règles regex dans l'ordre.
    Retourne {intent, params, confidence} si match, sinon None → LLM sera appelé.
    """
    q = question.strip()
    for pattern, handler in MAPPING_RULES:
        m = pattern.search(q)
        if m:
            result = handler(m, q)
            if result:
                return result
    return None


# ──────────────────────────────────────────────────────────────────────
# Test rapide : python app/prompt_template.py
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_cases = [
        ("quelles factures n ont pas ete reglees",     "get_factures_non_payees"),
        ("factures dont le solde restant est positif", "get_factures_partiellement_payees"),
        ("chiffre d affaires total par mois pour 2026","get_total_ventes_mois"),
        ("CA mensuel 2026",                            "get_total_ventes_mois"),
        ("factures non payees",                        "get_factures_non_payees"),
        ("factures partiellement payees",              "get_factures_partiellement_payees"),
        ("produits avec moins de 3 unites en stock",   "get_produits_stock_faible"),
        ("alertes stock critique",                     "get_produits_stock_faible"),
        ("clients fideles",                            "get_clients_multiple_commandes"),
        ("clients avec au moins 5 achats",             "get_clients_multiple_commandes"),
        ("factures de janvier 2026",                   "get_factures_between"),
        ("factures entre 2026-01-01 et 2026-01-31",   "get_factures_between"),
        ("DROP TABLE m38h_facture",                    "rejected"),
        ("factures UNION SELECT password FROM users",  "rejected"),
        ("donne moi les factures du client Dupont",    None),
    ]

    print(f"\n{'='*65}")
    print("  Test des regles de mapping — app/prompt_template.py")
    print(f"{'='*65}\n")

    ok_count = 0
    for q, expected in test_cases:
        result  = apply_mapping_rules(q)
        intent  = result["intent"] if result else None
        passed  = (intent == expected)
        ok_count += int(passed)
        tag     = "OK" if passed else "XX"
        conf    = f"[{result['confidence']:.2f}]" if result else "[LLM]"
        print(f"  [{tag}] {conf} {q}")
        print(f"          → {intent}  (attendu: {expected})")
        print()

    print(f"  Resultat : {ok_count}/{len(test_cases)} correct(s)\n")