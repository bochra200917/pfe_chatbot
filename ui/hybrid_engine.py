"""
ui/hybrid_engine.py
Moteur hybride NL2SQL — Chatbot Dolibarr
Logique : Templates V1/V2 d'abord → Claude via OpenRouter en fallback si échec

Auteur : Bochra Ben Yedder
"""

import re
import json
import time
import logging
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field, asdict
import sqlglot
from sqlglot.errors import ParseError
import requests

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    SentenceTransformer = None
    util = None

logger = logging.getLogger(__name__)

def load_model():
    from sentence_transformers import SentenceTransformer, util
    return SentenceTransformer("all-MiniLM-L6-v2"), util

def call_ollama(prompt: str, model: str = "mistral") -> str:
    """
    Appel à Ollama en local via API REST
    """
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            return ""

    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"ERROR: {str(e)}"

# ─── Constantes ───────────────────────────────────────────────────────────────

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
]

# Tables autorisées (whitelist)
ALLOWED_TABLES = {
    "m38h_facture", "m38h_facturedet", "m38h_commande", "m38h_commandedet",
    "m38h_societe", "m38h_socpeople", "m38h_product", "m38h_product_stock",
    "m38h_stock_mouvement", "m38h_entrepot", "m38h_paiement",
    "m38h_paiement_facture", "m38h_accounting_account",
    "m38h_accounting_bookkeeping", "m38h_bank", "m38h_bank_account",
    "m38h_user", "m38h_salary", "m38h_projet", "m38h_projet_task",
}

# ─── Embeddings Model ─────────────────────────────────────────────
if SentenceTransformer is not None:
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
else:
    embedding_model = None

MAX_ROWS = 200
LLM_CONFIDENCE_THRESHOLD = 0.6  # fallback déclenché si templates échouent
TEMPLATE_EMBEDDINGS = {}
# ─── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class HybridResult:
    question: str
    mode: str                          # "template" | "llm_router" | "llm_sql" | "fallback_error"
    intent: Optional[str]
    sql: Optional[str]
    params: dict
    valid: bool
    error: Optional[str]
    llm_called: bool
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    warning: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

def build_template_embeddings(templates: dict):
    """
    Pré-calcule les embeddings des templates (description + keywords)
    """
    global TEMPLATE_EMBEDDINGS

    TEMPLATE_EMBEDDINGS = {}

    if embedding_model is None:
        return

    for tid, t in templates.items():
        if not t.get("active", True):
            continue

        text = t.get("description", "") + " " + " ".join(t.get("keywords", []))

        if text.strip():
            TEMPLATE_EMBEDDINGS[tid] = embedding_model.encode(
                text,
                normalize_embeddings=True
            )
# ─── Validation SQL ───────────────────────────────────────────────────────────

def validate_sql_security(sql: str) -> tuple[bool, str]:
    """
    Valide qu'un SQL est SELECT-only, sans mots interdits,
    avec LIMIT, et via parsing AST (sqlglot).
    """
    sql_upper = sql.upper().strip()

    if "UNION" in sql_upper:
        return False, "UNION interdit."

    if ";" in sql.strip()[:-1]:
        return False, "Plusieurs requêtes interdites."

    if "--" in sql or "/*" in sql:
        return False, "Commentaires SQL interdits."

    # 1. Doit commencer par SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "La requête doit commencer par SELECT."

    # 2. Mots-clés interdits
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + kw + r'\b', sql_upper):
            return False, f"Mot-clé interdit détecté : {kw}"

    # 3. LIMIT obligatoire
    if "LIMIT" not in sql_upper:
        return False, "LIMIT absent — requis pour limiter les résultats."

    # 4. Validation AST via sqlglot
    try:
        parsed = sqlglot.parse_one(sql, dialect="mysql")
    except ParseError as e:
        return False, f"SQL invalide (AST) : {e}"

    # 5. Vérifier les tables utilisées
    tables_used = {
        t.name.lower()
        for t in parsed.find_all(sqlglot.exp.Table)
    }
    unauthorized = tables_used - {t.lower() for t in ALLOWED_TABLES}
    if unauthorized:
        return False, f"Tables non autorisées : {unauthorized}"

    return True, "OK"

def enforce_business_rules(sql: str) -> str:
    """
    Enforce règles métier critiques après génération LLM
    """
    sql_lower = sql.lower()

    if "entity = 1" not in sql_lower:
        raise ValueError("Filtre entity = 1 manquant.")

    if "limit" not in sql_lower:
        sql += " LIMIT 200"

    return sql

def sanitize(value: str) -> str:
    return re.sub(r"[;--]", "", value.replace("'", "''"))

def inject_params(sql: str, params: dict) -> str:
    result = sql
    for key, value in params.items():
        if str(value).isdigit():
            result = result.replace(f":{key}", str(value))
        else:
            result = result.replace(f":{key}", f"'{sanitize(value)}'")
    return result


# ─── Moteur Templates V1/V2 ───────────────────────────────────────────────────

def load_templates(templates_file: str = "templates.json") -> dict:
    if not os.path.exists(templates_file):
        return {}

    with open(templates_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    templates = data.get("templates", {})

    return templates


def match_template(question: str, templates: dict):
    """
    Matching sémantique via embeddings + fallback mots-clés
    """
    if not templates:
        return None, None, {}

    question_lower = question.lower()

    # ── Fallback 1 : matching par mots-clés exact (prioritaire) ──
    for tid, t in templates.items():
        if not t.get("active", True):
            continue
        keywords = t.get("keywords", [])
        if not keywords:
            continue
        matches = sum(1 for kw in keywords if kw.lower() in question_lower)
        # Si au moins 2 mots-clés matchent → c'est ce template
        ratio = matches / len(keywords)
        if ratio >= 0.6:
            params = extract_params_from_question(question, t.get("params", []))
            logger.info(f"[KEYWORD MATCH] tid={tid} matches={matches}")
            return tid, t, params
        # Si 1 seul mot-clé mais très spécifique (> 6 chars) → aussi valide
        if matches == 1:
            matching_kw = [kw for kw in keywords if kw.lower() in question_lower]
            if matching_kw and len(matching_kw[0]) > 6:
                params = extract_params_from_question(question, t.get("params", []))
                logger.info(f"[KEYWORD MATCH SINGLE] tid={tid} kw={matching_kw[0]}")
                return tid, t, params

    # ── Fallback 2 : embeddings avec seuil abaissé ──
    if not TEMPLATE_EMBEDDINGS:
        return None, None, {}

    q_emb = embedding_model.encode(question, normalize_embeddings=True)
    best_score = -1
    best_tid = None

    for tid, t_emb in TEMPLATE_EMBEDDINGS.items():
        score = util.cos_sim(q_emb, t_emb)[0][0].item()
        if score > best_score:
            best_score = score
            best_tid = tid

    # ── Seuil abaissé de 0.70 à 0.55 ──
    THRESHOLD = 0.55

    if best_score < THRESHOLD:
        return None, None, {}

    template = templates.get(best_tid, {})
    params = extract_params_from_question(question, template.get("params", []))

    logger.info(f"[EMBEDDING MATCH] tid={best_tid} score={round(best_score, 3)}")
    return best_tid, template, params

def extract_params_from_question(question: str, param_names: list) -> dict:
    """Extraction des paramètres depuis la question (regex améliorée)."""
    params = {}
    q = question.lower()

    MOIS_MAP = {
        "janvier": "01", "février": "02", "fevrier": "02",
        "mars": "03", "avril": "04", "mai": "05", "juin": "06",
        "juillet": "07", "août": "08", "aout": "08",
        "septembre": "09", "octobre": "10", "novembre": "11",
        "décembre": "12", "decembre": "12",
    }

    for p in param_names:
        p_lower = p.lower()

        # ── Dates (format YYYY-MM-DD ou DD/MM/YYYY) ──
        if "date" in p_lower or "debut" in p_lower or "fin" in p_lower:
            dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', question)
            if "debut" in p_lower and len(dates) >= 1:
                params[p] = dates[0]
            elif "fin" in p_lower and len(dates) >= 2:
                params[p] = dates[1]
            elif dates:
                params[p] = dates[0]

        # ── Année ──
        elif p_lower in ("annee", "year", "annee_commande", "annee_facture"):
            years = re.findall(r'\b(20\d{2})\b', question)
            if years:
                params[p] = years[0]
            else:
                from datetime import datetime
                params[p] = str(datetime.today().year)

        # ── Mois numérique (ex: :mois) ──
        elif p_lower in ("mois", "month", "mois_commande", "mois_facture"):
            # Cherche d'abord un mois en texte
            for mois_nom, mois_num in MOIS_MAP.items():
                if mois_nom in q:
                    params[p] = mois_num
                    break
            # Sinon cherche un format YYYY-MM
            if p not in params:
                ym = re.search(r'\d{4}-(\d{2})', question)
                if ym:
                    params[p] = ym.group(1)
            # Sinon mois courant
            if p not in params:
                from datetime import datetime
                params[p] = str(datetime.today().month).zfill(2)

        # ── Seuil / limite / client / nom ──
        elif p_lower in ("seuil", "seuil_stock"):
            numbers = re.findall(r'\b(\d+)\b', question)
            params[p] = numbers[0] if numbers else "10"

        elif p_lower in ("limit", "nb", "top", "nombre"):
            numbers = re.findall(r'\b(\d+)\b', question)
            params[p] = numbers[0] if numbers else "10"

        elif p_lower == "client":
            # Cherche un nom propre après "client" ou "pour"
            match = re.search(
                r'(?:client|pour|de)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\-]{1,40})',
                question, re.IGNORECASE
            )
            if match:
                params[p] = f"%{match.group(1).strip()}%"
            else:
                params[p] = "%"

        # ── Fallback générique ──
        else:
            numbers = re.findall(r'\b(\d+)\b', question)
            if numbers:
                params[p] = numbers[0]

    return params


# ─── Moteur LLM (Claude Anthropic via OpenRouter) ────────────────────────────

SCHEMA_SUMMARY = """
Tables autorisées (MariaDB / Dolibarr) :
- m38h_facture : ref, datef, total_ht, total_ttc, fk_soc, paye, fk_statut, entity
- m38h_facturedet : fk_facture, fk_product, qty, total_ht
- m38h_societe : rowid, nom, email, entity
- m38h_commande : rowid, fk_soc, date_commande, total_ht, total_ttc, entity
- m38h_commandedet : fk_commande, fk_product, qty, total_ht
- m38h_product : rowid, ref, label, tosell, entity
- m38h_product_stock : fk_product, fk_entrepot, reel
- m38h_entrepot : rowid, label
- m38h_paiement_facture : fk_facture, amount
- m38h_paiement : rowid, datep, amount

Règles ABSOLUES :
1. SELECT uniquement — jamais INSERT/UPDATE/DELETE/DROP/ALTER
2. Toujours inclure LIMIT (max 200)
3. Utiliser uniquement les tables listées ci-dessus
4. Ne jamais exposer les colonnes : pass, password, api_key, token
5. Toujours filtrer par entity = 1
"""

SYSTEM_PROMPT_ROUTER = f"""
Tu es un assistant NL2SQL pour une base Dolibarr (MariaDB).
Ton rôle : identifier l'intent de la question et extraire les paramètres.

{SCHEMA_SUMMARY}

IMPORTANT :
- Tu DOIS répondre uniquement avec un JSON valide
- AUCUN texte avant ou après
- PAS de ```json
- PAS d'explication
- PAS de commentaire
- Si tu ne respectes pas ce format, la réponse sera rejetée

Réponds STRICTEMENT au format JSON suivant :
Format attendu :
{{
  "intent": "nom_intent",
  "confidence": 0.95,
  "params": {{
    "param1": "valeur1"
  }},
  "needs_sql_generation": true,
  "reason": "courte explication"
}}

Si la question peut être résolue par un template existant, needs_sql_generation = false.
Si la question est trop complexe ou hors templates, needs_sql_generation = true.
Si la question est hors périmètre DB, intent = "out_of_scope".
"""

SYSTEM_PROMPT_SQL = f"""
Tu es un expert SQL spécialisé en MariaDB (Dolibarr).

{SCHEMA_SUMMARY}

Ta mission : générer UNE requête SQL correcte.

RÈGLES STRICTES :
- SELECT uniquement
- LIMIT 200 obligatoire
- Utiliser uniquement les tables autorisées
- Toujours inclure : entity = 1
- Ne jamais modifier les données (pas de INSERT, UPDATE, DELETE, DROP...)

IMPORTANT :
- Si la question contient "par client" → utiliser GROUP BY
- Utiliser SUM() pour les montants
- Utiliser JOIN avec m38h_societe pour les clients
- Si la question contient "combien" → utiliser COUNT(*)
- Si la question contient "commandes" → utiliser m38h_commande
- Si la question contient un mois + année → filtrer avec MONTH() et YEAR()

Exemple :
SELECT COUNT(*) as total
FROM m38h_commande
WHERE MONTH(date_commande) = 3
AND YEAR(date_commande) = 2026
AND entity = 1
LIMIT 200

FORMAT DE SORTIE :
- Retourne UNIQUEMENT la requête SQL
- PAS de JSON
- PAS d'explication
- PAS de texte avant ou après

EXEMPLE :
SELECT s.nom, SUM(f.total_ttc)
FROM m38h_facture f
JOIN m38h_societe s ON f.fk_soc = s.rowid
WHERE YEAR(f.datef) = 2026 AND f.entity = 1
GROUP BY s.nom
LIMIT 200
"""

def clean_llm_json(raw: str) -> str:
    if not raw:
        return ""

    raw = re.sub(r"```json", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"```", "", raw)

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return match.group(0)

    return raw.strip()

def llm_classify_intent(question: str, templates: dict) -> dict:
    """
    Utilise Claude pour classifier l'intent et extraire les paramètres.
    Retourne un dict avec intent, confidence, params, needs_sql_generation.
    """
    templates_summary = "\n".join(
        f"- {tid}: {t.get('description','—')} (keywords: {t.get('keywords',[])})"
        for tid, t in templates.items()
        if t.get("active", True)
    )

    user_msg = f"""
Templates disponibles :
{templates_summary}

Question utilisateur : "{question}"

Identifie l'intent et extrais les paramètres.
"""
    prompt = SYSTEM_PROMPT_ROUTER + "\n\n" + user_msg
    raw = call_ollama(prompt)    
    logger.debug(f"LLM router raw response: {repr(raw)}")

    raw = clean_llm_json(raw)

    try:
        parsed = json.loads(raw)

    # Sécurité minimale
        if not isinstance(parsed, dict):
            raise ValueError("Réponse non dict")

        return parsed

    except Exception as e:
        logger.error(f"LLM JSON invalide (router): {raw}")

        raw_fixed = raw.replace(",}", "}").replace(",]", "]")

        try:
            return json.loads(raw_fixed)
        except Exception:
            return {
            "intent": "unknown",
            "confidence": 0,
            "params": {},
            "needs_sql_generation": True,
            "reason": "fallback JSON parsing failed"
        }

def llm_generate_sql(question: str, cache: dict = None) -> dict:    
    """
    Génère du SQL via Ollama (robuste, sans dépendance stricte au JSON)
    """
    
    cache_key = re.sub(r"\s+", " ", question.strip().lower())

    if cache and cache_key in cache:
        logger.info("[LLM CACHE HIT]")
        return cache[cache_key]

    user_msg = f'Génère une requête SQL pour : "{question}"'

    # ── Étape 1 : appel Ollama ──
    try:
        prompt = SYSTEM_PROMPT_SQL + "\n\n" + user_msg
        raw = call_ollama(prompt)
        logger.debug(f"LLM SQL raw response: {repr(raw)}")
    except Exception as e:
        logger.error(f"Erreur appel LLM : {e}")
        return {
            "sql": "",
            "explanation": f"Erreur appel LLM : {str(e)}",
            "confidence": 0
        }

    if not raw:
        return {
            "sql": "",
            "explanation": "Réponse vide du LLM",
            "confidence": 0
        }

    # ── Étape 2 : tentative parsing JSON (optionnelle) ──
    sql = ""
    explanation = ""
    confidence = 0

    raw_clean = clean_llm_json(raw)

    # ── Étape 3 : extraction robuste SQL ──
    if not sql or not isinstance(sql, str):

        logger.warning("Extraction SQL depuis texte brut...")

        try:
            parsed = sqlglot.parse_one(raw, dialect="mysql")
            sql = parsed.sql()

        except Exception:
            # fallback regex : SELECT ... LIMIT
            match = re.search(
                r"(?i)(SELECT[\s\S]*?LIMIT\s+\d+)",
                raw,
                re.IGNORECASE | re.DOTALL
            )

            if match:
                sql = match.group(1)
            else:
                # fallback : SELECT ... ;
                match = re.search(
                    r"(SELECT .*?;)",
                    raw,
                    re.IGNORECASE | re.DOTALL
                )
                if match:
                    sql = match.group(1)

        # fallback ultime
        if not sql:
            match = re.search(
                r"(SELECT .*)",
                raw,
                re.IGNORECASE | re.DOTALL
            )
            if match:
                sql = match.group(1)

    # ── Étape 4 : validation finale ──
    if not sql or not isinstance(sql, str):
        logger.error(f"SQL introuvable dans réponse LLM : {raw}")
        return {
            "sql": "",
            "explanation": "SQL non trouvé dans la réponse LLM",
            "confidence": 0
        }

    sql = sql.strip()

    try:
        sql = enforce_business_rules(sql)
    except Exception as e:
        return {
        "sql": "",
        "explanation": str(e),
        "confidence": 0
    }


    # ── Étape 5 : sécurisation LIMIT ──

    if cache is not None:
        cache[cache_key] = {
        "sql": sql,
        "explanation": explanation or "SQL généré via Ollama",
        "confidence": confidence or 0.7
    }
    
    return {
        "sql": sql,
        "explanation": explanation or "SQL généré via Ollama",
        "confidence": confidence or 0.7
    }
    

# ─── Moteur hybride principal ─────────────────────────────────────────────────
class HybridEngine:
    """
    Moteur hybride NL2SQL.
    Stratégie : Templates V1/V2 → LLM router → LLM SQL generation → erreur.
    """

    def __init__(self, templates_file: str = "templates.json"):
        self.templates_file = templates_file
        self.templates = load_templates(templates_file)
        build_template_embeddings(self.templates)
        self._llm_cache = {}

    def cache_key(self, question: str) -> str:
        return question.strip().lower()
    
    def reload_templates(self):
        self.templates = load_templates(self.templates_file)
        build_template_embeddings(self.templates)
    
    def process(self, question: str) -> HybridResult:
        start = time.time()
        question = question.strip()

        # debug tracing global
        logger.info(f"[QUERY] {question}")

        # ── Étape 1 : Matching templates V1/V2 ──────────────────────────────
        tid, template, params = match_template(question, self.templates)

        if tid and template:
            sql_template = template.get("sql", "")
            required_params = template.get("params", [])


    # ── Vérifier les paramètres manquants ──
            missing = [p for p in required_params if p not in params]
            if missing:
                logger.warning(
            f"Template {tid} : paramètres manquants {missing} "
            f"— tentative avec valeurs par défaut"
        )
        # Valeurs par défaut pour les paramètres manquants
                from datetime import datetime
                defaults_map = {
            "limit":  "10",
            "annee":  str(datetime.today().year),
            "mois":   str(datetime.today().month).zfill(2),
            "seuil":  "10",
            "seuil_stock": "10",
            "client": "%",
        }
                for m in missing:
                    if m.lower() in defaults_map:
                        params[m] = defaults_map[m.lower()]
                    else:
                        params[m] = "10"  # fallback numérique

            sql_final = inject_params(sql_template, params)
            valid, err = validate_sql_security(sql_final)

            if valid:
                return HybridResult(
            question=question,
            mode="template",
            intent=template.get("intent", tid),
            sql=sql_final,
            params=params,
            valid=True,
            error=None,
            llm_called=False,
            duration_ms=round((time.time() - start) * 1000, 2),
        )
            else:
                logger.warning(f"Template {tid} SQL invalide après injection : {err}")

    # ── Étape 2 : LLM Router ──────────────────────────────
        llm_classification = {
        "intent": "unknown",
        "params": {},
        "needs_sql_generation": False
    }

        try:
            llm_classification = llm_classify_intent(question, self.templates)
        except Exception as e:
            logger.error(f"Router error: {e}")

        intent = llm_classification.get("intent", "unknown")
        llm_params = llm_classification.get("params", {})
        needs_sql = llm_classification.get("needs_sql_generation", False)

    # sécurité hors périmètre
        if intent == "out_of_scope":
            return HybridResult(
            question=question,
            mode="fallback_error",
            intent="out_of_scope",
            sql=None,
            params={},
            valid=False,
            error="Question hors périmètre.",
            llm_called=True,
            duration_ms=round((time.time() - start) * 1000, 2),
        )

    # ── Étape 3 : LLM génère le SQL directement ───────────────────
        if needs_sql:
            valid = False
            err = None      
            try:
                llm_sql_result = llm_generate_sql(question, self._llm_cache)
                generated_sql = llm_sql_result.get("sql", "")

                if not generated_sql or not isinstance(generated_sql, str):
                    return HybridResult(
                    question=question,
                    mode="fallback_error",
                    intent=intent,
                    sql=None,
                    params={},
                    valid=False,
                    error="SQL vide généré par le LLM.",
                    llm_called=True,
                    duration_ms=round((time.time() - start) * 1000, 2),
                )

                valid, err = validate_sql_security(generated_sql)

            # 🔥 FALLBACK INTELLIGENT SI SQL INVALIDE
                if not valid:
                    logger.warning("SQL invalide → fallback intelligent activé")

                    q = question.lower()

                # 👉 cas "combien de commandes"
                    if "combien" in q and "commande" in q:

                        mois_map = {
                        "janvier": 1, "février": 2, "mars": 3, "avril": 4,
                        "mai": 5, "juin": 6, "juillet": 7, "août": 8,
                        "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
                        }

                        mois = None
                        for nom, num in mois_map.items():
                            if nom in q:
                                mois = num
                                break

                        year_match = re.search(r"(20\d{2})", q)
                        annee = year_match.group(1) if year_match else "2026"

                        if mois:
                            generated_sql = f"""
SELECT COUNT(*) as total
FROM m38h_commande
WHERE MONTH(date_commande) = {mois}
AND YEAR(date_commande) = {annee}
AND entity = 1
LIMIT 200
"""
                            valid, err = validate_sql_security(generated_sql)
                        else:
                            valid = False
                            err = "mois introuvable"

            # ── résultat final ──────────────────────────────
                if valid:
                    return HybridResult(
                    question=question,
                    mode="llm_sql",
                    intent=intent,
                    sql=generated_sql,
                    params=llm_params,
                    valid=True,
                    error=None,
                    llm_called=True,
                    duration_ms=round((time.time() - start) * 1000, 2),
                    warning="SQL généré par LLM — vérifié par AST mais à valider manuellement.",
                )
                else:
                    return HybridResult(
                    question=question,
                    mode="fallback_error",
                    intent=intent,
                    sql=None,
                    params=llm_params,
                    valid=False,
                    error=f"SQL généré par LLM invalide : {err}",
                    llm_called=True,
                    duration_ms=round((time.time() - start) * 1000, 2),
                )

            except Exception as e:
                logger.error(f"Erreur LLM SQL : {e}")
                return HybridResult(
                question=question,
                mode="fallback_error",
                intent=intent,
                sql=None,
                params={},
                valid=False,
                error=f"Erreur lors de l'appel LLM : {str(e)}",
                llm_called=True,
                duration_ms=round((time.time() - start) * 1000, 2),
            )

        if 'generated_sql' in locals():
            logger.info(json.dumps({
        "question": question,
        "mode": "llm_sql",
        "sql": generated_sql,
        "valid": valid,
        "duration_ms": round((time.time() - start) * 1000, 2)
    }))

    # ── Étape 4 : Aucune solution trouvée ────────────────────────────────
        return HybridResult(
        question=question,
        mode="fallback_error",
        intent=intent,
        sql=None,
        params={},
        valid=False,
        error="Aucun template ni SQL valide trouvé pour cette question.",
        llm_called=True,
        duration_ms=round((time.time() - start) * 1000, 2),
    )

