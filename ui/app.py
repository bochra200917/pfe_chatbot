# ui/app.py
import streamlit as st
import requests
import pandas as pd
import html
import io
import json
import os
import streamlit.components.v1 as components
import matplotlib.pyplot as plt  # Déjà présent
import numpy as np  # À ajouter si pas déjà présent

from datetime import datetime, date
try:
    import importlib.util, os as _os
    _spec = importlib.util.spec_from_file_location(
        "pdf_export",
        _os.path.join(_os.path.dirname(__file__), "pdf_export.py")
    )
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    generate_pdf_report = _mod.generate_pdf_report
except Exception:
    generate_pdf_report = None

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
import os

API_USER       = "admin"
API_PASS       = "1234"
DOLIBARR_BASE_URL = "https://demonstration.cieloo.io"

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

API_URL        = f"{BASE_URL}/ask"
HYBRID_API_URL = os.getenv("HYBRID_API_URL", "http://localhost:8001/ask")
EXECUTE_URL    = f"{BASE_URL}/execute"

st.set_page_config(
    page_title="Chatbot ZAI Informatique",
    page_icon="💬",  # emoji conservé car c'est l'icône du navigateur, pas visible dans l'app
    layout="wide"
)

# ─────────────────────────────────────────────
# Fonctions utilitaires
# ─────────────────────────────────────────────

def month_name(m):
    names = {
        "01": "janvier", "02": "février", "03": "mars",
        "04": "avril",   "05": "mai",     "06": "juin",
        "07": "juillet", "08": "août",    "09": "septembre",
        "10": "octobre", "11": "novembre","12": "décembre"
    }
    return names.get(m, m)

# ─────────────────────────────────────────────
# CSS — Style Dolibarr / Cieloo (amélioré)
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');
@import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300..900&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}
code, pre, .stCode {
    font-family: 'JetBrains Mono', monospace !important;
}
/* Uniformiser la hauteur des boutons d'exemples et centrer le texte verticalement */
.example-buttons-wrapper .stButton button {
    min-height: 70px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    white-space: normal;
    word-break: break-word;
}
.fa-solid, .fa-regular, .fa-brands {
    font-size: inherit;
    vertical-align: middle;
    margin-right: 4px;
}
/* Tokens de couleurs (Dolibarr) */
:root {
    --bg-doli: #f6f9ff;
    --card-doli: #ffffff;
    --ink-doli: #0f172a;
    --muted-doli: #6b7280;
    --border-doli: #e6eaf2;
    --primary-doli: #2d6cdf;
    --primary-ink: #1f4fb0;
    --radius-doli: 14px;
    --shadow-doli: 0 10px 25px rgba(17,24,39,.06);
    --blue-doli: #2563eb;
    --blue-2: #3b82f6;
}

/* Fond général */
.main .block-container {
    background: linear-gradient(145deg, #f3f6fc 0%, #fafdff 100%);
}

/* Header du chat */
.chat-title {
    font-size: 1.8rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
    background: linear-gradient(135deg, #1e3a8a, #2563eb);
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
    letter-spacing: -0.3px;
}
.chat-subtitle {
    font-size: 0.95rem;
    color: var(--muted-doli);
    margin-bottom: 1.5rem;
    border-left: 3px solid var(--blue-doli);
    padding-left: 12px;
}

/* Cartes de résultat */
.result-box {
    background: var(--card-doli);
    border-radius: var(--radius-doli);
    padding: 1.2rem 1.5rem;
    border-left: 4px solid #4CAF50;
    margin-top: 1rem;
    box-shadow: var(--shadow-doli);
    transition: transform 0.2s, box-shadow 0.2s;
}
.result-box:hover {
    transform: translateY(-2px);
    box-shadow: 0 20px 30px rgba(17,24,39,0.08);
}
.rejected-box {
    background: #fff5f5;
    border-radius: var(--radius-doli);
    padding: 1.2rem 1.5rem;
    border-left: 4px solid #e53935;
    box-shadow: var(--shadow-doli);
    color: #b91c1c !important;
}
.clarification-box {
    background: #fffbeb;
    border-radius: var(--radius-doli);
    padding: 1.2rem 1.5rem;
    border-left: 4px solid #f59e0b;
    box-shadow: var(--shadow-doli);
    color: #92400e !important;
}
.llm-badge {
    background: #f3e8ff;
    border-radius: var(--radius-doli);
    padding: 0.5rem 1rem;
    border-left: 4px solid #9333ea;
    font-weight: 500;
    margin: 1rem 0;
    box-shadow: var(--shadow-doli);
}

/* Métadonnées (chips) */
.meta-chip, .meta-chip-llm {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 30px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-right: 8px;
    margin-bottom: 8px;
    background: #f1f5f9;
    color: #1e293b;
    font-family: 'JetBrains Mono', monospace;
}
.meta-chip-llm {
    background: #ede9fe;
    color: #6d28d9;
}

/* Boîte de suggestion */
.suggestion-box {
    background: #f8fafc;
    border-radius: var(--radius-doli);
    padding: 0.8rem 1rem;
    border-left: 4px solid #6366f1;
    margin: 1rem 0;
    box-shadow: var(--shadow-doli);
}
.suggestion-box span {
    color: var(--ink-doli) !important;
}

/* Historique */
.history-wrapper {
    background: var(--card-doli);
    border-radius: var(--radius-doli);
    border: 1px solid var(--border-doli);
    box-shadow: var(--shadow-doli);
    padding: 8px;
    height: 520px;
    overflow-y: auto;
}
.history-item {
    background: var(--card-doli);
    border-radius: 10px;
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.5rem;
    border: 1px solid #eef2f6;
    transition: all 0.1s;
}
.history-item:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
}
.history-item strong {
    color: var(--blue-doli);
}

/* Tableaux Dolibarr */
.dolibarr-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}
.dolibarr-table th {
    background: #f1f5f9;
    padding: 10px 12px;
    border-bottom: 2px solid #e2e8f0;
    font-weight: 600;
    color: var(--ink-doli);
}
.dolibarr-table td {
    padding: 8px 12px;
    border-bottom: 1px solid #eef2f6;
    color: var(--ink-doli);
}
.dolibarr-table tr:hover td {
    background: #f1f5f9;
}
.dolibarr-table-wrapper {
    max-height: 450px;
    overflow-y: auto;
    border-radius: 16px;
    border: 1px solid var(--border-doli);
    background: white;
}

/* Boutons modernes */
.stButton button {
    background: linear-gradient(135deg, var(--blue-doli), var(--blue-2)) !important;
    color: white !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: 0 2px 6px rgba(37,99,235,0.2);
    transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.stButton button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 14px rgba(37,99,235,0.3);
}
.stButton button:active {
    transform: translateY(1px);
}

/* Dialog (popup assistant) */
div[role="dialog"] {
    background: var(--card-doli) !important;
    border-radius: 20px !important;
    border: 1px solid var(--border-doli) !important;
    box-shadow: 0 25px 40px rgba(0,0,0,0.12) !important;
}
div[role="dialog"] [data-testid="stMarkdownContainer"] p {
    color: var(--ink-doli) !important;
}

/* Champs de formulaire */
.stTextInput > div > input {
    border-radius: 12px !important;
    border: 2px solid #2563eb !important;   /* contour bleu permanent */
    background-color: #ffffff;
    transition: 0.15s;
}
.stTextInput > div > input:focus {
    border-color: #1e40af !important;       /* bleu plus foncé au focus */
    box-shadow: 0 0 0 3px rgba(37,99,235,0.2) !important;
}
.stTextInput > div > input:focus, .stSelectbox > div > select:focus, .stTextArea textarea:focus {
    border-color: var(--blue-doli) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
}

/* Onglets (radio horizontal) */
div[data-baseweb="radio"] {
    background: white;
    padding: 4px;
    border-radius: 40px;
    border: 1px solid var(--border-doli);
    display: inline-flex;
    gap: 6px;
    margin-bottom: 1.5rem;
}
div[data-baseweb="radio"] label {
    border-radius: 30px;
    padding: 6px 20px;
    font-weight: 500;
    transition: 0.2s;
}
div[data-baseweb="radio"] label[data-checked="true"] {
    background: var(--blue-doli);
    color: white !important;
}
div[data-baseweb="radio"] label[data-checked="true"] span {
    color: white !important;
}

/* Expander */
[data-testid="stExpander"] {
    border: 1px solid var(--border-doli);
    border-radius: 16px;
    background: var(--card-doli);
    box-shadow: var(--shadow-doli);
}
[data-testid="stExpander"] summary {
    font-weight: 600;
    padding: 0.8rem 1.2rem;
}

/* Alertes */
.stAlert {
    border-radius: 12px;
    border-left-width: 4px;
}

/* Messages d'info / succès */
.stSuccess, .stInfo, .stWarning, .stError {
    border-radius: 12px !important;
}

/* Légères améliorations pour les métriques */
[data-testid="stMetricValue"] {
    font-weight: 700;
    color: var(--blue-doli);
}
[data-testid="stMetricDelta"] {
    font-size: 0.8rem;
}
/* Force le contour bleu permanent sur l'input */
div[data-testid="stTextInput"] input {
    border: 2px solid #2563eb !important;
    border-radius: 12px !important;
    background-color: #ffffff !important;
    box-shadow: none !important;
}

/* Au focus : bordure plus foncée */
div[data-testid="stTextInput"] input:focus {
    border-color: #1e40af !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.2) !important;
    outline: none !important;
}

/* 🔥 Force le contour bleu de l'input (si toujours invisible) */
div[data-testid="stTextInput"] input {
    border: 2px solid #2563eb !important;
    background: white !important;
    border-radius: 12px !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #1e40af !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.2) !important;
}
/* Force l'uniformisation des boutons exemples - solution robuste */
.example-buttons-wrapper div[data-testid="stButton"] button {
    min-height: 70px !important;
    height: auto !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    white-space: normal !important;
    word-break: break-word !important;
    vertical-align: middle !important;
}
/* Alternative : cible directement tous les boutons des 5 premières colonnes */
div[data-testid="column"]:nth-child(-n+5) button {
    min-height: 70px !important;
    height: auto !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    white-space: normal !important;
}
/* Uniformisation des boutons dans le popup assistant (identique aux exemples) */
div[role="dialog"] .stButton button {
    background: linear-gradient(135deg, var(--blue-doli), var(--blue-2)) !important;
    color: white !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: 0 2px 6px rgba(37,99,235,0.2);
    transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
div[role="dialog"] .stButton button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 14px rgba(37,99,235,0.3);
}
div[role="dialog"] .stButton button:active {
    transform: translateY(1px);
}
/* Forcer le texte blanc sur les boutons primaires du popup assistant */
div[role="dialog"] .stButton button[kind="primary"] {
    color: white !important;
}
            /* Alternative : tous les boutons du popup (même secondaires) */
div[role="dialog"] .stButton button {
    color: white !important;
}
            /* ── Force texte blanc sur TOUS les boutons du popup assistant ── */
div[role="dialog"] button,
div[role="dialog"] .stButton > button,
div[role="dialog"] .stButton > button p,
div[role="dialog"] .stButton > button span,
div[role="dialog"] .stButton > button div {
    color: white !important;
    -webkit-text-fill-color: white !important;
}

/* Bouton Fermer (secondaire) aussi en blanc */
div[role="dialog"] button[kind="secondary"],
div[role="dialog"] button[kind="secondary"] p {
    color: white !important;
    -webkit-text-fill-color: white !important;
}
            /* ── Textarea du popup assistant — contour bleu permanent ── */
div[role="dialog"] textarea,
div[role="dialog"] .stTextArea textarea,
div[role="dialog"] [data-testid="stTextArea"] textarea {
    border: 2px solid #2563eb !important;
    border-radius: 12px !important;
    background-color: #ffffff !important;
    color: #0f172a !important;
    box-shadow: none !important;
}

/* Au focus : bleu plus foncé + halo */
div[role="dialog"] textarea:focus,
div[role="dialog"] .stTextArea textarea:focus {
    border-color: #1e40af !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.2) !important;
    outline: none !important;
}

/* Placeholder visible */
div[role="dialog"] textarea::placeholder {
    color: #9ca3af !important;
    opacity: 1 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
defaults = {
    "history":            [],
    "feedback":           {},
    "pending_question":   "",
    "last_result":        None,
    "last_question":      "",
    "result_context":     "chatbot",
    "guided_form_key":    0,
    "form_question":      "",
    "active_tab":         0,
    "delete_fb_idx":      -1,
    "do_clear_form":      False,
    "popup_text":         "",
    "popup_counter":      0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Récupération question depuis le pop-up HTML
query_params = st.query_params
if "popup_q" in query_params:
    q_from_popup = query_params["popup_q"]
    if q_from_popup and q_from_popup != st.session_state.get("last_popup_q", ""):
        st.session_state.pending_question = q_from_popup
        st.session_state.result_context   = "chatbot"
        st.session_state.active_tab       = 0
        st.session_state.last_popup_q     = q_from_popup
        st.query_params.clear()
        st.rerun()


# ─────────────────────────────────────────────
# Chargement des prompts assistant
# ─────────────────────────────────────────────

PROMPTS_CONFIG_PATH = "config/assistant_prompts.json"

def load_assistant_prompts() -> dict:
    try:
        with open(PROMPTS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "greeting": "Que voulez-vous faire aujourd'hui ?",
            "categories": {
                "📈 Ventes": [
                    "Quel est mon chiffre d'affaires de ce mois ?",
                    "Quels sont mes meilleurs clients par CA en 2026 ?",
                ],
                "🧾 Factures": [
                    "Quelles factures ne sont pas encore payées ?",
                    "Factures entre 2026-01-01 et 2026-03-31",
                ],
                "📦 Stock": [
                    "Quels produits ont un stock inférieur à 5 ?",
                ],
            }
        }
    
# ═══════════════════════════════════════════════════════════════════════
# SUPPRESSION FEEDBACK — traitée AVANT tout rendu
# ═══════════════════════════════════════════════════════════════════════
FEEDBACK_FILE = "logs/feedback.jsonl"

def load_feedbacks() -> list:
    if not os.path.exists(FEEDBACK_FILE):
        return []
    items = []
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
    return items

def save_feedbacks(items: list):
    os.makedirs("logs", exist_ok=True)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def append_feedback(logs_id, question, rating, comment=""):
    os.makedirs("logs", exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "logs_id":   logs_id,
        "question":  question,
        "rating":    rating,
        "comment":   comment,
    }
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# Traitement suppression AVANT rendu
if st.session_state.delete_fb_idx >= 0:
    feedbacks_tmp = load_feedbacks()
    idx = st.session_state.delete_fb_idx
    if 0 <= idx < len(feedbacks_tmp):
        feedbacks_tmp.pop(idx)
        save_feedbacks(feedbacks_tmp)
    st.session_state.delete_fb_idx = -1
    st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════════════════

def call_hybrid_fallback(question: str) -> dict | None:
    """
    Appelle le moteur hybride LLM (port 8001).
    1. Génère le SQL via LLM
    2. Exécute le SQL via /execute (port 8000)
    Retourne un résultat formaté pour Streamlit, ou None si échec.
    """
    try:
        # ── Étape 1 : LLM génère le SQL ──
        r = requests.post(
            HYBRID_API_URL,
            json={"question": question, "force_llm": False},
            timeout=120
        )
        
        print(f"\n🔵 HYBRID API STATUS: {r.status_code}")
        print(f"🔵 HYBRID API BODY: {r.text[:500]}")
        
        if r.status_code != 200:
            return {
                "table": [],
                "summary": f"❌ Erreur API hybride (code {r.status_code})",
                "metadata": {
                    "status": "error",
                    "template": "llm",
                    "sql_query": "",
                    "duration_ms": 0,
                    "row_count": 0,
                    "logs_id": "",
                    "from_cache": False,
                    "suggestions": [],
                    "warning": "Le moteur hybride n'est pas accessible. Vérifiez le port 8001.",
                    "llm_mode": "llm_error",
                }
            }

        data = r.json()
        
        # Debug : afficher la réponse complète du LLM
        print(f"🔵 LLM RESPONSE: valid={data.get('valid')}, sql={data.get('sql', '')[:100]}")
        print(f"🔵 LLM ERROR: {data.get('error', 'none')}")

        # Échec LLM ou SQL invalide
        if not data.get("valid"):
            error_msg = data.get("error", "Validation SQL échouée")
            return {
                "table": [],
                "summary": f"❌ Requête LLM rejetée : {error_msg}",
                "metadata": {
                    "status": "error",
                    "template": data.get("intent", "llm"),
                    "sql_query": data.get("sql", ""),
                    "duration_ms": data.get("duration_ms", 0),
                    "row_count": 0,
                    "logs_id": data.get("request_id", ""),
                    "from_cache": False,
                    "suggestions": [],
                    "warning": f"Erreur LLM : {error_msg}",
                    "llm_mode": data.get("mode", "llm"),
                }
            }

        sql = data.get("sql", "").strip()
        
        if not sql:
            return {
                "table": [],
                "summary": "❌ Requête LLM rejetée : SQL vide généré par le LLM.",
                "metadata": {
                    "status": "error",
                    "template": data.get("intent", "llm"),
                    "sql_query": "",
                    "duration_ms": data.get("duration_ms", 0),
                    "row_count": 0,
                    "logs_id": data.get("request_id", ""),
                    "from_cache": False,
                    "suggestions": [],
                    "warning": "Le LLM n'a généré aucun SQL exploitable.",
                    "llm_mode": data.get("mode", "llm"),
                }
            }

        print(f"🟢 SQL GÉNÉRÉ PAR LLM: {sql[:200]}")

        # ── Étape 2 : Exécution via /execute (port 8000) ──
        try:
            exec_response = requests.post(
                EXECUTE_URL,
                json={"sql": sql},
                auth=(API_USER, API_PASS),
                timeout=60
            )
            
            print(f"🟢 EXECUTE STATUS: {exec_response.status_code}")
            print(f"🟢 EXECUTE BODY: {exec_response.text[:500]}")
            
            if exec_response.status_code == 200:
                exec_data = exec_response.json()
                row_count = exec_data.get("row_count", 0)
                return {
                    "table":   exec_data.get("rows", []),
                    "summary": f"{row_count} résultat(s) trouvé(s).",
                    "metadata": {
                        "status":      "success",
                        "template":    data.get("intent", "llm"),
                        "sql_query":   sql,
                        "duration_ms": data.get("duration_ms", 0),
                        "row_count":   row_count,
                        "logs_id":     data.get("request_id", ""),
                        "from_cache":  False,
                        "suggestions": [],
                        "warning":     data.get("warning", ""),
                        "llm_mode":    data.get("mode", "llm"),
                    }
                }
            else:
                # Erreur /execute
                try:
                    error_detail = exec_response.json().get("detail", exec_response.text[:200])
                except Exception:
                    error_detail = exec_response.text[:200]
                
                return {
                    "table": [],
                    "summary": f"❌ Erreur lors de l'exécution SQL.",
                    "metadata": {
                        "status": "error",
                        "template": data.get("intent", "llm"),
                        "sql_query": sql,
                        "duration_ms": data.get("duration_ms", 0),
                        "row_count": 0,
                        "logs_id": data.get("request_id", ""),
                        "from_cache": False,
                        "suggestions": [],
                        "warning": f"Erreur /execute ({exec_response.status_code}) : {error_detail}",
                        "llm_mode": data.get("mode", "llm"),
                    }
                }
                
        except Exception as ex:
            print(f"🔴 EXECUTE EXCEPTION: {ex}")
            return {
                "table": [],
                "summary": "❌ Connexion DB indisponible.",
                "metadata": {
                    "status": "error",
                    "template": data.get("intent", "llm"),
                    "sql_query": sql,
                    "duration_ms": data.get("duration_ms", 0),
                    "row_count": 0,
                    "logs_id": data.get("request_id", ""),
                    "from_cache": False,
                    "suggestions": [],
                    "warning": f"Erreur de connexion : {str(ex)}",
                    "llm_mode": data.get("mode", "llm"),
                }
            }

    except Exception as e:
        print(f"🔴 HYBRID FALLBACK EXCEPTION: {e}")
        return None

def call_api(question: str) -> dict:
    """
    Stratégie en 3 étapes :
    1. Port 8000 — templates V1/V2 (rapide, sans LLM)
       → success + données  : retour direct
       → rejected           : retour direct (sécurité)
       → clarification      : retour direct (ambiguïté)
       → tous les autres    : passe au LLM (port 8001)
    2. Port 8001 — moteur hybride LLM (fallback)
    3. Aucune solution trouvée
    """
    # ── Étape 1 : templates V1/V2 (port 8000) ──
    try:
        r = requests.post(
            API_URL,
            json={"question": question},
            auth=(API_USER, API_PASS),
            timeout=60  # augmenté de 30 à 60s
        )
        if r.status_code == 200:
            result = r.json()
            status = result.get("metadata", {}).get("status", "")
            table  = result.get("table", [])

            # ✅ Template trouvé avec données → retour direct
            if status == "success" and table:
                return result

            # 🔒 Injection SQL détectée → stop, pas de LLM
            if status == "rejected":
                return result

            # ❓ Question ambiguë → stop, demander clarification
            if status == "clarification_required":
                return result

            # Tous les autres cas tombent vers le LLM :
            # - success mais table vide (0 résultats)
            # - error (LLM interne échoue)
            # - status inconnu

    except requests.exceptions.ConnectionError:
        # Port 8000 inaccessible → essayer quand même le LLM
        pass

    except requests.exceptions.Timeout:
        # Port 8000 timeout → essayer le LLM
        pass

    except Exception:
        # Toute autre erreur réseau → essayer le LLM
        pass

    # ── Étape 2 : LLM fallback (port 8001) ──
    with st.spinner("🤖 Analyse en cours avec l'IA…"):
        hybrid_result = call_hybrid_fallback(question)

    if hybrid_result:
        return hybrid_result

    # ── Étape 3 : aucune solution ──
    return {
        "table":    [],
        "summary":  "Je ne peux pas répondre à cette question. Essayez de la reformuler.",
        "metadata": {"status": "error", "suggestions": []},
    }

def call_api_endpoint(endpoint: str, method: str = "GET") -> dict:
    try:
        fn = requests.get if method == "GET" else requests.post
        r  = fn(f"http://localhost:8000{endpoint}", auth=(API_USER, API_PASS), timeout=10)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════════════
# TRAITEMENT QUESTION EN ATTENTE
# ═══════════════════════════════════════════════════════════════════════
if st.session_state.pending_question:
    q = st.session_state.pending_question
    st.session_state.pending_question = ""
    st.session_state.last_question    = q
    st.session_state.form_question    = q
    with st.spinner(f"Analyse : « {q} »…"):
        result = call_api(q)
    st.session_state.last_result = result
    meta = result.get("metadata", {})
    st.session_state.history.insert(0, {
        "question":    q,
        "summary":     result.get("summary", ""),
        "status":      meta.get("status", ""),
        "template":    meta.get("template", ""),
        "row_count":   meta.get("row_count", 0),
        "duration_ms": meta.get("duration_ms", 0),
        "logs_id":     meta.get("logs_id", ""),
        "timestamp":   datetime.now().strftime("%H:%M:%S"),
        "llm_mode":    meta.get("llm_mode", ""),
    })

# Nettoyage différé du champ de saisie
if st.session_state.do_clear_form:
    st.session_state.form_question = ""
    st.session_state.do_clear_form = False

# ─────────────────────────────────────────────
# Helpers export
# ─────────────────────────────────────────────

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Résultats")
    return buf.getvalue()


def auto_chart(df: pd.DataFrame, template: str):
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use("Agg")
    fig = None
    try:
        if template == "get_total_ventes_mois" and "CA_HT" in df.columns:
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar(df["mois"].astype(str), df["CA_HT"], color="#4CAF50", alpha=0.85)
            ax.set_ylabel("CA HT")
            ax.set_title("Chiffre d'affaires HT")
            ax.tick_params(axis="x", rotation=30)
            fig.tight_layout()
        elif template == "get_clients_multiple_commandes" and "nb_commandes" in df.columns:
            top = df.nlargest(10, "nb_commandes")
            fig, ax = plt.subplots(figsize=(6, max(3, len(top) * 0.4)))
            ax.barh(top["client_nom"].astype(str), top["nb_commandes"], color="#2196F3", alpha=0.85)
            ax.set_xlabel("Nb commandes")
            ax.set_title("Top clients")
            fig.tight_layout()
        elif template == "get_produits_stock_faible" and "stock_disponible" in df.columns:
            top = df.nsmallest(15, "stock_disponible")
            colors = ["#e53935" if s == 0 else "#FF9800" if s < 3 else "#4CAF50"
                      for s in top["stock_disponible"]]
            fig, ax = plt.subplots(figsize=(6, max(3, len(top) * 0.35)))
            ax.barh(top["produit_nom"].astype(str), top["stock_disponible"],
                    color=colors, alpha=0.85)
            ax.set_xlabel("Stock")
            ax.set_title("Produits à stock faible")
            fig.tight_layout()
        elif template in ("get_factures_non_payees", "get_factures_partiellement_payees") \
                and "montant_paye" in df.columns and "montant_restant" in df.columns:
            tp = float(df["montant_paye"].sum())
            tr = float(df["montant_restant"].sum())
            if tp + tr > 0:
                fig, ax = plt.subplots(figsize=(5, 3))
                ax.pie([tp, tr], labels=["Payé", "Restant"],
                       colors=["#4CAF50", "#e53935"], autopct="%1.1f%%", startangle=90)
                ax.set_title("Répartition paiements")
                fig.tight_layout()
        elif template == "get_factures_between" \
                and "date_facture" in df.columns and "total_ttc" in df.columns:
            df2 = df.copy()
            df2["date_facture"] = pd.to_datetime(df2["date_facture"], errors="coerce")
            df2 = df2.dropna(subset=["date_facture"]).sort_values("date_facture")
            if len(df2) >= 2:
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.plot(df2["date_facture"], df2["total_ttc"].astype(float),
                        color="#9C27B0", marker="o", markersize=3, linewidth=1.5)
                ax.set_ylabel("Total TTC")
                ax.set_title("Factures sur la période")
                ax.tick_params(axis="x", rotation=30)
                fig.tight_layout()
        # ── Graphique automatique pour résultats LLM ──
        elif "total_ttc" in df.columns and "client" in df.columns:
            top = df.nlargest(10, "total_ttc") if len(df) > 10 else df
            fig, ax = plt.subplots(figsize=(6, max(3, len(top) * 0.4)))
            ax.barh(top["client"].astype(str), top["total_ttc"].astype(float),
                    color="#9C27B0", alpha=0.85)
            ax.set_xlabel("Total TTC")
            ax.set_title("CA par client")
            fig.tight_layout()
        elif "total_ttc" in df.columns and len(df) > 1:
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar(range(len(df)), df["total_ttc"].astype(float),
                   color="#2196F3", alpha=0.85)
            ax.set_title("Résultats")
            fig.tight_layout()
    except Exception:
        fig = None
    return fig


# ═══════════════════════════════════════════════════════════════════════
# États prêts à l'emploi
# ═══════════════════════════════════════════════════════════════════════
import json as _json

ETATS_CONFIG_PATH = "config/etats_standards.json"

def get_etats_standards() -> list:
    today           = date.today()
    first_day_month = date(today.year, today.month, 1)
    first_day_year  = date(today.year, 1, 1)
    mois_courant    = month_name(str(today.month).zfill(2))

    variables = {
        "today":           str(today),
        "first_day_month": str(first_day_month),
        "first_day_year":  str(first_day_year),
        "mois_courant":    mois_courant,
        "annee":           str(today.year),
    }

    try:
        with open(ETATS_CONFIG_PATH, "r", encoding="utf-8") as f:
            etats_raw = _json.load(f)
        etats = []
        for e in etats_raw:
            question = e["question_template"]
            for key, val in variables.items():
                question = question.replace(f"{{{key}}}", val)
            etats.append({"label": e["label"], "question": question})
        return etats
    except (FileNotFoundError, KeyError, _json.JSONDecodeError):
        return [
            {"label": "• Factures non payées",          "question": "factures non payées"},
            {"label": "• Produits stock faible (< 10)",  "question": "produits avec stock inférieur à 10"},
            {"label": "• Top clients (multi-commandes)", "question": "clients avec plus de 2 commandes"},
        ]


# ═══════════════════════════════════════════════════════════════════════
# render_result
# ═══════════════════════════════════════════════════════════════════════

# ── Mapping : colonne id → URL Dolibarr ─────────────────────────────────────
# Détecté automatiquement selon les colonnes présentes dans le DataFrame.
DOLIBARR_LINKS = {
    # (colonne_id,   colonne_label,   url_template)
    "facture": (
        "id", "facture_ref",
        DOLIBARR_BASE_URL + "/compta/facture/card.php?id={id}&save_lastsearch_values=1"
    ),
    "client": (
        "id", "client",
        DOLIBARR_BASE_URL + "/societe/card.php?socid={id}&save_lastsearch_values=1"
    ),
    "client_nom": (
        "id", "client_nom",
        DOLIBARR_BASE_URL + "/societe/card.php?socid={id}&save_lastsearch_values=1"
    ),
    "produit": (
        "id", "produit_nom",
        DOLIBARR_BASE_URL + "/product/card.php?id={id}&save_lastsearch_values=1"
    ),
    "commande_client": (
        "id", "commande_ref",
        DOLIBARR_BASE_URL + "/commande/card.php?id={id}&save_lastsearch_values=1"
    ),
    "commande_fournisseur": (
        "id", "commande_ref",
        DOLIBARR_BASE_URL + "/fourn/commande/card.php?id={id}&save_lastsearch_values=1"
    ),
}
 
def detect_entity_type(df: pd.DataFrame) -> str | None:
    """
    Détecte automatiquement le type d'entité à partir des colonnes du DataFrame.
    Retourne la clé de DOLIBARR_LINKS ou None si non détectable.
    """
    cols = set(df.columns)
    if "id" not in cols:
        return None
    if "facture_ref" in cols:
        return "facture"
    if "client_nom" in cols:
        return "client_nom"
    if "client" in cols and "nb_factures" in cols:
        return "client"       # top clients CA
    if "client" in cols and "nb_commandes" not in cols:
        return "client"       # liste clients simple
    if "produit_nom" in cols:
        return "produit"
    if "commande_ref" in cols:
        # distinction commande client vs fournisseur par nom de colonne supplémentaire
        return "commande_fournisseur" if "fournisseur" in cols else "commande_client"
    return None
 
 
def render_dataframe_with_links(df: pd.DataFrame, entity_type: str) -> None:
    """
    Affiche un DataFrame HTML avec la colonne label transformée en lien cliquable.
    La colonne 'id' est masquée dans l'affichage final.
    """
    id_col, label_col, url_tpl = DOLIBARR_LINKS[entity_type]
 
    if id_col not in df.columns or label_col not in df.columns:
        st.dataframe(df, use_container_width=True)
        return
 
    df_display = df.copy()
 
    # Générer les liens HTML pour la colonne label
    def make_link(row):
        try:
            doc_id = int(row[id_col])
        except (ValueError, TypeError):
            return str(row[label_col])
        url = url_tpl.replace("{id}", str(doc_id))
        label = html.escape(str(row[label_col]))
        return (
            f'<a href="{url}" target="_blank" '
            f'style="color:#1565c0;text-decoration:underline;font-weight:600;" '
            f'title="Ouvrir dans Dolibarr">{label} ↗</a>'
        )
 
    df_display[label_col] = df_display.apply(make_link, axis=1)
 
    # ── Réorganiser les colonnes sans masquer l'ID ──
    cols = list(df_display.columns)

    # Mettre l'id au début pour meilleure lisibilité
    if id_col in cols:
        cols.remove(id_col)
        cols.insert(0, id_col)

    df_display = df_display[cols]

    # Rendu HTML
    table_html = df_display.to_html(
        escape=False,
        index=False,
        classes="dolibarr-table",
        border=0
    )
 
    st.markdown("""
    <style>
    .dolibarr-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
        font-family: sans-serif;
    }
    .dolibarr-table th {
        background: #f1f3f5;
        color: #111;
        padding: 8px 12px;
        text-align: left;
        border-bottom: 2px solid #dee2e6;
        position: sticky;
        top: 0;
        font-weight: 600;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .dolibarr-table td {
        padding: 7px 12px;
        border-bottom: 1px solid #e5e7eb;
        color: #222;
        vertical-align: middle;
    }
    .dolibarr-table tr:nth-child(even) td { background: #f9fafb; }
    .dolibarr-table tr:hover td { background: #ede9fe; }
    .dolibarr-table-wrapper {
        max-height: 400px;
        overflow-y: auto;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        scrollbar-width: thin;
        scrollbar-color: #cbd5e0 transparent;
    }
    .dolibarr-table-wrapper::-webkit-scrollbar { width: 5px; }
    .dolibarr-table-wrapper::-webkit-scrollbar-thumb {
        background: #cbd5e0; border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
 
    st.markdown(
        f'<div class="dolibarr-table-wrapper">{table_html}</div>',
        unsafe_allow_html=True
    )
 
    # Légende
    st.markdown(f'<div style="font-size:0.8rem; color:#666;"><i class="fa-regular fa-circle-info"></i> Cliquez sur un lien pour ouvrir la fiche dans Dolibarr ({DOLIBARR_BASE_URL})</div>', unsafe_allow_html=True)

# ── 2. Remplacer la fonction render_result complète ─────────────────────────
 
def render_result(result: dict, question: str, context: str = "main"):
    status      = result.get("metadata", {}).get("status", "")
    summary     = result.get("summary", "")
    table_data  = result.get("table", [])
    meta        = result.get("metadata", {})
    sql_query   = meta.get("sql_query", "")
    template    = meta.get("template", "")
    logs_id     = meta.get("logs_id", "") or "noid"
    from_cache  = meta.get("from_cache", False)
    suggestions = meta.get("suggestions", [])
    warning     = meta.get("warning", "")
    llm_mode    = meta.get("llm_mode", "")
    pfx         = f"{context}_{logs_id}"
 
    if status == "rejected":
        st.markdown(
            f'<div class="rejected-box"><i class="fa-solid fa-ban"></i> <strong>Requête rejetée</strong><br>'
            f'{html.escape(summary)}</div>', unsafe_allow_html=True)
        return
    if status == "clarification_required":
        st.markdown(
            f'<div class="clarification-box"><i class="fa-solid fa-circle-question"></i> <strong>Précision nécessaire</strong><br>'
            f'{html.escape(summary)}</div>', unsafe_allow_html=True)
        return
    if status == "error":
        st.error(f"⚠️ {summary}")
        return
 
    duration  = meta.get("duration_ms", 0)
    row_count = meta.get("row_count", 0)
    cache_tag = ' · cache <i class="fa-solid fa-bolt"></i>' if from_cache else ""

 
    is_llm = bool(llm_mode) or str(template).startswith("llm:")
    if is_llm:
        st.markdown(
    '<div class="llm-badge"><i class="fa-solid fa-robot" style="margin-right:6px;"></i><strong>Réponse générée par IA</strong> — SQL validé et exécuté de manière sécurisée</div>',
    unsafe_allow_html=True
)
 
    chip_template = (
f'<span class="meta-chip-llm"><i class="fa-solid fa-robot"></i> {html.escape(str(template))}</span>'
        if is_llm else
f'<span class="meta-chip"><i class="fa-regular fa-note-sticky"></i> {html.escape(str(template))}</span>'
    )
 
    st.markdown(f"""
<div class="result-box">
    <i class="fa-regular fa-circle-check" style="color:#4CAF50;"></i> <strong>{html.escape(summary)}</strong><br>
    {chip_template}
    <span class="meta-chip"><i class="fa-solid fa-table-list"></i> {row_count} ligne(s)</span>
    <span class="meta-chip"><i class="fa-regular fa-clock"></i> {duration:.0f} ms{cache_tag}</span>
    <span class="meta-chip" style="background:#eff4ff;color:#1f4fb0;border:1px solid #bfdbfe;"><i class="fa-solid fa-key"></i> {html.escape(str(logs_id))[:8]}...</span>
</div>
""", unsafe_allow_html=True)
 
    if warning:
        st.warning(f"⚠️ {warning}")
 
    if table_data:
        df = pd.DataFrame(table_data)
 
        st.markdown("#### Résultats")
 
        # ── Détection entité + affichage avec liens ──────────────────────────
        entity_type = detect_entity_type(df)
 
        if entity_type and entity_type in DOLIBARR_LINKS:
            render_dataframe_with_links(df, entity_type)
        else:
            # Affichage standard si pas de liens détectés
            st.dataframe(df, use_container_width=True, height=min(400, 50 + 35 * len(df)))
 
        # ── Export ────────────────────────────────────────────────────────────
        st.markdown("#### Exporter")
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        fig = auto_chart(df, template)
 
        # Pour l'export CSV/Excel/PDF on garde le df complet (avec id)
        col_csv, col_xlsx, col_pdf, _ = st.columns([1, 1, 1, 2])
        with col_csv:
            st.download_button("⬇ CSV", data=df_to_csv_bytes(df),
                               file_name=f"{template}_{ts}.csv", mime="text/csv",
                               use_container_width=True, key=f"csv_{pfx}")
        with col_xlsx:
            try:
                st.download_button("⬇ Excel", data=df_to_excel_bytes(df),
                                   file_name=f"{template}_{ts}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True, key=f"xlsx_{pfx}")
            except Exception:
                st.caption("pip install openpyxl")
        with col_pdf:
            if generate_pdf_report is None:
                st.caption("pdf_export.py introuvable")
            else:
                try:
                    pdf_bytes = generate_pdf_report(
                        question=question,
                        summary=summary,
                        template=str(template),
                        duration_ms=float(duration),
                        row_count=int(row_count),
                        logs_id=str(logs_id),
                        table_data=table_data,
                        chart_fig=fig,
                        from_cache=from_cache,
                        sql_query=str(sql_query),
                    )
                    st.download_button(
                        "⬇ PDF",
                        data=pdf_bytes,
                        file_name=f"{template}_{ts}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"pdf_{pfx}",
                    )
                except Exception as e:
                    st.caption(f"PDF indisponible : {e}")
 
        if sql_query:
            with st.expander("⌘ Voir la requête SQL générée"):                
                st.code(sql_query, language="sql")
 
    # ── Suggestions ───────────────────────────────────────────────────────────
    if suggestions:
        st.markdown("---")
        st.markdown(
    '<div class="suggestion-box"><span style="color:#111;"><i class="fa-regular fa-lightbulb" style="color:#2563eb;margin-right:6px;"></i><strong>Que souhaitez-vous faire ensuite ?</strong></span></div>',
    unsafe_allow_html=True)
        sug_cols = st.columns(min(len(suggestions), 2))
        for i, s in enumerate(suggestions):
            if sug_cols[i % 2].button(f"→ {s}", key=f"sug_{pfx}_{i}", use_container_width=True):
                st.session_state.pending_question = s
                st.session_state.result_context   = context
                if context == "guided":
                    st.session_state.guided_form_key += 1
                st.rerun()
 
    # ── Feedback ──────────────────────────────────────────────────────────────
    if logs_id == "noid":
        return
 
    fb_done_key = f"fb_done_{pfx}"
    st.markdown("---")
 
    if st.session_state.get(fb_done_key, False):
        return
 
    st.markdown('<h4><i class="fa-regular fa-star" style="color:#2563eb;margin-right:6px;"></i>Évaluer cette réponse</h4>', unsafe_allow_html=True)
    fcol1, fcol2, fcol3 = st.columns([1, 1, 4])
    comment_key = f"comment_{pfx}"
    comment = st.text_input(
        "Commentaire",
        key=comment_key,
        placeholder="Écrivez un commentaire avant de valider...",
        label_visibility="collapsed"
    )
    if comment and not st.session_state.get(f"clicked_{pfx}", False):
        st.warning("⚠️ Veuillez choisir ✔ (Correcte) ou ✘ (Incorrecte) pour valider votre commentaire.")
    with fcol1:
        if st.button("✔ Correcte", key=f"ok_{pfx}", use_container_width=True):
            if not comment.strip():
                st.error("❌ Veuillez ajouter un commentaire avant de valider.")
            else:
                append_feedback(logs_id, question, "positive", comment)
                st.session_state[fb_done_key] = True
                st.rerun()
    with fcol2:
        if st.button("✘ Incorrecte", key=f"ko_{pfx}", use_container_width=True):
            if not comment.strip():
                st.error("❌ Veuillez ajouter un commentaire avant de valider.")
            else:
                append_feedback(logs_id, question, "negative", comment)
                st.session_state[fb_done_key] = True
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# POP-UP ASSISTANT — s'ouvre UNE SEULE FOIS au démarrage
# ═══════════════════════════════════════════════════════════════════════

assistant_prompts = load_assistant_prompts()


@st.dialog("💬 Assistant ZAI - Que voulez-vous faire ?", width="large")
def show_assistant_popup():
    prompts_by_cat = assistant_prompts.get("categories", {})

    st.markdown(
        "<p style='color:#6b7280;font-size:0.88rem;margin-bottom:0.5rem;'>"
        "Cliquez sur un exemple pour le copier dans la zone de texte, "
        "modifiez-le si besoin, puis cliquez sur <strong>Envoyer</strong>.</p>",
        unsafe_allow_html=True
    )

    for cat, prompts in prompts_by_cat.items():
        st.markdown(
    f"<p style='font-size:0.75rem;font-weight:600;color:#6366f1;"
    f"text-transform:uppercase;letter-spacing:0.06em;"
    f"margin:0.8rem 0 0.25rem 0'>{cat}</p>",
    unsafe_allow_html=True
)
        nb_cols = min(len(prompts), 3)
        cols = st.columns(nb_cols)
        for i, p in enumerate(prompts):
            with cols[i % nb_cols]:
                if st.button(p, key=f"popup_pick_{cat}_{i}", use_container_width=True, type="primary"):
                    st.session_state.popup_text    = p
                    st.session_state.popup_counter += 1
                    st.rerun()

    st.markdown("---")
    st.markdown(
    "<p style='font-size:0.82rem;color:#374151;margin-bottom:0.3rem;'>"
    "<i class='fa-regular fa-pen-to-square'></i> <strong>Modifiez votre question si besoin :</strong></p>",
    unsafe_allow_html=True
)

    textarea_key = f"popup_textarea_{st.session_state.popup_counter}"
    q_popup = st.text_area(
        label="question_popup",
        value=st.session_state.popup_text,
        placeholder="Cliquez sur un exemple ci-dessus ou écrivez directement ici…",
        height=90,
        label_visibility="collapsed",
        key=textarea_key
    )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    col_send, col_close = st.columns([3, 1])

    with col_send:
        valeur = st.session_state.get(textarea_key, "").strip()
        if st.button(
            "➤ Envoyer",
            type="primary",
            use_container_width=True,
            key="popup_send_btn",
            disabled=not valeur
        ):
            st.session_state.pending_question  = valeur
            st.session_state.result_context    = "chatbot"
            st.session_state.active_tab        = 0
            st.session_state.popup_text        = ""
            st.session_state.popup_counter     = 0
            st.session_state.popup_should_open = False  # ← ferme définitivement
            st.rerun()

    with col_close:
        if st.button("✕ Fermer", use_container_width=True, key="popup_close_btn", type="primary"):
            st.session_state.popup_text        = ""
            st.session_state.popup_counter     = 0
            st.session_state.popup_should_open = False  # ← ferme définitivement
            st.rerun()


# ── Initialisation UNE SEULE FOIS par session ──
if "popup_should_open" not in st.session_state:
    st.session_state.popup_should_open = False

# ── Ouvrir le popup seulement si demandé ──
if st.session_state.popup_should_open:
    show_assistant_popup()
    # Ne pas remettre à False ici — c'est le bouton Fermer/Envoyer qui le fait

# ── Bouton de réouverture ──
col_reopen = st.columns([10, 1])[1]
with col_reopen:
    if st.button("💬", key="btn_reopen_popup", help="Ouvrir l'assistant"):
        st.session_state.popup_should_open = True
        st.rerun()

# ─────────────────────────────────────────────
# Layout — onglets (radio horizontal)
# ─────────────────────────────────────────────
tab_labels = ["Chatbot", "Assistant guidé", "Analyse prédictive"]

selected_tab = st.radio(
    "",
    tab_labels,
    horizontal=True,
    index=st.session_state.active_tab
)
st.session_state.active_tab = tab_labels.index(selected_tab)

# ═══════════════════════════════════════════
# Onglet 1 — Chatbot
# ═══════════════════════════════════════════
if selected_tab == "Chatbot":
    col_main, col_history = st.columns([3, 1], gap="large")

    with col_main:
        st.markdown('<div class="chat-title"><i class="fa-regular fa-comments"></i> Chatbot ZAI Informatique</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="chat-subtitle"><i class="fa-solid fa-database" style="color:#2563eb;margin-right:6px;"></i>Posez vos questions en langage naturel sur vos données Dolibarr</div>',
            unsafe_allow_html=True)

        with st.form(key="question_form", clear_on_submit=False):
            q_input = st.text_input(
                "Votre question",
                placeholder="Ex: Donne-moi les factures non payées",
                label_visibility="collapsed",
                key="form_question"
            )
            submitted = st.form_submit_button("Envoyer", use_container_width=True)

        if submitted and q_input.strip():
            st.session_state.pending_question = q_input.strip()
            st.session_state.result_context   = "chatbot"
            st.session_state.active_tab       = 0
            st.rerun()

        st.markdown('<p style="font-weight:600;"><i class="fa-solid fa-bolt" style="color:#2563eb;margin-right:6px;"></i>États prêts à l\'emploi :</p>', unsafe_allow_html=True)
        etats = get_etats_standards()
        etat_labels = [e["label"] for e in etats]
        col_combo, col_btn = st.columns([4, 1])
        with col_combo:
            etat_selected = st.selectbox(
                "État standard",
                options=etat_labels,
                index=0,
                label_visibility="collapsed",
                key="combo_etat_standard",
            )
        with col_btn:
            if st.button("▶ Lancer cet état", use_container_width=True, key="btn_lancer_etat"):
                question_etat = next(
                    e["question"] for e in etats if e["label"] == etat_selected
                )
                st.session_state.pending_question = question_etat
                st.session_state.result_context   = "chatbot"
                st.session_state.active_tab       = 0
                st.rerun()

        st.markdown('<p style="font-weight:600;"><i class="fa-regular fa-lightbulb" style="color:#2563eb;margin-right:6px;"></i>Exemples de questions :</p>', unsafe_allow_html=True)

# Conteneur personnalisé pour les boutons exemples
        st.markdown('<div class="example-buttons-wrapper">', unsafe_allow_html=True)
        examples = [
    "Factures entre 2026-01-01 et 2026-02-28",
    "Liste des factures non payées",
    "Produits avec stock inférieur à 5",
    "Clients avec plus de 2 commandes",
    "Chiffre d'affaires de janvier 2026",
]
        ex_cols = st.columns(5)  # nombre exact d'exemples
        for i, ex in enumerate(examples):
            if ex_cols[i].button(ex, key=f"ex_chat_{i}", use_container_width=True):
                st.session_state.pending_question = ex
                st.session_state.result_context   = "chatbot"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        if (st.session_state.last_result is not None
                and st.session_state.result_context == "chatbot"):
            render_result(st.session_state.last_result,
                          st.session_state.last_question,
                          context="chatbot")

    with col_history:
        st.markdown('<h3 style="font-size:1.1rem;font-weight:700;"><i class="fa-regular fa-clock" style="color:#2563eb;margin-right:8px;"></i>Historique</h3>', unsafe_allow_html=True)
        if not st.session_state.history:
            st.markdown('<div style="color:#aaa;font-size:0.85rem;">Aucune question posée</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:0.78rem;color:#999;">'
                        f'{len(st.session_state.history)} question(s)</div>',
                        unsafe_allow_html=True)
            items_html = ""
            for item in st.session_state.history:
                icon = {
    "rejected":               '<i class="fa-solid fa-lock" style="color:#dc2626;"></i>',
    "clarification_required": '<i class="fa-solid fa-circle-question" style="color:#d97706;"></i>',
    "error":                  '<i class="fa-solid fa-triangle-exclamation" style="color:#d97706;"></i>',
}.get(item["status"], '<i class="fa-solid fa-circle-check" style="color:#16a34a;"></i>')
                llm_icon = ' <i class="fa-solid fa-robot" style="color:#7c3aed;font-size:0.8rem;"></i>' if item.get("llm_mode") else ""
                q = html.escape(item["question"])
                s = html.escape(item["summary"])
                items_html += (
                    f'<div class="history-item">'
                    f'{icon}{llm_icon} <strong>{item["timestamp"]}</strong><br>'
                    f'{q[:55]}{"..." if len(q) > 55 else ""}<br>'
                    f'<span style="color:#999;font-size:0.78rem;">'
                    f'{s[:60]}{"..." if len(s) > 60 else ""}</span>'
                    f'</div>'
                )
            st.markdown(f'<div class="history-wrapper">{items_html}</div>',
                        unsafe_allow_html=True)
            if st.button("🗑 Effacer l'historique", use_container_width=True):
                st.session_state.history       = []
                st.session_state.last_result   = None
                st.session_state.last_question = ""
                st.session_state.do_clear_form = True
                st.rerun()

# ═══════════════════════════════════════════
# Onglet 2 — Assistant guidé
# ═══════════════════════════════════════════
elif selected_tab == "Assistant guidé":
    st.markdown('<h2><i class="fa-solid fa-compass"></i> Assistant guidé</h2>', unsafe_allow_html=True)
    st.caption("Construisez votre requête sans taper de texte")

    form_key = f"guided_form_{st.session_state.guided_form_key}"

    with st.form(form_key):
        col1, col2 = st.columns(2)
        with col1:
            data_type = st.selectbox("Type de données",
                                     ["Factures", "Paiements", "Clients", "Produits"])
        with col2:
            analysis_type = st.selectbox("Type d'analyse",
                                         ["Total", "Non payées", "Partiellement payées",
                                          "Par client", "Stock faible", "Multiples commandes"])
        col3, col4 = st.columns(2)
        with col3:
            start_date = st.date_input("Du", value=None)
        with col4:
            end_date = st.date_input("Au", value=None)
        quick = st.selectbox("Période rapide (optionnel)",
                             ["-- Aucun --", "Ce mois", "Année en cours", "Tout 2026"])
        submit_guided = st.form_submit_button("▶ Lancer l'analyse", use_container_width=True)

    if submit_guided:
        today = date.today()
        if quick == "Ce mois":
            start_date = date(today.year, today.month, 1)
            end_date   = today
        elif quick == "Année en cours":
            start_date = date(today.year, 1, 1)
            end_date   = today
        elif quick == "Tout 2026":
            start_date = date(2026, 1, 1)
            end_date   = date(2026, 12, 31)

        q_parts = {
            ("Factures", "Non payées"):           "factures non payées",
            ("Factures", "Partiellement payées"): "factures partiellement payées",
            ("Factures", "Par client"):           "donne moi les factures",
            ("Factures", "Total"):                f"factures entre {start_date} et {end_date}",
            ("Clients",  "Multiples commandes"):  "clients avec plus de 2 commandes",
            ("Produits", "Stock faible"):         "produits avec stock inférieur à 5",
        }
        question = q_parts.get(
            (data_type, analysis_type),
            f"factures entre {start_date} et {end_date}"
            if start_date and end_date else "factures non payées"
        )
        st.session_state.pending_question = question
        st.session_state.result_context   = "guided"
        st.session_state.guided_form_key += 1
        st.session_state.active_tab       = 1
        st.rerun()

    if (st.session_state.last_result is not None
            and st.session_state.result_context == "guided"):
        st.markdown("---")
        render_result(st.session_state.last_result,
                      st.session_state.last_question,
                      context="guided")

# ═══════════════════════════════════════════
# Onglet 3 — Analyse prédictive (VRAIE PRÉDICTION)
# ═══════════════════════════════════════════
elif selected_tab == "Analyse prédictive":
    st.markdown('<h3><i class="fa-solid fa-wand-magic-sparkles" style="color:inherit; margin-right:8px;"></i>Analyse prédictive</h3>', unsafe_allow_html=True)
    st.caption("Prévisions basées sur les données historiques (Machine Learning)")
    
    # Importer les fonctions de prédiction
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from utils.predictive import predict_ca_mensuel, predict_stock_rupture, predict_fidelite_clients
    pred_type = st.selectbox(
        "Type d'analyse",
        ["• CA mensuel - prévision", "• Stock - alerte rupture", "• Clients - fidélité prévue"]
    )
    
    if st.button("▶ Lancer la prédiction", type="primary", key="btn_predict_real"):
        with st.spinner("⏳ Analyse et prédiction en cours..."):
            
            # ─── PRÉDICTION CA MENSUEL ─────────────────────────────────────────
            if "CA mensuel" in pred_type:
                st.markdown("#### Prédiction du Chiffre d'Affaires")
    
    # Une seule requête pour récupérer TOUS les mois
                with st.spinner("📜 Récupération des données historiques..."):
                    result = call_api("évolution chiffre d affaires mensuel")
                    table = result.get("table", [])
    
                months_data = []
                if table:
                    for row in table:
                        if isinstance(row, dict):
                            annee = row.get("annee")
                            mois = row.get("mois")
                            ca = row.get("chiffre_affaires")
                
                            if annee and mois and ca and float(ca) > 0:
                                months_data.append({
                        "mois": f"{annee}-{str(mois).zfill(2)}",
                        "CA_HT": float(ca)
                    })
        
        # Trier par date
                    months_data.sort(key=lambda x: x["mois"])
        
                    st.info(f"➤ {len(months_data)} mois de données historiques récupérées")
                    df_hist = pd.DataFrame(months_data)
                    st.dataframe(df_hist, use_container_width=True, hide_index=True)
    
                if len(months_data) >= 3:
        # Faire la prédiction
                    prediction = predict_ca_mensuel(months_data, months_ahead=1)
        
                    if "error" in prediction:
                        st.error(prediction["error"])
                    else:
            # Afficher les prédictions
                        st.markdown("**Prédictions (prochain mois)**")
                        df_pred = pd.DataFrame(prediction["predictions"])
                        st.dataframe(df_pred, use_container_width=True, hide_index=True)
            
            # Métriques
                        # Dans l'affichage des métriques
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Qualité du modèle (R²)", f"{prediction['model_score']:.2f}")
                        col2.metric("Tendance", "📈 Hausse" if prediction["tendance"] == "hausse" else "📉 Baisse")

                        dernier_ca = months_data[-1]["CA_HT"]
                        ca_prevu = prediction["predictions"][0]["CA_HT_predit"]
                        variation = ((ca_prevu - dernier_ca) / dernier_ca * 100) if dernier_ca > 0 else 0

# Ajouter un avertissement si la variation est extrême
                        if abs(variation) > 50:
                            st.warning(f"⚠️ Variation extrême de {variation:+.1f}% détectée. La prédiction peut être peu fiable en raison de données volatiles.")

                        col3.metric("Prévision mois prochain", f"{ca_prevu:,.0f} TND", delta=f"{variation:+.1f}%")
            # Graphique
                        fig, ax = plt.subplots(figsize=(10, 4))
                        hist_months = [d["mois"] for d in months_data]
                        hist_values = [d["CA_HT"] for d in months_data]
                        pred_months = [d["mois"] for d in prediction["predictions"]]
                        pred_values = [d["CA_HT_predit"] for d in prediction["predictions"]]
            
                        ax.plot(hist_months, hist_values, 'b-o', label="Historique", linewidth=2, markersize=6)
                        ax.plot(pred_months, pred_values, 'r--o', label="Prédiction", linewidth=2, markersize=6)
                        ax.axvline(x=len(hist_months)-0.5, color='gray', linestyle='--', alpha=0.5)
                        ax.set_ylabel("CA HT (TND)")
                        ax.set_xlabel("Mois")
                        ax.set_title("Évolution et prédiction du Chiffre d'Affaires")
                        ax.legend()
                        ax.grid(True, alpha=0.3)
                        plt.xticks(rotation=45)
                        fig.tight_layout()
                        st.pyplot(fig)
                        plt.close(fig)
                else:
                    st.warning(f"Données insuffisantes pour la prédiction ({len(months_data)}/3 mois minimum).")              
            # ─── PRÉDICTION STOCK ─────────────────────────────────────────────
            elif "Stock" in pred_type:
                st.markdown("#### Prédiction des ruptures de stock")
                
                r = call_api("produits avec stock inférieur à 20")
                products_data = r.get("table", [])
                
                if products_data:
                    # Convertir les tuples en dictionnaires
                    formatted_products = []
                    for p in products_data:
                        if isinstance(p, (tuple, list)):
                            # Adapter l'index selon votre requête SQL
                            # Exemple: SELECT p.ref, p.label, p.stock
                            formatted_products.append({
    "produit_nom": p[1] if len(p) > 1 else "",  # ← "produit_nom" pas "produit_ref"
    "stock_actuel": float(p[2]) if len(p) > 2 and p[2] is not None else 0  # ← "stock_actuel"
})
                        else:
                            formatted_products.append(p)
                    
                    alerts = predict_stock_rupture(formatted_products, seuil=10)
                    
                    if alerts:
                        st.warning(f"⚠️ {len(alerts)} produit(s) en risque de rupture")
                        df_alerts = pd.DataFrame(alerts)
                        st.dataframe(df_alerts, use_container_width=True, hide_index=True)
                        
                        # Niveaux de risque
                        critique = sum(1 for a in alerts if a.get("niveau_risque") == "critique")
                        eleve = sum(1 for a in alerts if a.get("niveau_risque") == "elevé")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Risque critique", critique, delta="< 7 jours")
                        col2.metric("Risque élevé", eleve, delta="< 30 jours")
                        col3.metric("Stock faible", len(alerts) - critique - eleve, delta="< seuil")
                    else:
                        st.success("✅ Aucun produit en risque de rupture détecté")
                else:
                    st.info("Aucun produit avec stock faible détecté")
            
            # ─── PRÉDICTION FIDÉLITÉ CLIENTS ───────────────────────────────────
            elif "fidélité" in pred_type:
                st.markdown("#### Prédiction de fidélité clients")
                
                r = call_api("clients avec plus de 2 commandes")
                clients_data = r.get("table", [])
                
                if clients_data:
                    formatted_clients = []
                    for c in clients_data:
                        if isinstance(c, (tuple, list)):
                            formatted_clients.append({
                                "nom": c[0] if len(c) > 0 else "",
                                "nombre_commandes": int(c[1]) if len(c) > 1 and c[1] is not None else 0
                            })
                        else:
                            formatted_clients.append(c)
                    
                    predictions = predict_fidelite_clients(formatted_clients)
                    
                    st.markdown("**Top clients par score de fidélité**")
                    df_fidelite = pd.DataFrame(predictions[:10])
                    st.dataframe(df_fidelite, use_container_width=True, hide_index=True)
                    
                    # Statistiques
                    fideles = sum(1 for p in predictions if p["score_fidelite"] > 70)
                    a_risque = sum(1 for p in predictions if p["prediction_rachat"] == "faible")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Clients fidèles", fideles, delta="score > 70")
                    col2.metric("Risque de départ", a_risque, delta="prédiction faible")
                    col3.metric("Total clients analysés", len(predictions))
                    
                    # Graphique distribution
                    fig, ax = plt.subplots(figsize=(8, 4))
                    scores = [p["score_fidelite"] for p in predictions]
                    ax.hist(scores, bins=20, color='#4CAF50', alpha=0.7, edgecolor='black')
                    ax.set_xlabel("Score de fidélité")
                    ax.set_ylabel("Nombre de clients")
                    ax.set_title("Distribution des scores de fidélité")
                    ax.axvline(x=70, color='red', linestyle='--', label="Seuil fidèle")
                    ax.axvline(x=30, color='orange', linestyle='--', label="Seuil risque")
                    ax.legend()
                    fig.tight_layout()
                    st.pyplot(fig)
                    plt.close(fig)
                else:
                    st.info("Aucune donnée client disponible")