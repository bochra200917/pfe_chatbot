import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
API_URL = "http://localhost:8000/ask"
API_USER="admin"
API_PASS="1234"

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
    .history-item {
        background: white;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin-bottom: 0.4rem;
        font-size: 0.88rem;
        color: #333;
        border: 1px solid #e0e0e0;
        cursor: pointer;
    }
    .history-item:hover { background: #f0f4ff; }
    .meta-chip {
        display: inline-block;
        background: #e8f5e9;
        color: #2e7d32;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.8rem;
        margin-right: 6px;
    }
    .meta-chip-red {
        background: #ffebee;
        color: #c62828;
    }
    .meta-chip-yellow {
        background: #fffde7;
        color: #f57f17;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "question_input" not in st.session_state:
    st.session_state.question_input = ""

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

        status = result.get("metadata", {}).get("status", "")
        summary = result.get("summary", "")
        table_data = result.get("table", [])
        meta = result.get("metadata", {})

        # Enregistrement dans l'historique
        st.session_state.history.insert(0, {
            "question": question.strip(),
            "summary": summary,
            "status": status,
            "template": meta.get("template", ""),
            "row_count": meta.get("row_count", 0),
            "duration_ms": meta.get("duration_ms", 0),
            "logs_id": meta.get("logs_id", ""),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

        # Affichage selon le statut
        if status == "rejected":
            st.markdown(f"""
            <div class="rejected-box">
                🔒 <strong>Requête rejetée</strong><br>
                {summary}
            </div>
            """, unsafe_allow_html=True)

        elif status == "clarification_required":
            st.markdown(f"""
            <div class="clarification-box">
                ❓ <strong>Précision nécessaire</strong><br>
                {summary}
            </div>
            """, unsafe_allow_html=True)

        elif status == "error":
            st.error(f"⚠️ {summary}")

        else:
            # Résultat OK
            template = meta.get("template", "N/A")
            duration = meta.get("duration_ms", 0)
            row_count = meta.get("row_count", 0)
            logs_id = meta.get("logs_id", "")

            st.markdown(f"""
            <div class="result-box">
                ✅ <strong>{summary}</strong><br><br>
                <span class="meta-chip">📋 {template}</span>
                <span class="meta-chip">📊 {row_count} ligne(s)</span>
                <span class="meta-chip">⏱ {duration:.0f} ms</span>
                <span class="meta-chip" style="background:#e3f2fd;color:#1565c0;">🔑 {logs_id[:8]}...</span>
            </div>
            """, unsafe_allow_html=True)

            # Tableau de résultats
            if table_data:
                st.markdown("#### Résultats")
                df = pd.DataFrame(table_data)
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=min(400, 50 + 35 * len(df))
                )
            else:
                st.info("Aucune donnée retournée.")

# ─────────────────────────────────────────────
# Colonne historique
# ─────────────────────────────────────────────
with col_history:
    st.markdown("### 🕘 Historique")

    if not st.session_state.history:
        st.markdown('<div style="color:#aaa;font-size:0.85rem;">Aucune question posée</div>', unsafe_allow_html=True)
    else:
        for i, item in enumerate(st.session_state.history[:20]):
            status_icon = {
                "rejected": "🔒",
                "clarification_required": "❓",
                "error": "⚠️"
            }.get(item["status"], "✅")

            st.markdown(f"""
            <div class="history-item">
                {status_icon} <strong>{item['timestamp']}</strong><br>
                {item['question'][:50]}{'...' if len(item['question']) > 50 else ''}
                <br><span style="color:#999;font-size:0.78rem;">{item['summary'][:60]}{'...' if len(item['summary']) > 60 else ''}</span>
            </div>
            """, unsafe_allow_html=True)

    if st.session_state.history:
        if st.button("🗑 Effacer l'historique", use_container_width=True):
            st.session_state.history = []
            st.rerun()