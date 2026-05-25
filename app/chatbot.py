# app/chatbot.py
import os
import json as _json_templates
import re
import unicodedata
import time
from app.templates_sql import TEMPLATE_MAPPING
from app.db import execute_query
from app.logger import log_query
from app.sql_security import detect_injection
from app.chatbot_v3 import run_llm_pipeline
from app.sql_security import validate_sql_query
from app.cache import chatbot_cache
from app.suggestion_engine import generate_suggestions
from app.prompt_template import apply_mapping_rules
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

import logging

logger = logging.getLogger(__name__)

MONTHS = {
    "janv": "01", "fév": "02", "fev": "02", "avr": "04",
    "juil": "07", "sept": "09", "oct": "10", "nov": "11",
    "dec": "12", "déc": "12", "janvier": "01", "fevrier": "02",
    "février": "02", "mars": "03", "avril": "04", "mai": "05",
    "juin": "06", "juillet": "07", "aout": "08", "août": "08",
    "septembre": "09", "octobre": "10", "novembre": "11",
    "decembre": "12", "décembre": "12"
}

COMPLEX_KEYWORDS = [
    "semestre",
    "mais pas", "sauf en", "pas en",
    "jamais commandé", "n ont jamais", "n a jamais",
    "comparer", "comparaison",
]

hybrid_engine = None


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return text.encode("ascii", "ignore").decode("utf-8")


# Mots qui ne font PAS partie d'un nom de client
_STOP_WORDS = {
    "avec", "et", "ou", "pour", "de", "du", "des", "les", "la", "le",
    "total", "ht", "ttc", "montant", "facture", "factures", "entre",
    "depuis", "jusqu", "par", "sur", "en", "au", "aux", "un", "une",
    "non", "pas", "plus", "moins",
}


def _extract_client_name(q: str) -> str | None:
    # Pattern 1 : "client <nom>"
    m = re.search(
        r'\bclient\s+([a-zA-ZÀ-ÿ0-9][a-zA-ZÀ-ÿ0-9_\-\s]{0,40})',
        q, re.IGNORECASE
    )
    if not m and "facture" in q:
        # Pattern 2 : "factures de/du <nom>"
        m = re.search(
            r'\bfactures?\s+(?:de|du|d\')\s+([a-zA-ZÀ-ÿ0-9][a-zA-ZÀ-ÿ0-9_\-\s]{0,40})',
            q,
            re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).strip()
    tokens = raw.split()
    clean_tokens = []
    for tok in tokens:
        if tok.lower() in _STOP_WORDS:
            break
        clean_tokens.append(tok)
    client = " ".join(clean_tokens).strip()
    return client if client else None


def match_question(question: str):
    q = normalize(question)

    # ── CA par trimestre ──────────────────────────────────────
    if "trimestre" in q and any(
        w in q for w in [
            "ca",
            "chiffre",
            "vente",
            "depense",
            "total"]):
        match_year = re.search(r'\b(20\d{2})\b', q)
        annee = match_year.group(1) if match_year else "2026"
        return "get_ca_par_trimestre", {"annee": annee}

    # ── EXCLUSION PRIORITAIRE : questions complexes → LLM ──

    if any(kw in q for kw in COMPLEX_KEYWORDS):
        return None, None  # → force passage au LLM

    # ══════════════════════════════════════════════════════════════════
    # PRIORITÉ HAUTE — patterns spécifiques avant les patterns généraux
    # ══════════════════════════════════════════════════════════════════

    # ── Top clients par CA ─────────────────────────────────────────
    if (
        any(w in q for w in [
            "top", "meilleur", "eleve", "plus grand", "plus important",
            "plus haut", "chiffre affaires le plus", "plus eleve",
            "les plus eleve", "le plus eleve"
        ])
        and
        any(w in q for w in ["client", "societe"])
    ):
        match_n = re.search(r'\b(\d+)\b', q)
        limit = int(match_n.group(1)) if match_n else 5
        return "get_top_clients_ca", {"limit": limit}

    # ── Commandes par mois — PRIORITÉ HAUTE ───────────────────────
    # ── Commandes par mois — PRIORITÉ HAUTE ───────────────────────
    if (
        "commande" in q
        and any(w in q for w in ["combien", "nombre", "total"])
        and not any(w in q for w in ["facture", "vente", "ca", "chiffre"])
        # ← AJOUT
        and not any(w in q for w in ["ligne", "distinct", "grand", "plus grand", "jamais"])
    ):
        for month_key, month_num in MONTHS.items():
            if month_key in q:
                match_year = re.search(r'\b(20\d{2})\b', q)
                year = match_year.group(1) if match_year else "2026"
                return "get_commandes_par_mois", {
                    "annee": year, "mois": month_num}
        match_ym = re.search(r'(\d{4})-(\d{2})', q)
        if match_ym:
            return "get_commandes_par_mois", {
                "annee": match_ym.group(1),
                "mois": match_ym.group(2)
            }
        if any(
            w in q for w in [
                "combien",
                "nombre",
                "total",
                "liste",
                "affiche"]):
            from datetime import datetime
            now = datetime.today()
            return "get_commandes_par_mois", {
                "annee": str(now.year),
                "mois": str(now.month).zfill(2)
            }

    # ── Liste clients simple ───────────────────────────────────────
    if (
        "client" in q
        and any(w in q for w in ["liste", "tous", "affiche", "donne"])
        and not any(w in q for w in ["commande", "facture", "top", "meilleur"])
    ):
        return "liste_clients_simple", {}

    # ══════════════════════════════════════════════════════════════════
    # PATTERNS EXISTANTS
    # ══════════════════════════════════════════════════════════════════

    match_ym = re.search(r'(\d{4})-(\d{2})(?!-\d{2})', q)
    if match_ym and any(w in q for w in ["total", "ventes", "chiffre", "ca"]):
        return "get_total_ventes_mois", {
            "year": match_ym.group(1), "month": match_ym.group(2)}

    match = re.search(r'(\d{4}-\d{2}-\d{2}).*(\d{4}-\d{2}-\d{2})', q)
    if match:
        # Ne pas retourner get_factures_between si la question concerne les
        # achats fournisseurs
        if not any(
            term in q for term in [
                "achat",
                "fournisseur",
                "entrepot",
                "magasin",
                "reception"]):
            return "get_factures_between", {
                "start_date": match.group(1), "end_date": match.group(2)}

    if "partiellement pay" in q or "partiel" in q:
        return "get_factures_partiellement_payees", {}

    # Dans match_question(), AVANT le bloc "non pay" existant :

    # ── Factures non payées AVEC dates ──────────────────────────
    match_dates = re.search(r'(\d{4}-\d{2}-\d{2}).*(\d{4}-\d{2}-\d{2})', q)
    if match_dates and any(w in q for w in ["non pay", "impaye", "non regle"]):
        return "get_factures_non_payees", {
            "start_date": match_dates.group(1),
            "end_date": match_dates.group(2)
        }

    # ── Factures non payées SANS dates (toutes) ──────────────────
    if ("non pay" in q or "impaye" in q or "non regle" in q
            or "pas regle" in q or "montant restant" in q):
        from datetime import date as _date
        today = _date.today()
        return "get_factures_non_payees", {
            "start_date": "2000-01-01",   # depuis toujours
            "end_date": str(today)
        }

    # ── Factures non payées depuis N jours — PRIORITÉ SUR le template générique ──
    match_jours = re.search(r'(\d+)\s*jours?', q)
    if match_jours and any(
        w in q for w in [
            "non pay",
            "impaye",
            "non regle",
            "retard"]):
        return "get_factures_non_payees_30j", {}

    if any(
        w in q for w in [
            "30 jours",
            "trente jours",
            "depuis plus",
            "depuis plus de",
            "un mois",
            "plus d un mois",
            "plus d'un mois"]):
        if any(
            w in q for w in [
                "non pay",
                "impaye",
                "non regle",
                "retard",
                "facture"]):
            return "get_factures_non_payees_30j", {}

    if ("non pay" in q or "impaye" in q or "non regle" in q
            or "pas regle" in q or "pas ete regle" in q
            or "n ont pas" in q or "montant restant" in q):
        return "get_factures_non_payees", {}

    if "paiement partiel" in q or "cours de paiement" in q:
        return "get_factures_partiellement_payees", {}

    # Factures payées / totalement réglées / soldées
    if any(w in q for w in [
        "totalement pay", "entierement pay", "completement pay",
        "totalement regle", "entierement regle",
        "factures payees", "factures reglees", "factures soldees",
    ]) and not any(w in q for w in ["non", "pas", "impay", "partiel"]):
        return "get_factures_payees", {}

    if "negatif" in q or "negativ" in q or "avoir" in q:
        return "get_factures_negatives", {}

    client_name = _extract_client_name(q)
    if client_name and "facture" in q:
        return "get_factures_par_client", {"client": client_name}

    # Boucle MONTHS — uniquement pour le CA/ventes
    for month_name, month_num in MONTHS.items():
        if month_name in q and any(
            w in q for w in [
                "ca",
                "chiffre",
                "vente",
                "revenu"]):
            match_year = re.search(r'\b(20\d{2})\b', q)
            if match_year:
                return "get_total_ventes_mois", {
                    "year": match_year.group(1), "month": month_num}
            return None, None

    match = re.search(r'(\d{4})-(\d{2})', q)
    if match and any(w in q for w in ["total", "ventes", "chiffre", "ca"]):
        return "get_total_ventes_mois", {
            "year": match.group(1), "month": match.group(2)}

    match = re.search(r'plus de (\d+) commandes', q)
    if match:
        return "get_clients_multiple_commandes", {
            "min_commandes": int(match.group(1))}

    if ("plus de deux commandes" in q or "commandes multiples" in q
            or "plusieurs commandes" in q or "plus de commandes" in q
            or "clients fideles" in q):
        return "get_clients_multiple_commandes", {"min_commandes": 2}

    if "stock" in q or "rupture" in q:
        match = re.search(r'\d+', q)
        seuil = int(match.group()) if match else 5
        return "get_produits_stock_faible", {"stock_min": seuil}

    match = re.search(r'(\d{4}-\d{2}-\d{2}).*(\d{4}-\d{2}-\d{2})', q)
    if match and any(
        w in q for w in [
            "paiement",
            "regl",
            "encaissement",
            "verse"]):
        return "get_total_paiements", {
            "start_date": match.group(1), "end_date": match.group(2)}

    if "3 derniers mois" in q and any(w in q for w in ["paiement", "regl"]):
        from datetime import datetime, timedelta
        end = datetime.today()
        start = end - timedelta(days=90)
        return "get_total_paiements", {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d")
        }

    return None, None


def _convert_mapping_result(result: dict):
    intent = result.get("intent", "")
    params = result.get("params", {})

    if intent in ("rejected", "clarification_required", ""):
        return None, None

    harmonized = {}
    if "date_debut" in params:
        harmonized["start_date"] = params["date_debut"]
    if "date_fin" in params:
        harmonized["end_date"] = params["date_fin"]
    if "seuil" in params:
        harmonized["stock_min"] = params["seuil"]
    if "min_commandes" in params:
        harmonized["min_commandes"] = params["min_commandes"]
    if "mois" in params:
        harmonized["month"] = params["mois"]
    if "annee" in params:
        harmonized["year"] = params["annee"]

    for k, v in params.items():
        if k not in ("date_debut", "date_fin", "seuil", "mois", "annee"):
            harmonized.setdefault(k, v)

    return intent, harmonized


def _execute_template(question: str, template_name: str,
                      params: dict, start_time: float) -> dict:
    """
    Bloc réutilisable : vérifie le cache, sinon exécute le SQL.
    Filtre automatiquement les paramètres non présents dans le SQL
    pour éviter les erreurs du driver MariaDB.
    """
    # ── Cache hit ──
    cached = chatbot_cache.get(template_name, params)
    if cached is not None:
        duration = round((time.time() - start_time) * 1000, 2)
        suggestions = generate_suggestions(template_name, params)
        log_id = log_query(
            question,
            cached.get("sql_query", ""),
            duration,
            len(cached["table"]),
            template_name,
            params,
            "success",
            None,
            from_cache=True
        )
        return {
            "table": cached["table"],
            "summary": f"{len(cached['table'])} résultat(s) trouvé(s). (cache)",
            "metadata": {
                "status": "success",
                "template": template_name,
                "duration_ms": duration,
                "row_count": len(cached["table"]),
                "params": params,
                "logs_id": log_id,
                "sql_query": cached.get("sql_query", ""),
                "from_cache": True,
                "suggestions": suggestions
            }
        }

    # ── Template introuvable ──
    template_function = TEMPLATE_MAPPING.get(template_name)
    if template_function is None:
        return {
            "table": [],
            "summary": f"Template '{template_name}' non trouvé.",
            "metadata": {
                "status": "error",
                "template": template_name,
                "suggestions": []
            }
        }

    # ── Exécution SQL ──
    sql_query = template_function()

    try:
        validate_sql_query(sql_query)

        # Ne passer au driver que les paramètres présents dans le SQL.
        # Cela évite l'erreur "paramètre inconnu" quand on passe {"limit": 5}
        # à un SQL qui ne contient pas :limit (ex: get_top_clients_ca).
        sql_placeholders = set(re.findall(r':(\w+)', sql_query))
        missing = sql_placeholders - set(params.keys())
        if missing:
            raise ValueError(f"Missing SQL params: {missing}")
        sql_params = {k: v for k, v in params.items() if k in sql_placeholders}

        columns, rows, execution_time = execute_query(sql_query, sql_params)
        duration = round((time.time() - start_time) * 1000, 2)
        result_rows = [dict(zip(columns, row)) for row in rows]

        if template_name == "get_top_produits_commandes" and "limit" in params:
            try:
                result_rows = result_rows[:int(params["limit"])]
            except (ValueError, TypeError):
                pass

        # ── Troncature top N côté Python ──
        # Le SQL retourne jusqu'à 200 lignes (garde-fou DB),
        # on tronque ici au nombre demandé par l'utilisateur.
        if template_name == "get_top_clients_ca" and "limit" in params:
            try:
                result_rows = result_rows[:int(params["limit"])]
            except (ValueError, TypeError):
                pass

        suggestions = generate_suggestions(template_name, params)

        log_id = log_query(
            question, sql_query, duration, len(result_rows),
            template_name, params, "success", None,
            from_cache=False
        )

        chatbot_cache.set(template_name, params, {
            "table": result_rows,
            "logs_id": log_id,
            "sql_query": sql_query
        })

        return {
            "table": result_rows,
            "summary": f"{len(result_rows)} résultat(s) trouvé(s).",
            "metadata": {
                "status": "success",
                "template": template_name,
                "duration_ms": duration,
                "row_count": len(result_rows),
                "params": params,
                "logs_id": log_id,
                "sql_query": sql_query,
                "from_cache": False,
                "suggestions": suggestions
            }
        }

    except Exception as e:
        duration = round((time.time() - start_time) * 1000, 2)
        log_id = log_query(
            question, sql_query, duration, 0,
            template_name, params, "error", str(e),
            from_cache=False
        )
        return {
            "table": [],
            "summary": "Erreur lors de l'exécution.",
            "metadata": {
                "status": "error",
                "template": template_name,
                "duration_ms": duration,
                "row_count": 0,
                "params": params,
                "error": str(e),
                "logs_id": log_id,
                "suggestions": []
            }
        }


def reload_templates():
    global TEMPLATES
    from ui.hybrid_engine import load_templates
    TEMPLATES = load_templates()


HYBRID_TEMPLATES_FILE = os.path.join(
    os.path.dirname(__file__), "..", "ui", "templates.json"
)


def load_hybrid_templates() -> dict:
    """Recharge à chaque requête — pas de cache mémoire."""
    try:
        with open(HYBRID_TEMPLATES_FILE, "r", encoding="utf-8") as f:
            data = _json_templates.load(f)
        return data.get("templates", {})
    except Exception:
        return {}


def match_admin_template(question: str) -> tuple:
    q = normalize(question)
    q_words = set(q.split())

    # ── Blacklist étendue : ces questions ne doivent JAMAIS aller vers admin templates ──
    BLACKLIST_PATTERNS = [
        r"non pay", r"impay", r"non regle", r"non sold",
        r"entre.*et", r"factures entre",
        r"plus de.*commande",
        r"chiffre.*affaires.*janvier", r"chiffre.*affaires.*fevrier",
        r"chiffre.*affaires.*mars", r"ca de", r"ca du mois",
        # ── NOUVEAUX : bloquer les questions simples déjà couvertes par V1/V2 ──
        r"stock.*inferieur",     # → get_produits_stock_faible
        r"inferieur.*stock",
        r"stock.*inf",
        r"moins de.*stock",
        r"stock.*moins de",
        r"rupture.*stock",
        r"factures.*client\s+\w",  # → get_factures_par_client
        r"facture.*de.*client",
        r"facture.*pour.*client",
    ]
    for pat in BLACKLIST_PATTERNS:
        if re.search(pat, q):
            return None, None, {}

    templates = load_hybrid_templates()
    best_match = None
    best_score = 0

    for tid, t in templates.items():
        if not t.get("active", True):
            continue
        keywords = t.get("keywords", [])
        if not keywords:
            continue
        total_score = 0
        for kw in keywords:
            kw_norm = normalize(kw)
            if kw_norm in q:
                # Mots trop génériques ne comptent pas seuls
                if kw_norm in {"facture", "factures", "client", "clients",
                               "commande", "commandes", "produit", "produits",
                               "total", "stock"}:
                    total_score += 1  # poids réduit
                else:
                    total_score += 3
                continue
            kw_words = set(kw_norm.split())
            common = kw_words & q_words
            if len(common) >= max(1, len(kw_words) // 2):
                total_score += 2
            elif len(common) >= 1:
                total_score += 1
        if total_score > best_score:
            best_score = total_score
            best_match = (tid, t)

    # ── Seuil relevé de 2 à 4 ──
    if best_match and best_score >= 4:
        tid, t = best_match
        sql = t.get("sql", "")
        placeholders = set(re.findall(r':(\w+)', sql))
        params = _extract_admin_params(question, placeholders)
        return tid, sql, params

    return None, None, {}


def _extract_admin_params(question: str, placeholders: set) -> dict:
    params = {}
    q = normalize(question)

    for p in placeholders:
        p_lower = p.lower()
        if "limit" in p_lower:
            m = re.search(r'\b(\d+)\b', q)
            params[p] = m.group(1) if m else "10"

        elif "annee" in p_lower or "year" in p_lower:
            # Cherche une année 4 chiffres
            m = re.search(r'\b(20\d{2})\b', question)
            params[p] = m.group(1) if m else "2026"

        elif "fournisseur" in p_lower:
            # Pattern : "fournisseur NOM" jusqu'à virgule ou fin
            m = re.search(
                r'fournisseur\s+([A-Z][A-Z0-9\s\-\.]{1,50}?)(?:\s*,|\s+rayon|\s+famille|\s+marque|\s+saison|\s+matiere|$)',
                question,
                re.IGNORECASE)
            params[p] = m.group(1).strip() if m else None

        elif "rayon" in p_lower:
            m = re.search(
                r'rayon\s+([A-Z][A-Z0-9\s\-]{1,30}?)(?:\s*,|\s+famille|\s+marque|\s+saison|\s+matiere|$)',
                question,
                re.IGNORECASE)
            params[p] = m.group(1).strip() if m else None

        elif "famille" in p_lower and "sous" not in p_lower:
            m = re.search(
                r'famille\s+([^,]+?)(?:\s*,|\s+sous|$)',
                question, re.IGNORECASE
            )
            params[p] = m.group(1).strip() if m else None

        elif "sous_famille" in p_lower or "sous-famille" in p_lower:
            m = re.search(
                r'sous[- ]famille\s+([^,]+?)(?:\s*,|$)',
                question, re.IGNORECASE
            )
            params[p] = m.group(1).strip() if m else None

        elif "marque" in p_lower:
            m = re.search(
                r'marque\s+([^,]+?)(?:\s*,|$)',
                question, re.IGNORECASE
            )
            params[p] = m.group(1).strip() if m else None

        elif "matiere" in p_lower:
            m = re.search(
                r'mati[èe]re\s+([^,]+?)(?:\s*,|$)',
                question, re.IGNORECASE
            )
            params[p] = m.group(1).strip() if m else None

        elif "saison" in p_lower:
            m = re.search(
                r'saison\s+([^,]+?)(?:\s*,|$)',
                question, re.IGNORECASE
            )
            params[p] = m.group(1).strip() if m else None

        elif "mois" in p_lower or "month" in p_lower:
            from datetime import datetime as _dt
            params[p] = str(_dt.today().month).zfill(2)

        elif "seuil" in p_lower or "stock_min" in p_lower:
            m = re.search(r'\b(\d+)\b', q)
            params[p] = m.group(1) if m else "10"

        elif p_lower == "client":
            client = _extract_client_name(question)
            params[p] = f"%{client}%" if client else "%"

        else:
            m = re.search(r'\b(\d+)\b', q)
            if m:
                params[p] = m.group(1)

    return params


def get_response(question: str) -> dict:
    # Règle d'exception pour les questions qui doivent obligatoirement passer
    # par le LLM
    force_llm_questions = [
        "quelles factures ont été émises et payées dans le même mois",
        "quels sont les 5 produits avec le plus grand nombre de lignes de commande distinctes"]
    q_lower = question.lower().strip()
    start_time = time.time()

    # ===== FORCAGE BRUTAL POUR LE RÉCAPITULATIF =====
    if "récapitulatif des ventes" in q_lower or "ventes et règlements" in q_lower:
        print(">>> DÉTECTION DU RÉCAPITULATIF - EXÉCUTION FORCÉE DU TEMPLATE")
        import json
        import os
        from app.db import execute_query

        templates_file = os.path.join(
            os.path.dirname(__file__), "..", "ui", "templates.json")
        with open(templates_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        tpl = data["templates"]["recap_ventes_reglements"]
        sql_template = tpl["sql"]

        params = {}
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', question)
        if len(dates) >= 2:
            params["date_debut"] = dates[0]
            params["date_fin"] = dates[1]
        else:
            params["date_debut"] = "2026-01-01"
            params["date_fin"] = "2026-12-31"

        mag_match = re.search(
            r'magasin\s+([A-Za-z0-9_]+)',
            question,
            re.IGNORECASE)
        params["magasin"] = mag_match.group(1) if mag_match else None
        params["limit"] = "200"

        sql = sql_template
        for key, value in params.items():
            if value is None:
                sql = sql.replace(f":{key}", "NULL")
            else:
                safe_value = str(value).replace("'", "''")
                sql = sql.replace(f":{key}", f"'{safe_value}'")

        try:
            columns, rows, _ = execute_query(sql, {})
            duration = round((time.time() - start_time) * 1000, 2)
            result_rows = [dict(zip(columns, row)) for row in rows]
            return {
                "table": result_rows,
                "summary": f"{len(result_rows)} résultat(s) trouvé(s).",
                "metadata": {
                    "status": "success",
                    "template": "recap_ventes_reglements",
                    "duration_ms": duration,
                    "row_count": len(result_rows),
                    "params": params,
                    "logs_id": "forced_manual",
                    "sql_query": sql,
                    "from_cache": False,
                    "suggestions": []
                }
            }
        except Exception as e:
            print(f"ERREUR SQL lors de l'exécution forcée : {e}")
            # En cas d'erreur on laisse le code continuer (fallback normal)

    # ===== FORCER LE TEMPLATE ACHATS PAR FOURNISSEUR (réceptions) =====
    q_lower_local = question.lower()
    if ("achats par fournisseur" in q_lower_local or
            ("fournisseur" in q_lower_local and "entrepot" in q_lower_local)):
        print(">>> DÉTECTION ACHATS PAR FOURNISSEUR - EXÉCUTION FORCÉE")
        import json
        import os
        from app.db import execute_query

        templates_file = os.path.join(
            os.path.dirname(__file__), "..", "ui", "templates.json")
        with open(templates_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        tpl = data["templates"]["achats_par_fournisseur"]
        # doit contenir la requête avec :entrepot, :fournisseur, :date_debut,
        # :date_fin, :limit
        sql_template = tpl["sql"]

        params = {}

        # Entrepôt (magasin)
        entrepot_match = re.search(
            r'entrepot\s+([A-Za-z0-9_]+)',
            question,
            re.IGNORECASE)
        params["entrepot"] = entrepot_match.group(
            1) if entrepot_match else None

        # Fournisseur : extraction robuste (dernière occurrence après
        # "fournisseur")
        fournisseur = None
        # Chercher "fournisseur XXXX" jusqu'à la prochaine virgule ou "entre"
        # ou fin
        match_f = re.search(
            r'fournisseur\s+([A-Za-z0-9_ ]+?)(?:\s+entre|\s+pour|\s+et|,|$)',
            question,
            re.IGNORECASE)
        if match_f:
            candidate = match_f.group(1).strip()
            if candidate and not any(
                bad in candidate.lower() for bad in [
                    'pour',
                    'l\'année',
                    'entrepot',
                    'magasin',
                    'date']):
                fournisseur = candidate
        # Fallback : découpage par "fournisseur"
        if not fournisseur:
            parts = question.lower().split("fournisseur")
            if len(parts) >= 2:
                after = parts[-1].strip()
                if ',' in after:
                    candidate = after[:after.index(',')].strip()
                else:
                    candidate = after.strip()
                if candidate and not any(
                    bad in candidate for bad in [
                        'pour',
                        'l\'année',
                        'entrepot',
                        'magasin']):
                    fournisseur = candidate
        params["fournisseur"] = fournisseur
        print(f"[DEBUG] fournisseur extrait = {fournisseur}")

        # Dates
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', question)
        if len(dates) >= 2:
            params["date_debut"] = dates[0]
            params["date_fin"] = dates[1]
        else:
            params["date_debut"] = "2026-01-01"
            params["date_fin"] = "2026-12-31"

        params["limit"] = "200"

        # Injection des paramètres
        sql = sql_template
        for key, value in params.items():
            if value is None:
                sql = sql.replace(f":{key}", "NULL")
            else:
                safe_value = str(value).replace("'", "''")
                sql = sql.replace(f":{key}", f"'{safe_value}'")

        try:
            columns, rows, _ = execute_query(sql, {})
            duration = round((time.time() - start_time) * 1000, 2)
            result_rows = [dict(zip(columns, row)) for row in rows]
            return {
                "table": result_rows,
                "summary": f"{len(result_rows)} résultat(s) trouvé(s).",
                "metadata": {
                    "status": "success",
                    "template": "achats_par_fournisseur",
                    "duration_ms": duration,
                    "row_count": len(result_rows),
                    "params": params,
                    "logs_id": "forced_achats",
                    "sql_query": sql,
                    "from_cache": False,
                    "suggestions": []
                }
            }
        except Exception as e:
            print(f"ERREUR achats par fournisseur : {e}")

        # ===== FORCER LE TEMPLATE LISTES APPROVISIONNEMENTS =====
    q_lower_local = question.lower()
    if ("listes des approvisionnements" in q_lower_local or (
            "approvisionnements" in q_lower_local and "magasin" in q_lower_local)):
        print(">>> DÉTECTION LISTES APPROVISIONNEMENTS - EXÉCUTION FORCÉE")
        import json
        import os
        from app.db import execute_query

        templates_file = os.path.join(
            os.path.dirname(__file__), "..", "ui", "templates.json")
        with open(templates_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        tpl = data["templates"]["listes_approvisionnements"]
        sql_template = tpl["sql"]

        params = {}

        # Magasin (entrepôt)
        magasin_match = re.search(
            r'magasin\s+([A-Za-z0-9_]+)',
            question,
            re.IGNORECASE)
        params["magasin"] = magasin_match.group(1) if magasin_match else None

        # Fournisseur (dernière occurrence après "fournisseur")
        fournisseur = None
        parts = question.lower().split("fournisseur")
        if len(parts) >= 2:
            after = parts[-1].strip()
            if ',' in after:
                candidate = after[:after.index(',')].strip()
            else:
                candidate = after.strip()
            if candidate and not any(
                bad in candidate for bad in [
                    'pour',
                    'l\'année',
                    'entrepot',
                    'magasin',
                    'entre']):
                fournisseur = candidate
        params["fournisseur"] = fournisseur

        # Nature (optionnel – laisser NULL)
        params["nature"] = None

        # Référence
        ref_match = re.search(
            r'reference\s+([A-Za-z0-9_\-]+)',
            question,
            re.IGNORECASE)
        params["reference"] = ref_match.group(1) if ref_match else None

        # Dates
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', question)
        if len(dates) >= 2:
            params["date_debut"] = dates[0]
            params["date_fin"] = dates[1]
        else:
            params["date_debut"] = "2026-01-01"
            params["date_fin"] = "2026-12-31"

        params["limit"] = "200"

        sql = sql_template
        for key, value in params.items():
            if value is None:
                sql = sql.replace(f":{key}", "NULL")
            else:
                safe_value = str(value).replace("'", "''")
                sql = sql.replace(f":{key}", f"'{safe_value}'")

        try:
            columns, rows, _ = execute_query(sql, {})
            duration = round((time.time() - start_time) * 1000, 2)
            result_rows = [dict(zip(columns, row)) for row in rows]
            return {
                "table": result_rows,
                "summary": f"{len(result_rows)} résultat(s) trouvé(s).",
                "metadata": {
                    "status": "success",
                    "template": "listes_approvisionnements",
                    "duration_ms": duration,
                    "row_count": len(result_rows),
                    "params": params,
                    "logs_id": "forced_appro",
                    "sql_query": sql,
                    "from_cache": False,
                    "suggestions": []
                }
            }
        except Exception as e:
            print(f"ERREUR listes approvisionnements : {e}")

    # ===== FORCER LE TEMPLATE ANALYSE MOUVEMENTS STOCK =====
    q_lower_local = question.lower()
    if ("analyse des mouvements de stock" in q_lower_local or "mouvements de stock" in q_lower_local):
        print(">>> DÉTECTION ANALYSE MOUVEMENTS STOCK - EXÉCUTION FORCÉE")
        import json
        import os
        import re
        from app.db import execute_query

        templates_file = os.path.join(
            os.path.dirname(__file__), "..", "ui", "templates.json")
        with open(templates_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        tpl = data["templates"]["analyse_mouvements_stock"]
        sql_template = tpl["sql"]

        # (Facultatif) Vérification du template
        print("DEBUG SQL TEMPLATE (début) :", repr(sql_template[:200]))

        params = {}

        # === Dates ===
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', question)
        if len(dates) >= 2:
            params["date_debut"] = dates[0]
            params["date_fin"] = dates[1]
        else:
            params["date_debut"] = "2026-01-01"
            params["date_fin"] = "2026-12-31"

        # === Entrepôt ===
        entrepot_match = re.search(
            r'entrepot\s+([A-Za-z0-9_]+)',
            question,
            re.IGNORECASE)
        if entrepot_match:
            params["entrepot"] = entrepot_match.group(1)

        # === Catégorie ===
        cat_match = re.search(
            r'categorie\s+([A-Za-z0-9_\-]+)',
            question,
            re.IGNORECASE)
        if cat_match:
            params["categorie"] = cat_match.group(1)

        # === Nature produit (RowMaterial / Finished) ===
        nature_match = re.search(
            r'nature\s+([A-Za-z0-9_\-]+)',
            question,
            re.IGNORECASE)
        if nature_match:
            candidate = nature_match.group(1).strip()
            candidate_norm = candidate[0].upper(
            ) + candidate[1:].lower() if candidate else ''
            if candidate_norm in ('Rowmaterial', 'Finished'):
                params["nature"] = candidate_norm
            # Si la valeur n'est pas reconnue, on ne filtre pas sur ce champ

        # === Limite ===
        params["limit"] = 200   # entier (sera interprété correctement)

        # Tous les autres paramètres (produit, type_mouvement, taille, couleur, rayon, saison, marque, matiere)
        # ne sont pas utilisés dans la requête SQL actuelle – on les ignore
        # pour éviter les erreurs.

        # Exécution avec paramètres nommés (pas de remplacement manuel !)
        try:
            columns, rows, _ = execute_query(sql_template, params)
            duration = round((time.time() - start_time) * 1000, 2)
            result_rows = [dict(zip(columns, row)) for row in rows]
            return {
                "table": result_rows,
                "summary": f"{len(result_rows)} mouvement(s) trouvé(s).",
                "metadata": {
                    "status": "success",
                    "template": "analyse_mouvements_stock",
                    "duration_ms": duration,
                    "row_count": len(result_rows),
                    "params": params,
                    "logs_id": "forced_stock_mvt",
                    "sql_query": sql_template,
                    "from_cache": False,
                    "suggestions": []
                }
            }
        except Exception as e:
            print(f"ERREUR analyse mouvements stock : {e}")
            # Vous pouvez aussi retourner une réponse d'erreur explicite
            return {
                "table": [],
                "summary": f"Erreur SQL : {str(e)}",
                "metadata": {"status": "error"}
            }

    # ── Force LLM pour questions complexes spécifiques ──
    if any(forced in q_lower for forced in force_llm_questions):
        from ui.hybrid_engine import ask_hybrid
        return ask_hybrid(question)

    if SentenceTransformer is None:
        raise RuntimeError("Model not available")

    global hybrid_engine
    if hybrid_engine is None:
        from ui.hybrid_engine import HybridEngine
        hybrid_engine = HybridEngine()

    suggestions = []

    # ── 1. Sécurité ──
    try:
        detect_injection(question)
    except Exception:
        return {
            "table": [],
            "summary": "Requête rejetée pour des raisons de sécurité.",
            "metadata": {"status": "rejected", "suggestions": []}
        }

    q_lower = normalize(question)

    # ── Questions complexes → réponse d'erreur directe (pas de LLM) ──
    if any(kw in q_lower for kw in COMPLEX_KEYWORDS):
        return {
            "table": [],
            "summary": "Je ne peux pas répondre à cette question.",
            "metadata": {"status": "error", "suggestions": []}
        }

    # ── 2. Ambiguïtés simples ──
    if q_lower.strip() in ["facture", "factures"]:
        return {
            "table": [],
            "summary": "Veuillez préciser votre demande (ex: factures non payées, factures par client...).",
            "metadata": {
                "status": "clarification_required",
                "suggestions": []}}

    if q_lower.strip() in ["vente", "ventes"]:
        return {
            "table": [],
            "summary": "Veuillez préciser votre demande (ex: chiffre d'affaires par mois...).",
            "metadata": {
                "status": "clarification_required",
                "suggestions": []}}

    # ── 2b. Ambiguïtés avancées ──
    if re.search(r'factures?\s+(du\s+)?client\s*$', q_lower):
        return {
            "table": [],
            "summary": "Veuillez préciser le nom du client.",
            "metadata": {"status": "clarification_required", "suggestions": []}
        }

    if "client" in q_lower and re.search(
            r'\d{4}-\d{2}-\d{2}.*\d{4}-\d{2}-\d{2}', q_lower):
        return {
            "table": [],
            "summary": "Souhaitez-vous filtrer par client ou par période ?",
            "metadata": {"status": "clarification_required", "suggestions": []}
        }

    if q_lower.strip() == "produits":
        return {
            "table": [],
            "summary": "Veuillez préciser votre demande sur les produits.",
            "metadata": {"status": "clarification_required", "suggestions": []}
        }

    ambiguous_patterns = [
        "ventes du mois", "donne moi les ventes", "factures du mois dernier",
        "factures janvier", "factures fevrier", "factures mars",
        "donne moi les factures", "ventes 2026",
    ]
    for p in ambiguous_patterns:
        if p in q_lower:
            if p == "donne moi les factures" and re.search(
                    r'\d{4}-\d{2}-\d{2}', q_lower):
                continue
            if p == "donne moi les factures" and "client" in q_lower:
                continue
            if p == "donne moi les factures" and any(w in q_lower for w in [
                "payee", "payees", "regle", "reglees", "soldee", "soldees",
                "paye", "totalement", "entierement", "completement"
            ]):
                continue                                        # ← ajouté
            if p == "ventes 2026" and re.search(r'\d{4}-\d{2}', q_lower):
                continue
            return {
                "table": [],
                "summary": "Veuillez préciser votre demande.",
                "metadata": {
                    "status": "clarification_required",
                    "suggestions": []}}

    # ── 2c. EARLY MATCH — templates V1/V2 prioritaires (avant admin templates) ──
    early_match, early_params = match_question(question)
    if early_match in (
        "get_top_clients_ca",
        "get_commandes_par_mois",
        "liste_clients_simple",
        "get_top_produits_commandes",
        "get_ca_par_trimestre",
        "get_produits_stock_faible",
        "get_factures_par_client",
        "get_factures_non_payees",
        "get_factures_non_payees_30j",
        "get_factures_payees",
    ):
        return _execute_template(
            question,
            early_match,
            early_params,
            start_time)

    # ── 2d. Templates admin ──
    admin_tid, admin_sql, admin_params = match_admin_template(question)
    if admin_tid and admin_sql:
        logger.info(f"[ADMIN TEMPLATE MATCH] {admin_tid}")
        sql_placeholders = set(re.findall(r':(\w+)', admin_sql))
        sql_params = {
            k: v for k,
            v in admin_params.items() if k in sql_placeholders}

        # Injection manuelle sécurisée
        sql_injected = admin_sql
        for key, value in sql_params.items():
            if value is None:
                sql_injected = sql_injected.replace(
                    f"= :{key}", "IS NOT NULL OR 1=1"
                ).replace(f":{key}", "NULL")
            else:
                safe_value = str(value).replace("'", "''")
                sql_injected = sql_injected.replace(
                    f":{key}", f"'{safe_value}'")

        try:
            columns, rows, _ = execute_query(sql_injected, {})
            duration = round((time.time() - start_time) * 1000, 2)
            result_rows = [dict(zip(columns, row)) for row in rows]

            if "limit" in admin_params and admin_params["limit"]:
                try:
                    result_rows = result_rows[:int(admin_params["limit"])]
                except (ValueError, TypeError):
                    pass

            log_id = log_query(
                question, sql_injected, duration, len(result_rows),
                admin_tid, sql_params, "success", None, from_cache=False
            )
            return {
                "table": result_rows,
                "summary": f"{
                    len(result_rows)} résultat(s) trouvé(s).",
                "metadata": {
                    "status": "success",
                    "template": admin_tid,
                    "duration_ms": duration,
                    "row_count": len(result_rows),
                    "params": sql_params,
                    "logs_id": log_id,
                    "sql_query": sql_injected,
                    "from_cache": False,
                    "suggestions": generate_suggestions(
                        admin_tid,
                        admin_params),
                }}
        except Exception as e:
            logger.warning(f"Erreur template admin {admin_tid} : {e}")
            # Fallback vers le routing normal si le template admin échoue

    # ── 3. Mapping rules ──
    mapping_result = apply_mapping_rules(question)
    print("🔍 MAPPING RESULT:", mapping_result)

    if mapping_result is not None:
        intent = mapping_result.get("intent", "")

        if intent == "rejected":
            return {
                "table": [],
                "summary": "Requête rejetée pour des raisons de sécurité.",
                "metadata": {"status": "rejected", "suggestions": suggestions}
            }

        if intent == "clarification_required":
            return {
                "table": [],
                "summary": mapping_result.get(
                    "clarification_message",
                    "Veuillez préciser votre demande."),
                "metadata": {
                    "status": "clarification_required",
                    "suggestions": suggestions}}

        template_name, params = _convert_mapping_result(mapping_result)
        if template_name is not None:
            return _execute_template(
                question, template_name, params, start_time)

    # ── 4. Match question (fallback règles regex) ──
    template_name, params = match_question(question)

    # ── 5. Aucune solution trouvée ──
    if template_name is None:
        return {
            "table": [],
            "summary": "Je ne peux pas répondre à cette question.",
            "metadata": {"status": "error", "suggestions": []}
        }

    # ── 6. Exécution SQL ──
    return _execute_template(question, template_name, params, start_time)
