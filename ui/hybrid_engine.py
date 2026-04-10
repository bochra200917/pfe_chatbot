"""
hybrid_engine.py
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

from openai import OpenAI
import sqlglot
from sqlglot.errors import ParseError

logger = logging.getLogger(__name__)

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

MAX_ROWS = 200
LLM_CONFIDENCE_THRESHOLD = 0.0  # fallback déclenché si templates échouent

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


# ─── Validation SQL ───────────────────────────────────────────────────────────

def validate_sql_security(sql: str) -> tuple[bool, str]:
    """
    Valide qu'un SQL est SELECT-only, sans mots interdits,
    avec LIMIT, et via parsing AST (sqlglot).
    """
    sql_upper = sql.upper().strip()

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


def inject_params(sql: str, params: dict) -> str:
    """Remplace les :param par leurs valeurs (strings entre guillemets)."""
    result = sql
    for key, value in params.items():
        result = result.replace(f":{key}", f"'{value}'")
    return result


# ─── Moteur Templates V1/V2 ───────────────────────────────────────────────────

def load_templates(templates_file: str = "templates.json") -> dict:
    if not os.path.exists(templates_file):
        return {}
    with open(templates_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("templates", {})


def match_template(question: str, templates: dict) -> tuple[Optional[str], Optional[dict], dict]:
    """
    Tente de matcher la question à un template via mots-clés.
    Retourne (template_id, template, params_extraits) ou (None, None, {}).
    """
    question_lower = question.lower()

    for tid, t in templates.items():
        if not t.get("active", True):
            continue
        keywords = t.get("keywords", [])
        if not keywords:
            continue
        score = sum(1 for kw in keywords if kw.lower() in question_lower)
        if score >= 1:
            params = extract_params_from_question(question, t.get("params", []))
            return tid, t, params

    return None, None, {}


def extract_params_from_question(question: str, param_names: list) -> dict:
    """Extraction basique des paramètres depuis la question (regex)."""
    params = {}
    q = question.lower()

    for p in param_names:
        p_lower = p.lower()

        # Dates (format YYYY-MM-DD ou DD/MM/YYYY)
        if "date" in p_lower or "debut" in p_lower or "fin" in p_lower:
            dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}', question)
            if "debut" in p_lower and len(dates) >= 1:
                params[p] = dates[0]
            elif "fin" in p_lower and len(dates) >= 2:
                params[p] = dates[1]
            elif dates:
                params[p] = dates[0]

        # Année
        elif "annee" in p_lower or "year" in p_lower:
            years = re.findall(r'\b(20\d{2})\b', question)
            if years:
                params[p] = years[0]

        # Seuil / limite numérique
        elif "seuil" in p_lower or "limit" in p_lower or "nb" in p_lower or "top" in p_lower:
            numbers = re.findall(r'\b(\d+)\b', question)
            if numbers:
                params[p] = numbers[0]
            else:
                params[p] = "200" if "limit" in p_lower else "10"

        # Mois en texte
        elif "mois" in p_lower:
            mois_map = {
                "janvier": "01", "février": "02", "mars": "03", "avril": "04",
                "mai": "05", "juin": "06", "juillet": "07", "août": "08",
                "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12",
            }
            for mois_nom, mois_num in mois_map.items():
                if mois_nom in q:
                    params[p] = mois_num
                    break

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

Réponds UNIQUEMENT en JSON valide, sans texte avant ni après, sans balises markdown.
Format attendu :
{{
  "intent": "nom_intent",
  "confidence": 0.95,
  "params": {{
    "param1": "valeur1"
  }},
  "needs_sql_generation": false,
  "reason": "courte explication"
}}

Si la question peut être résolue par un template existant, needs_sql_generation = false.
Si la question est trop complexe ou hors templates, needs_sql_generation = true.
Si la question est hors périmètre DB, intent = "out_of_scope".
"""

SYSTEM_PROMPT_SQL = f"""
Tu es un générateur SQL sécurisé pour une base Dolibarr (MariaDB).

{SCHEMA_SUMMARY}

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ni après, sans balises markdown.
Format attendu :
{{
  "sql": "SELECT ... FROM ... WHERE ... LIMIT 200",
  "explanation": "courte explication de la requête",
  "confidence": 0.9
}}

La requête SQL doit :
- Commencer par SELECT
- Contenir LIMIT (max 200)
- N'utiliser que les tables autorisées
- Ne jamais modifier les données
"""


def call_claude(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
    """Appelle Claude via OpenRouter et retourne le texte de la réponse."""
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )
    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4.6",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content.strip()


def clean_llm_json(raw: str) -> str:
    """Nettoie la réponse LLM pour extraire uniquement le JSON."""
    raw = re.sub(r'```json\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)
    raw = raw.strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        return match.group(0)
    return raw


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
    raw = call_claude(SYSTEM_PROMPT_ROUTER, user_msg, max_tokens=300)
    logger.debug(f"LLM router raw response: {repr(raw)}")

    raw = clean_llm_json(raw)
    return json.loads(raw)


def llm_generate_sql(question: str) -> dict:
    """
    Utilise Claude pour générer directement le SQL pour une question complexe.
    Retourne un dict avec sql, explanation, confidence.
    """
    user_msg = f'Génère une requête SQL pour : "{question}"'
    raw = call_claude(SYSTEM_PROMPT_SQL, user_msg, max_tokens=500)
    logger.debug(f"LLM SQL raw response: {repr(raw)}")

    raw = clean_llm_json(raw)
    return json.loads(raw)


# ─── Moteur hybride principal ─────────────────────────────────────────────────

class HybridEngine:
    """
    Moteur hybride NL2SQL.
    Stratégie : Templates V1/V2 → LLM router → LLM SQL generation → erreur.
    """

    def __init__(self, templates_file: str = "templates.json"):
        self.templates_file = templates_file
        self.templates = load_templates(templates_file)

    def reload_templates(self):
        self.templates = load_templates(self.templates_file)

    def process(self, question: str) -> HybridResult:
        start = time.time()
        question = question.strip()

        # ── Étape 1 : Matching templates V1/V2 ──────────────────────────────
        tid, template, params = match_template(question, self.templates)

        if tid and template:
            sql_template = template.get("sql", "")
            required_params = template.get("params", [])
            missing = [p for p in required_params if p not in params]

            if not missing:
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
                    logger.warning(f"Template {tid} SQL invalide : {err}")
            else:
                logger.info(f"Template {tid} : paramètres manquants {missing} — passage au LLM")

        # ── Étape 2 : LLM Router (classify + extract params) ─────────────────
        try:
            llm_classification = llm_classify_intent(question, self.templates)
            intent = llm_classification.get("intent", "unknown")
            llm_params = llm_classification.get("params", {})
            needs_sql = llm_classification.get("needs_sql_generation", False)

            # Hors périmètre
            if intent == "out_of_scope":
                return HybridResult(
                    question=question,
                    mode="fallback_error",
                    intent="out_of_scope",
                    sql=None,
                    params={},
                    valid=False,
                    error="Question hors périmètre de la base de données.",
                    llm_called=True,
                    duration_ms=round((time.time() - start) * 1000, 2),
                )

            # LLM a identifié un template existant
            if not needs_sql and intent in self.templates:
                t = self.templates[intent]
                sql_template = t.get("sql", "")
                sql_final = inject_params(sql_template, llm_params)
                valid, err = validate_sql_security(sql_final)

                if valid:
                    return HybridResult(
                        question=question,
                        mode="llm_router",
                        intent=intent,
                        sql=sql_final,
                        params=llm_params,
                        valid=True,
                        error=None,
                        llm_called=True,
                        duration_ms=round((time.time() - start) * 1000, 2),
                    )

            # ── Étape 3 : LLM génère le SQL directement ───────────────────
            if needs_sql:
                llm_sql_result = llm_generate_sql(question)
                generated_sql = llm_sql_result.get("sql", "")

                valid, err = validate_sql_security(generated_sql)
                if valid:
                    return HybridResult(
                        question=question,
                        mode="llm_sql",
                        intent=intent,
                        sql=generated_sql,
                        params={},
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
                        params={},
                        valid=False,
                        error=f"SQL généré par LLM invalide : {err}",
                        llm_called=True,
                        duration_ms=round((time.time() - start) * 1000, 2),
                    )

        except json.JSONDecodeError as e:
            logger.error(f"LLM JSON invalide : {e}")
            return HybridResult(
                question=question,
                mode="fallback_error",
                intent=None,
                sql=None,
                params={},
                valid=False,
                error="Réponse LLM mal formée (JSON invalide).",
                llm_called=True,
                duration_ms=round((time.time() - start) * 1000, 2),
            )
        except Exception as e:
            logger.error(f"Erreur LLM : {e}")
            return HybridResult(
                question=question,
                mode="fallback_error",
                intent=None,
                sql=None,
                params={},
                valid=False,
                error=f"Erreur lors de l'appel LLM : {str(e)}",
                llm_called=True,
                duration_ms=round((time.time() - start) * 1000, 2),
            )

        # ── Étape 4 : Aucune solution trouvée ────────────────────────────────
        return HybridResult(
            question=question,
            mode="fallback_error",
            intent=None,
            sql=None,
            params={},
            valid=False,
            error="Aucun template ni SQL valide trouvé pour cette question.",
            llm_called=True,
            duration_ms=round((time.time() - start) * 1000, 2),
        )