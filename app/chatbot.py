# app/chatbot.py
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
from ui.hybrid_engine import load_templates
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
    "depuis plus de", "depuis plus",
    "comparer", "comparaison",
]

hybrid_engine = None

def normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return text.encode("ascii", "ignore").decode("utf-8")


def match_question(question: str):
    q = normalize(question)

    # ── NOUVEAU : top produits commandés → template dédié ──
    if (any(w in q for w in ["produit", "article"]) and 
       any(w in q for w in ["commande", "vendu", "vendu"]) and 
       any(w in q for w in ["top", "plus", "meilleur", "populaire"])):
        match_n = re.search(r'\b(\d+)\b', q)
        limit = int(match_n.group(1)) if match_n else 10
        return "get_top_produits_commandes", {"limit": limit}

    # ── CA par trimestre ──────────────────────────────────────
    if "trimestre" in q and any(w in q for w in ["ca", "chiffre", "vente", "depense", "total"]):
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
    if any((w in q for w in ["top", "meilleur", "eleve", "plus grand", "plus important",
                             "plus haut", "chiffre affaires le plus", "plus eleve",
                             "les plus eleve", "le plus eleve"]) 
            and any(w in q for w in ["client", "societe"])):
        match_n = re.search(r'\b(\d+)\b', q)
        limit = int(match_n.group(1)) if match_n else 5
        return "get_top_clients_ca", {"limit": limit}

    # ── Commandes par mois — PRIORITÉ HAUTE ───────────────────────
    if (
    "commande" in q
    and any(w in q for w in ["combien", "nombre", "total"])
    and not any(w in q for w in ["facture", "vente", "ca", "chiffre"])
):
        for month_key, month_num in MONTHS.items():
            if month_key in q:
                match_year = re.search(r'\b(20\d{2})\b', q)
                year = match_year.group(1) if match_year else "2026"
                return "get_commandes_par_mois", {"annee": year, "mois": month_num}
        match_ym = re.search(r'(\d{4})-(\d{2})', q)
        if match_ym:
            return "get_commandes_par_mois", {
                "annee": match_ym.group(1),
                "mois":  match_ym.group(2)
            }
        if any(w in q for w in ["combien", "nombre", "total", "liste", "affiche"]):
            from datetime import datetime
            now = datetime.today()
            return "get_commandes_par_mois", {
                "annee": str(now.year),
                "mois":  str(now.month).zfill(2)
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
        return "get_total_ventes_mois", {"year": match_ym.group(1), "month": match_ym.group(2)}

    match = re.search(r'(\d{4}-\d{2}-\d{2}).*(\d{4}-\d{2}-\d{2})', q)
    if match:
        return "get_factures_between", {"start_date": match.group(1), "end_date": match.group(2)}

    if "partiellement pay" in q or "partiel" in q:
        return "get_factures_partiellement_payees", {}

    # ── Factures non payées depuis N jours — PRIORITÉ SUR le template générique ──
    match_jours = re.search(r'(\d+)\s*jours?', q)
    if match_jours and any(w in q for w in ["non pay", "impaye", "non regle", "retard"]):
        return "get_factures_non_payees_30j", {}
    
    if "30 jours" in q or "trente jours" in q or "depuis plus" in q:
        if any(w in q for w in ["non pay", "impaye", "non regle", "retard", "facture"]):
            return "get_factures_non_payees_30j", {}
    
    if ("non pay" in q or "impaye" in q or "non regle" in q
            or "pas regle" in q or "pas ete regle" in q
            or "n ont pas" in q or "montant restant" in q):
        return "get_factures_non_payees", {}

    if "paiement partiel" in q or "cours de paiement" in q:
        return "get_factures_partiellement_payees", {}

    if "negatif" in q or "negativ" in q or "avoir" in q:
        return "get_factures_negatives", {}

    match = re.search(r'factures?\s+client\s+([a-zA-Z0-9_\- ]+)', q)
    if match:
        return "get_factures_par_client", {"client": match.group(1).strip()}

    match = re.search(r'client\s+([a-zA-Z0-9_\- ]+)', q)
    if "facture" in q and match:
        client_name = match.group(1).strip().replace("pour", "").strip()
        return "get_factures_par_client", {"client": client_name}

    # Boucle MONTHS — uniquement pour le CA/ventes
    for month_name, month_num in MONTHS.items():
        if month_name in q and any(w in q for w in ["ca", "chiffre", "vente", "revenu"]):
            match_year = re.search(r'\b(20\d{2})\b', q)
            if match_year:
                return "get_total_ventes_mois", {"year": match_year.group(1), "month": month_num}
            return None, None

    match = re.search(r'(\d{4})-(\d{2})', q)
    if match and any(w in q for w in ["total", "ventes", "chiffre", "ca"]):
        return "get_total_ventes_mois", {"year": match.group(1), "month": match.group(2)}

    match = re.search(r'plus de (\d+) commandes', q)
    if match:
        return "get_clients_multiple_commandes", {"min_commandes": int(match.group(1))}

    if ("plus de deux commandes" in q or "commandes multiples" in q
            or "plusieurs commandes" in q or "plus de commandes" in q
            or "clients fideles" in q):
        return "get_clients_multiple_commandes", {"min_commandes": 2}

    if "stock" in q or "rupture" in q:
        match = re.search(r'\d+', q)
        seuil = int(match.group()) if match else 5
        return "get_produits_stock_faible", {"stock_min": seuil}

    match = re.search(r'(\d{4}-\d{2}-\d{2}).*(\d{4}-\d{2}-\d{2})', q)
    if match and any(w in q for w in ["paiement", "regl", "encaissement", "verse"]):
        return "get_total_paiements", {"start_date": match.group(1), "end_date": match.group(2)}

    if "3 derniers mois" in q and any(w in q for w in ["paiement", "regl"]):
        from datetime import datetime, timedelta
        end   = datetime.today()
        start = end - timedelta(days=90)
        return "get_total_paiements", {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date":   end.strftime("%Y-%m-%d")
        }

    return None, None


def _convert_mapping_result(result: dict):
    intent = result.get("intent", "")
    params = result.get("params", {})

    if intent in ("rejected", "clarification_required", ""):
        return None, None

    harmonized = {}
    if "date_debut"    in params: harmonized["start_date"]    = params["date_debut"]
    if "date_fin"      in params: harmonized["end_date"]      = params["date_fin"]
    if "seuil"         in params: harmonized["stock_min"]     = params["seuil"]
    if "min_commandes" in params: harmonized["min_commandes"] = params["min_commandes"]
    if "mois"          in params: harmonized["month"]         = params["mois"]
    if "annee"         in params: harmonized["year"]          = params["annee"]

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
        duration    = round((time.time() - start_time) * 1000, 2)
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
                "status":      "success",
                "template":    template_name,
                "duration_ms": duration,
                "row_count":   len(cached["table"]),
                "params":      params,
                "logs_id":     log_id,
                "sql_query":   cached.get("sql_query", ""),
                "from_cache":  True,
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
                "status":      "error",
                "template":    template_name,
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
        duration    = round((time.time() - start_time) * 1000, 2)
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
            "table":     result_rows,
            "logs_id":   log_id,
            "sql_query": sql_query
        })

        return {
            "table": result_rows,
            "summary": f"{len(result_rows)} résultat(s) trouvé(s).",
            "metadata": {
                "status":      "success",
                "template":    template_name,
                "duration_ms": duration,
                "row_count":   len(result_rows),
                "params":      params,
                "logs_id":     log_id,
                "sql_query":   sql_query,
                "from_cache":  False,
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
                "status":      "error",
                "template":    template_name,
                "duration_ms": duration,
                "row_count":   0,
                "params":      params,
                "error":       str(e),
                "logs_id":     log_id,
                "suggestions": []
            }
        }


def reload_templates():
    """Recharge les templates depuis le fichier JSON."""
    global TEMPLATES
    TEMPLATES = load_templates()


def get_response(question: str) -> dict:

    if SentenceTransformer is None:
        raise RuntimeError("Model not available")

    global hybrid_engine
    if hybrid_engine is None:
        from ui.hybrid_engine import HybridEngine
        hybrid_engine = HybridEngine()
    
    start_time = time.time()

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

    # ── NOUVEAU : questions complexes → LLM directement, skip tout le routing ──
    
    q_norm = normalize(question)
    if any(kw in q_lower for kw in COMPLEX_KEYWORDS):
        # Passe directement au LLM interne, skip ambiguités + mapping + routing
        try:
            result = run_llm_pipeline(question)

            if not result or "metadata" not in result:
                raise ValueError("LLM returned invalid result")
            
            intent = result["metadata"].get("template", "")
            p = result["metadata"].get("params", {})
            result["metadata"]["suggestions"] = generate_suggestions(intent, p)
            return {
                "table":    result["table"],
                "summary":  f"{result['metadata']['row_count']} résultat(s) trouvé(s).",
                "metadata": result["metadata"]
            }
        except Exception as e:
            print("LLM ERROR:", e)
            return {
                "table": [],
                "summary": "Je ne peux pas répondre à cette question.",
                "metadata": {"status": "error", "suggestions": []}
            }

    q_lower = normalize(question)

    # ── 2. Ambiguïtés simples ──
    if q_lower.strip() in ["facture", "factures"]:
        return {
            "table": [],
            "summary": "Veuillez préciser votre demande (ex: factures non payées, factures par client...).",
            "metadata": {"status": "clarification_required", "suggestions": []}
        }

    if q_lower.strip() in ["vente", "ventes"]:
        return {
            "table": [],
            "summary": "Veuillez préciser votre demande (ex: chiffre d'affaires par mois...).",
            "metadata": {"status": "clarification_required", "suggestions": []}
        }

    # ── 2b. Ambiguïtés avancées ──
    if re.search(r'factures?\s+(du\s+)?client\s*$', q_lower):
        return {
            "table": [],
            "summary": "Veuillez préciser le nom du client.",
            "metadata": {"status": "clarification_required", "suggestions": []}
        }

    if "client" in q_lower and re.search(r'\d{4}-\d{2}-\d{2}.*\d{4}-\d{2}-\d{2}', q_lower):
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
        "factures payees", "factures totalement payees",
    ]

    for p in ambiguous_patterns:
        if p in q_lower:
            if p == "donne moi les factures" and re.search(r'\d{4}-\d{2}-\d{2}', q_lower):
                continue
            if p == "donne moi les factures" and "client" in q_lower:
                continue
            if p == "ventes 2026" and re.search(r'\d{4}-\d{2}', q_lower):
                continue
            return {
                "table": [],
                "summary": "Veuillez préciser votre demande.",
                "metadata": {"status": "clarification_required", "suggestions": []}
            }

    # ── 3. EARLY MATCH (PRIORITÉ ABSOLUE) ──
    early_match, early_params = match_question(question)
    if early_match in ("get_top_clients_ca", "get_commandes_par_mois", "liste_clients_simple","get_top_produits_commandes","get_ca_par_trimestre",):
        return _execute_template(question, early_match, early_params, start_time)

    logger.debug(f"MAPPING RESULT: {apply_mapping_rules(question)}")
    
    # ── 4. Mapping rules ──
    mapping_result = apply_mapping_rules(question)
    if mapping_result is not None:
        intent = mapping_result.get("intent", "")

        if intent == "rejected":
            return {
                "table": [],
                "summary": "Requête rejetée pour des raisons de sécurité.",
                "metadata": {"status": "rejected", "suggestions": []}
            }

        if intent == "clarification_required":
            return {
                "table": [],
                "summary": mapping_result.get(
                    "clarification_message", "Veuillez préciser votre demande."),
                "metadata": {"status": "clarification_required", "suggestions": []}
            }

        template_name, params = _convert_mapping_result(mapping_result)
        if template_name is not None:
            return _execute_template(question, template_name, params, start_time)

    # ── 5. Match question (fallback règles) ──
    template_name, params = match_question(question)

    # ── 6. LLM fallback ──
    # Couche 4 : LLM fallback
    if template_name is None:
        try:
            result      = run_llm_pipeline(question)
            intent      = result["metadata"].get("template", "")
            p           = result["metadata"].get("params", {})
            suggestions = generate_suggestions(intent, p)
            result["metadata"]["suggestions"] = suggestions
            return {
            "table":    result["table"],
            "summary":  f"{result['metadata']['row_count']} résultat(s) trouvé(s).",
            "metadata": result["metadata"]
        }
        except Exception as e:
            print("LLM ERROR:", e)
            return {
            "table": [],
            "summary": "Je ne peux pas répondre à cette question.",
            "metadata": {"status": "error", "suggestions": []}
            # ↑ "error" au lieu de "rejected"
            # "error" → call_api passera au LLM hybride port 8001
        }

    # ── 7. Exécution SQL ──
    return _execute_template(question, template_name, params, start_time)