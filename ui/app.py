import streamlit as st
import requests
import pandas as pd
import html
from datetime import datetime

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
API_URL = "http://localhost:8000/ask"
API_USER = "admin"
API_PASS = "1234"

st.set_page_config(
    page_title="Chatbot ZAI Informatique",
    page_icon="💬",
    layout="wide"
)

# ─────────────────────────────────────────────
# CSS personnalisé
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .chat-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.2rem;
    }
    .chat-subtitle {
        font-size: 0.95rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .result-box {
        background: white;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        border-left: 4px solid #4CAF50;
        margin-top: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .rejected-box {
        background: #fff5f5;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        border-left: 4px solid #e53935;
        margin-top: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .clarification-box {
        background: #fffde7;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        border-left: 4px solid #FFC107;
        margin-top: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .history-wrapper {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 8px;
        background: #fafafa;
        height: 520px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: #cbd5e0 transparent;
    }
    .history-wrapper::-webkit-scrollbar { width: 5px; }
    .history-wrapper::-webkit-scrollbar-thumb {
        background: #cbd5e0;
        border-radius: 10px;
    }
    .history-item {
        background: white;
        border-radius: 8px;
        padding: 0.55rem 0.9rem;
        margin-bottom: 0.35rem;
        font-size: 0.86rem;
        color: #333;
        border: 1px solid #e8e8e8;
        line-height: 1.5;
    }
    .history-count {
        font-size: 0.78rem;
        color: #999;
        margin-bottom: 0.4rem;
    }
    .meta-chip {
        display: inline-block;
        background: #e8f5e9;
        color: #2e7d32;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.8rem;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []

# ─────────────────────────────────────────────
# Fonction appel API
# ─────────────────────────────────────────────
def call_api(question: str) -> dict:
    try:
        response = requests.post(
            API_URL,
            json={"question": question},
            auth=(API_USER, API_PASS),
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "table": [],
                "summary": f"Erreur API ({response.status_code})",
                "metadata": {"status": "error"}
            }
    except requests.exceptions.ConnectionError:
        return {
            "table": [],
            "summary": "Impossible de joindre l'API. Vérifiez que le serveur est démarré.",
            "metadata": {"status": "error"}
        }
    except Exception as e:
        return {
            "table": [],
            "summary": f"Erreur : {str(e)}",
            "metadata": {"status": "error"}
        }

# ─────────────────────────────────────────────
# Layout : 2 colonnes
# ─────────────────────────────────────────────
col_main, col_history = st.columns([3, 1], gap="large")

# ─────────────────────────────────────────────
# Colonne principale
# ─────────────────────────────────────────────
with col_main:
    st.markdown('<div class="chat-title">💬 Chatbot ZAI Informatique</div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-subtitle">Posez vos questions en langage naturel sur vos données Dolibarr</div>', unsafe_allow_html=True)

    # Zone de saisie
    with st.form(key="question_form", clear_on_submit=True):
        question = st.text_input(
            label="Votre question",
            placeholder="Ex: Donne-moi les factures non payées",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("➤ Envoyer", use_container_width=True)

    # Exemples cliquables
    st.markdown("**Exemples de questions :**")
    examples = [
        "Factures entre 2026-01-01 et 2026-02-28",
        "Factures non payées",
        "Produits avec stock inférieur à 5",
        "Clients avec plus de 2 commandes",
        "Chiffre d'affaires de janvier 2026",
    ]
    ex_cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if ex_cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            question = ex
            submitted = True

    # Traitement de la question
    if submitted and question.strip():
        with st.spinner("Analyse en cours..."):
            result = call_api(question.strip())

        status    = result.get("metadata", {}).get("status", "")
        summary   = result.get("summary", "")
        table_data = result.get("table", [])
        meta      = result.get("metadata", {})

        # Enregistrement dans l'historique
        st.session_state.history.insert(0, {
            "question":    question.strip(),
            "summary":     summary,
            "status":      status,
            "template":    meta.get("template", ""),
            "row_count":   meta.get("row_count", 0),
            "duration_ms": meta.get("duration_ms", 0),
            "logs_id":     meta.get("logs_id", ""),
            "timestamp":   datetime.now().strftime("%H:%M:%S")
        })

        # Affichage selon le statut
        if status == "rejected":
            st.markdown(f'<div class="rejected-box">🔒 <strong>Requête rejetée</strong><br>{html.escape(summary)}</div>', unsafe_allow_html=True)

        elif status == "clarification_required":
            st.markdown(f'<div class="clarification-box">❓ <strong>Précision nécessaire</strong><br>{html.escape(summary)}</div>', unsafe_allow_html=True)

        elif status == "error":
            st.error(f"⚠️ {summary}")

        else:
            template  = meta.get("template", "N/A")
            duration  = meta.get("duration_ms", 0)
            row_count = meta.get("row_count", 0)
            logs_id   = meta.get("logs_id", "")

            st.markdown(f"""
            <div class="result-box">
                ✅ <strong>{html.escape(summary)}</strong><br><br>
                <span class="meta-chip">📋 {html.escape(str(template))}</span>
                <span class="meta-chip">📊 {row_count} ligne(s)</span>
                <span class="meta-chip">⏱ {duration:.0f} ms</span>
                <span class="meta-chip" style="background:#e3f2fd;color:#1565c0;">🔑 {html.escape(str(logs_id))[:8]}...</span>
            </div>
            """, unsafe_allow_html=True)

            if table_data:
                st.markdown("#### Résultats")
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, height=min(400, 50 + 35 * len(df)))
            else:
                st.info("Aucune donnée retournée.")

# ─────────────────────────────────────────────
# Colonne historique — scrollable hauteur fixe
# ─────────────────────────────────────────────
with col_history:
    nb = len(st.session_state.history)
    st.markdown("### 🕘 Historique")

    if not st.session_state.history:
        st.markdown('<div style="color:#aaa;font-size:0.85rem;">Aucune question posée</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="history-count">{nb} question(s) enregistrée(s)</div>', unsafe_allow_html=True)

        # Construire les items en échappant TOUT le contenu dynamique
        items_html = ""
        for item in st.session_state.history:
            icon = {"rejected": "🔒", "clarification_required": "❓", "error": "⚠️"}.get(item["status"], "✅")

            q = html.escape(item["question"])
            s = html.escape(item["summary"])
            t = html.escape(item["timestamp"])

            # Tronquer après échappement
            q_short = q[:55] + "..." if len(q) > 55 else q
            s_short = s[:60] + "..." if len(s) > 60 else s

            items_html += (
                f'<div class="history-item">'
                f'{icon} <strong>{t}</strong><br>'
                f'{q_short}<br>'
                f'<span style="color:#999;font-size:0.78rem;">{s_short}</span>'
                f'</div>'
            )

        st.markdown(f'<div class="history-wrapper">{items_html}</div>', unsafe_allow_html=True)

        if st.button("🗑 Effacer l'historique", use_container_width=True):
            st.session_state.history = []
            st.rerun()