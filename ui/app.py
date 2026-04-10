# ui/app.py
import streamlit as st
import requests
import pandas as pd
import html
import io
import json
import os
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
API_URL  = "http://localhost:8000/ask"
API_USER = "admin"
API_PASS = "1234"

st.set_page_config(
    page_title="Chatbot ZAI Informatique",
    page_icon="💬",
    layout="wide"
)

def month_name(m):
    names = {
        "01": "janvier",  "02": "février",  "03": "mars",
        "04": "avril",    "05": "mai",       "06": "juin",
        "07": "juillet",  "08": "août",      "09": "septembre",
        "10": "octobre",  "11": "novembre",  "12": "décembre"
    }
    return names.get(m, m)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
.rejected-box {
    color: black !important;
}

.clarification-box {
    color: black !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.main { background-color: #f8f9fa; }
.chat-title { font-size: 1.8rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.2rem; }
.chat-subtitle { font-size: 0.95rem; color: #6c757d; margin-bottom: 1.5rem; }
.result-box {
    background: white !important; border-radius: 10px; padding: 1.2rem 1.5rem;
    border-left: 4px solid #4CAF50; margin-top: 1rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06); color: #111 !important;
}
.result-box strong { color: #111 !important; }
.rejected-box {
    background: #fff5f5 !important; border-radius: 10px; padding: 1.2rem 1.5rem;
    border-left: 4px solid #e53935;
}
.clarification-box {
    background: #fffde7 !important; border-radius: 10px; padding: 1.2rem 1.5rem;
    border-left: 4px solid #FFC107;
}
.history-wrapper {
    border: 1px solid #e0e0e0; border-radius: 10px; padding: 8px;
    background: #fafafa; height: 520px; overflow-y: auto;
    scrollbar-width: thin; scrollbar-color: #cbd5e0 transparent;
}
.history-wrapper::-webkit-scrollbar { width: 5px; }
.history-wrapper::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 10px; }
.history-item {
    background: white; border-radius: 8px; padding: 0.55rem 0.9rem;
    margin-bottom: 0.35rem; font-size: 0.86rem; color: #333; border: 1px solid #e8e8e8;
}
.meta-chip {
    display: inline-block; background: #e8f5e9; color: #2e7d32;
    border-radius: 20px; padding: 2px 10px; font-size: 0.8rem; margin-right: 6px;
}
.suggestion-box {
    background: #f3f4f6 !important; border-radius: 10px; padding: 0.8rem 1rem;
    border-left: 4px solid #6366f1;
}
/* ── Tableaux scrollables ── */
.scroll-table, .fb-scroll {
    background: #f9fafb !important; border: 1px solid #e5e7eb !important;
    border-radius: 10px; max-height: 350px; overflow-y: auto;
    scrollbar-width: thin; scrollbar-color: #cbd5e0 transparent;
}
.scroll-table::-webkit-scrollbar, .fb-scroll::-webkit-scrollbar { width: 5px; }
.scroll-table::-webkit-scrollbar-thumb, .fb-scroll::-webkit-scrollbar-thumb {
    background: #cbd5e0; border-radius: 10px;
}
.scroll-table-header, .fb-header {
    display: flex; background: #f1f3f5 !important; padding: 6px 10px;
    font-size: 0.78rem; font-weight: 600; color: #111 !important;
    border-bottom: 1px solid #dee2e6; position: sticky; top: 0; z-index: 2;
}
.scroll-table-row {
    display: flex; align-items: center; padding: 6px 10px;
    border-bottom: 1px solid #e5e7eb; font-size: 0.83rem;
    background: #ffffff !important; color: #111 !important;
}
.scroll-table-row:nth-child(even) { background: #f3f4f6 !important; }
.scroll-table-row:hover { background: #e5e7eb !important; }
.scroll-table-row span, .scroll-table-header span, .fb-header span { color: #111 !important; }
.col-rank  { width: 8%;  text-align: center; font-weight: 600; }
.col-ques  { width: 76%; }
.col-count { width: 16%; text-align: center; font-weight: 600; color: #2e7d32; }
/* ── Feedback row (Streamlit columns) ── */
.fb-row-wrapper {
    border-bottom: 1px solid #e5e7eb; padding: 4px 0;
    background: white; font-size: 0.83rem; color: #111;
}
.fb-row-wrapper:nth-child(even) { background: #f9fafb; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════
defaults = {
    "history":          [],
    "feedback":         {},
    "pending_question": "",
    "last_result":      None,
    "last_question":    "",
    "result_context":   "chatbot",
    "guided_form_key":  0,
    "form_question":    "",
    "active_tab":       0,
    "delete_fb_idx":    -1,
    "do_clear_form":    False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
    entry = {"timestamp": datetime.now().isoformat(), "logs_id": logs_id,
             "question": question, "rating": rating, "comment": comment}
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

def call_api(question: str) -> dict:
    try:
        r = requests.post(API_URL, json={"question": question},
                          auth=(API_USER, API_PASS), timeout=30)
        if r.status_code == 200:
            return r.json()
        return {"table": [], "summary": f"Erreur API ({r.status_code})",
                "metadata": {"status": "error", "suggestions": []}}
    except requests.exceptions.ConnectionError:
        return {"table": [], "summary": "Serveur inaccessible.",
                "metadata": {"status": "error", "suggestions": []}}
    except Exception as e:
        return {"table": [], "summary": str(e),
                "metadata": {"status": "error", "suggestions": []}}


def call_api_endpoint(endpoint: str, method: str = "GET") -> dict:
    try:
        fn = requests.get if method == "GET" else requests.post
        r  = fn(f"http://localhost:8000{endpoint}", auth=(API_USER, API_PASS), timeout=10)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


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
        "timestamp":   datetime.now().strftime("%H:%M:%S")
    })
# ── Nettoyage différé du champ de saisie ──
# Doit être traité ICI, avant que st.text_input(key="form_question") soit rendu
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
            ax.set_ylabel("CA HT"); ax.set_title("Chiffre d'affaires HT")
            ax.tick_params(axis="x", rotation=30); fig.tight_layout()
        elif template == "get_clients_multiple_commandes" and "nb_commandes" in df.columns:
            top = df.nlargest(10, "nb_commandes")
            fig, ax = plt.subplots(figsize=(6, max(3, len(top) * 0.4)))
            ax.barh(top["client_nom"].astype(str), top["nb_commandes"], color="#2196F3", alpha=0.85)
            ax.set_xlabel("Nb commandes"); ax.set_title("Top clients"); fig.tight_layout()
        elif template == "get_produits_stock_faible" and "stock_disponible" in df.columns:
            top = df.nsmallest(15, "stock_disponible")
            colors = ["#e53935" if s == 0 else "#FF9800" if s < 3 else "#4CAF50"
                      for s in top["stock_disponible"]]
            fig, ax = plt.subplots(figsize=(6, max(3, len(top) * 0.35)))
            ax.barh(top["produit_nom"].astype(str), top["stock_disponible"],
                    color=colors, alpha=0.85)
            ax.set_xlabel("Stock"); ax.set_title("Produits à stock faible"); fig.tight_layout()
        elif template in ("get_factures_non_payees", "get_factures_partiellement_payees") \
                and "montant_paye" in df.columns and "montant_restant" in df.columns:
            tp = float(df["montant_paye"].sum()); tr = float(df["montant_restant"].sum())
            if tp + tr > 0:
                fig, ax = plt.subplots(figsize=(5, 3))
                ax.pie([tp, tr], labels=["Payé", "Restant"],
                       colors=["#4CAF50", "#e53935"], autopct="%1.1f%%", startangle=90)
                ax.set_title("Répartition paiements"); fig.tight_layout()
        elif template == "get_factures_between" \
                and "date_facture" in df.columns and "total_ttc" in df.columns:
            df2 = df.copy()
            df2["date_facture"] = pd.to_datetime(df2["date_facture"], errors="coerce")
            df2 = df2.dropna(subset=["date_facture"]).sort_values("date_facture")
            if len(df2) >= 2:
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.plot(df2["date_facture"], df2["total_ttc"].astype(float),
                        color="#9C27B0", marker="o", markersize=3, linewidth=1.5)
                ax.set_ylabel("Total TTC"); ax.set_title("Factures sur la période")
                ax.tick_params(axis="x", rotation=30); fig.tight_layout()
    except Exception:
        fig = None
    return fig


# ═══════════════════════════════════════════════════════════════════════
# États prêts à l'emploi — définitions
# (dates dynamiques calculées à l'appel)
# ═══════════════════════════════════════════════════════════════════════

import json

ETATS_CONFIG_PATH = "config/etats_standards.json"

def get_etats_standards() -> list[dict]:
    """
    Charge les états depuis le fichier JSON de configuration.
    Fallback sur les états par défaut si le fichier est absent ou corrompu.
    """
    today           = date.today()
    first_day_month = date(today.year, today.month, 1)
    first_day_year  = date(today.year, 1, 1)
    mois_courant    = month_name(str(today.month).zfill(2))

    variables = {
        "today":            str(today),
        "first_day_month":  str(first_day_month),
        "first_day_year":   str(first_day_year),
        "mois_courant":     mois_courant,
        "annee":            str(today.year),
    }

    try:
        with open(ETATS_CONFIG_PATH, "r", encoding="utf-8") as f:
            etats_raw = json.load(f)

        etats = []
        for e in etats_raw:
            question = e["question_template"]
            for key, val in variables.items():
                question = question.replace(f"{{{key}}}", val)
            etats.append({
                "label":    e["label"],
                "question": question,
            })
        return etats

    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        # Fallback : liste hardcodée si le fichier est absent
        return [
            {"label": "🔴 Factures non payées",           "question": "factures non payées"},
            {"label": "📦 Produits stock faible (< 10)",   "question": "produits avec stock inférieur à 10"},
            {"label": "🏆 Top clients (multi-commandes)",  "question": "clients avec plus de 2 commandes"},
        ]

# ═══════════════════════════════════════════════════════════════════════
# render_result
# ═══════════════════════════════════════════════════════════════════════

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
    pfx         = f"{context}_{logs_id}"

    if status == "rejected":
        st.markdown(
            f'<div class="rejected-box">🔒 <strong>Requête rejetée</strong><br>'
            f'{html.escape(summary)}</div>', unsafe_allow_html=True)
        return
    if status == "clarification_required":
        st.markdown(
            f'<div class="clarification-box">❓ <strong>Précision nécessaire</strong><br>'
            f'{html.escape(summary)}</div>', unsafe_allow_html=True)
        return
    if status == "error":
        st.error(f"⚠️ {summary}")
        return

    duration  = meta.get("duration_ms", 0)
    row_count = meta.get("row_count", 0)
    cache_tag = " · cache ⚡" if from_cache else ""

    st.markdown(f"""
    <div class="result-box">
        ✅ <strong>{html.escape(summary)}</strong><br><br>
        <span class="meta-chip">📋 {html.escape(str(template))}</span>
        <span class="meta-chip">📊 {row_count} ligne(s)</span>
        <span class="meta-chip">⏱ {duration:.0f} ms{cache_tag}</span>
        <span class="meta-chip" style="background:#e3f2fd;color:#1565c0;">
            🔑 {html.escape(str(logs_id))[:8]}...
        </span>
    </div>
    """, unsafe_allow_html=True)

    if table_data:
        df = pd.DataFrame(table_data)
        st.markdown("#### Résultats")
        st.dataframe(df, use_container_width=True, height=min(400, 50 + 35 * len(df)))

        st.markdown("#### Exporter")
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        fig = auto_chart(df, template)

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
            with st.expander("🔍 Voir la requête SQL générée"):
                st.code(sql_query, language="sql")

    # ── Suggestions ──
    if suggestions:
        st.markdown("---")
        st.markdown(
            '<div class="suggestion-box"><span style="color:#111;">💡 <strong>Que souhaitez-vous faire ensuite ?</strong></span></div>',
            unsafe_allow_html=True)
        st.markdown("")
        sug_cols = st.columns(min(len(suggestions), 2))
        for i, s in enumerate(suggestions):
            if sug_cols[i % 2].button(f"→ {s}", key=f"sug_{pfx}_{i}",
                                       use_container_width=True):
                st.session_state.pending_question = s
                st.session_state.result_context   = context
                if context == "guided":
                    st.session_state.guided_form_key += 1
                st.rerun()

    # ── Feedback ──
    if logs_id == "noid":
        return

    fb_done_key = f"fb_done_{pfx}"
    st.markdown("---")

    if st.session_state.get(fb_done_key, False):
        return

    st.markdown("#### Évaluer cette réponse")
    fcol1, fcol2, fcol3 = st.columns([1, 1, 4])
    comment_key = f"comment_{pfx}"
    comment = st.text_input(
        "Commentaire",
        key=comment_key,
        placeholder="Écrivez un commentaire avant de valider...",
        label_visibility="collapsed"
    )
    if comment and not st.session_state.get(f"clicked_{pfx}", False):
        st.warning("⚠️ Veuillez choisir 👍 ou 👎 pour valider votre commentaire.")

    with fcol1:
        if st.button("👍 Correcte", key=f"ok_{pfx}", use_container_width=True):
            if not comment.strip():
                st.error("❌ Veuillez ajouter un commentaire avant de valider.")
            else:
                append_feedback(logs_id, question, "positive", comment)
                st.session_state[fb_done_key] = True
                st.rerun()
    with fcol2:
        if st.button("👎 Incorrecte", key=f"ko_{pfx}", use_container_width=True):
            if not comment.strip():
                st.error("❌ Veuillez ajouter un commentaire avant de valider.")
            else:
                append_feedback(logs_id, question, "negative", comment)
                st.session_state[fb_done_key] = True
                st.rerun()


# ─────────────────────────────────────────────
# Layout — 4 onglets (radio horizontal)
# ─────────────────────────────────────────────
tab_labels = ["💬 Chatbot", "🎯 Assistant guidé", "📊 Analyse prédictive",
              "⚙️ Cache & Audit", "📈 Analytics"]

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
if selected_tab == "💬 Chatbot":
    col_main, col_history = st.columns([3, 1], gap="large")

    with col_main:
        st.markdown('<div class="chat-title">💬 Chatbot ZAI Informatique</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="chat-subtitle">Posez vos questions en langage naturel sur vos données Dolibarr</div>',
            unsafe_allow_html=True)

        with st.form(key="question_form", clear_on_submit=False):
            q_input = st.text_input(
                "Votre question",
                placeholder="Ex: Donne-moi les factures non payées",
                label_visibility="collapsed",
                key="form_question"
            )
            submitted = st.form_submit_button("➤ Envoyer", use_container_width=True)

        if submitted and q_input.strip():
            st.session_state.pending_question = q_input.strip()
            st.session_state.result_context   = "chatbot"
            st.session_state.active_tab       = 0
            st.rerun()

        # ── MODIFICATION 1 : Combo box "États prêts à l'emploi" ──
        st.markdown("**États prêts à l'emploi :**")
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
            if ex_cols[i].button(ex, key=f"ex_chat_{i}", use_container_width=True):
                st.session_state.pending_question = ex
                st.session_state.result_context   = "chatbot"
                st.rerun()

        if (st.session_state.last_result is not None
                and st.session_state.result_context == "chatbot"):
            render_result(st.session_state.last_result,
                          st.session_state.last_question,
                          context="chatbot")

    with col_history:
        st.markdown("### 🕘 Historique")
        if not st.session_state.history:
            st.markdown('<div style="color:#aaa;font-size:0.85rem;">Aucune question posée</div>',
                        unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="font-size:0.78rem;color:#999;">'
                        f'{len(st.session_state.history)} question(s)</div>',
                        unsafe_allow_html=True)
            items_html = ""
            for item in st.session_state.history:
                icon = {"rejected": "🔒", "clarification_required": "❓",
                        "error": "⚠️"}.get(item["status"], "✅")
                q = html.escape(item["question"])
                s = html.escape(item["summary"])
                items_html += (
                    f'<div class="history-item">'
                    f'{icon} <strong>{item["timestamp"]}</strong><br>'
                    f'{q[:55]}{"..." if len(q) > 55 else ""}<br>'
                    f'<span style="color:#999;font-size:0.78rem;">'
                    f'{s[:60]}{"..." if len(s) > 60 else ""}</span>'
                    f'</div>'
                )
            st.markdown(f'<div class="history-wrapper">{items_html}</div>',
                        unsafe_allow_html=True)
            if st.button("🗑 Effacer l'historique", use_container_width=True):
                st.session_state.history        = []
                st.session_state.last_result    = None
                st.session_state.last_question  = ""
                st.session_state.do_clear_form  = True   # ← flag, pas d'assignation directe
                st.rerun()

# ═══════════════════════════════════════════
# Onglet 2 — Assistant guidé
# ═══════════════════════════════════════════
elif selected_tab == "🎯 Assistant guidé":
    st.markdown("## 🎯 Assistant guidé")
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
        submit_guided = st.form_submit_button("🚀 Lancer l'analyse", use_container_width=True)

    if submit_guided:
        today = date.today()
        if quick == "Ce mois":
            start_date = date(today.year, today.month, 1); end_date = today
        elif quick == "Année en cours":
            start_date = date(today.year, 1, 1); end_date = today
        elif quick == "Tout 2026":
            start_date = date(2026, 1, 1); end_date = date(2026, 12, 31)
        q_parts = {
            ("Factures", "Non payées"):            "factures non payées",
            ("Factures", "Partiellement payées"):  "factures partiellement payées",
            ("Factures", "Par client"):            "donne moi les factures",
            ("Factures", "Total"):                 f"factures entre {start_date} et {end_date}",
            ("Clients",  "Multiples commandes"):   "clients avec plus de 2 commandes",
            ("Produits", "Stock faible"):          "produits avec stock inférieur à 5",
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
# Onglet 3 — Analyse prédictive
# ═══════════════════════════════════════════
elif selected_tab == "📊 Analyse prédictive":
    st.markdown("### 🔮 Analyse prédictive")
    st.caption("Tendances et prévisions basées sur vos données historiques")

    pred_type = st.selectbox("Type d'analyse",
                             ["CA mensuel — prévision mois suivant",
                              "Stock — alertes rupture prévue",
                              "Clients — fidélité prévue"])

    if st.button("Lancer l'analyse", type="primary", key="btn_predict"):
        with st.spinner("Analyse en cours..."):
            if "CA mensuel" in pred_type:
                months = []
                for y, m in [("2025", "10"), ("2025", "11"), ("2025", "12"),
                              ("2026", "01"), ("2026", "02"), ("2026", "03")]:
                    r = call_api(f"chiffre d affaires de {month_name(m)} {y}")
                    t = r.get("table", [])
                    if t and "CA_HT" in t[0]:
                        months.append({"mois": f"{y}-{m}", "CA_HT": float(t[0]["CA_HT"] or 0)})
                if months:
                    st.dataframe(pd.DataFrame(months), use_container_width=True)
                    st.info("💡 Utilisez POST /predict pour la prévision complète.")
                else:
                    st.info("Données insuffisantes.")
            elif "Stock" in pred_type:
                r = call_api("produits stock inférieur à 10")
                t = r.get("table", [])
                if t:
                    st.warning(f"⚠️ {len(t)} produit(s) à risque")
                    st.dataframe(pd.DataFrame(t), use_container_width=True)
                else:
                    st.success("Aucun produit en risque.")
            elif "fidélité" in pred_type:
                r = call_api("clients avec plus de 2 commandes")
                t = r.get("table", [])
                if t:
                    st.metric("Clients fidèles", len(t))
                    st.dataframe(pd.DataFrame(t), use_container_width=True)

# ═══════════════════════════════════════════
# Onglet 4 — Cache & Audit
# ═══════════════════════════════════════════
elif selected_tab == "⚙️ Cache & Audit":
    st.markdown("### ⚙️ Monitoring — Cache & Audit")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Cache")
        if st.button("🔄 Actualiser", key="btn_cache_refresh"):
            stats = call_api_endpoint("/cache/stats")
            if stats:
                st.metric("Taille", f"{stats.get('size', 0)} / {stats.get('max_size', 100)}")
                st.metric("Hit rate", f"{stats.get('hit_rate', 0)}%")
                col_a, col_b = st.columns(2)
                col_a.metric("Hits", stats.get("hits", 0))
                col_b.metric("Misses", stats.get("misses", 0))
                by_tpl = stats.get("by_template", {})
                if by_tpl:
                    st.dataframe(pd.DataFrame(list(by_tpl.items()),
                                              columns=["Template", "Entrées"]))
            else:
                st.info("API non disponible.")
        if st.button("🗑 Vider le cache", type="secondary", key="btn_cache_clear"):
            call_api_endpoint("/cache/clear", method="POST")
            st.success("Cache vidé.")

    with c2:
        st.markdown("#### Audit")
        audit = call_api_endpoint("/audit")
        if audit and "total_requests" in audit:

            # ── Métriques globales ──
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total requêtes",  audit.get("total_requests", 0))
            m2.metric("Succès",          audit.get("success_count", 0))
            m3.metric("Erreurs",         audit.get("error_count", 0))
            m4.metric("Rejetées",        audit.get("rejected_count", 0))

            # ── Latence P95 / P99 ──
            st.markdown("**Latence (ms)**")
            latency = audit.get("latency", {})
            lc1, lc2, lc3, lc4 = st.columns(4)
            lc1.metric("Moyenne",  f"{latency.get('mean_ms', 0):.0f} ms")
            lc2.metric("Médiane",  f"{latency.get('median_ms', 0):.0f} ms")
            lc3.metric("P95",      f"{latency.get('p95_ms', 0):.0f} ms")
            lc4.metric("P99",      f"{latency.get('p99_ms', 0):.0f} ms")

            # ── Cache hit/miss ──
            st.markdown("**Cache**")
            cache = audit.get("cache", {})
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Hit rate",  f"{cache.get('hit_rate_pct', 0):.1f}%")
            cc2.metric("Hits",      cache.get("cache_hits", 0))
            cc3.metric("Misses",    cache.get("cache_misses", 0))

            # ── Alertes ──
            alerts = audit.get("alerts", [])
            if alerts:
                st.markdown("**Alertes**")
                for alert in alerts:
                    level = alert.get("level", "warning")
                    msg   = alert.get("message", "")
                    if level == "critical":
                        st.error(f"🔴 {msg}")
                    else:
                        st.warning(f"🟡 {msg}")
            else:
                st.success("✅ Aucune alerte — système nominal")

            # ── Tendances 24h ──
            trends = audit.get("trends", {})
            if trends.get("recent_24h", {}).get("count", 0) > 0:
                st.markdown("**Tendance 24h**")
                delta = trends.get("delta_pct", 0)
                trend = trends.get("trend", "stable")
                color = "normal" if trend == "stable" else (
                "inverse" if trend == "hausse" else "normal"
            )
                tc1, tc2 = st.columns(2)
                tc1.metric(
                "Requêtes dernières 24h",
                trends["recent_24h"]["count"],
                delta=f"{trends['recent_24h']['mean_ms']:.0f} ms moy."
            )
                tc2.metric(
                "Tendance latence",
                trend.capitalize(),
                delta=f"{delta:+.1f}%",
                delta_color=color
            )

            # ── Top questions (tableau HTML existant) ──
            top_q = audit.get("top_questions", {})
            if top_q:
                st.markdown("**Top questions**")
                header = (
                '<div class="scroll-table">'
                '<div class="scroll-table-header">'
                '<span class="col-rank">#</span>'
                '<span class="col-ques">Question</span>'
                '<span class="col-count">Nb</span>'
                '</div>'
            )
                rows_html = ""
                for rank, (q_text, cnt) in enumerate(
                        sorted(top_q.items(), key=lambda x: -x[1]), 1):
                    q_esc = html.escape(
                    q_text[:70] + ("…" if len(q_text) > 70 else ""))
                    rows_html += (
                    f'<div class="scroll-table-row">'
                    f'<span class="col-rank">{rank}</span>'
                    f'<span class="col-ques">{q_esc}</span>'
                    f'<span class="col-count">{cnt}</span>'
                    f'</div>'
                )
                st.markdown(
                header + rows_html + "</div>",
                unsafe_allow_html=True
            )

        else:
            st.info("API non disponible.")

    # ── Feedback utilisateurs ──
    st.markdown("---")
    st.markdown("#### Feedback utilisateurs")

    feedbacks = load_feedbacks()

    if not feedbacks:
        st.info("Aucun feedback enregistré. Utilisez 👍/👎 dans l'onglet Chatbot.")
    else:
        pos = sum(1 for f in feedbacks if f.get("rating") == "positive")
        neg = sum(1 for f in feedbacks if f.get("rating") == "negative")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total", len(feedbacks))
        m2.metric("👍 Positifs", pos)
        m3.metric("👎 Négatifs", neg)

        df_fb = pd.DataFrame(feedbacks)
        st.download_button("⬇ Exporter tout en CSV",
                           data=df_to_csv_bytes(df_fb),
                           file_name="feedbacks.csv", mime="text/csv",
                           key="btn_export_fb")

        st.markdown("##### Liste des feedbacks")

        # ── En-tête HTML ──
        st.markdown(
            '<div class="fb-scroll">'
            '<div class="fb-header">'
            '<span style="width:6%;text-align:center;">Note</span>'
            '<span style="width:14%;">Date</span>'
            '<span style="width:40%;">Question</span>'
            '<span style="width:30%;font-style:italic;">Commentaire</span>'
            '<span style="width:10%;text-align:center;">Suppr.</span>'
            '</div></div>',
            unsafe_allow_html=True
        )

        # ── Lignes : st.columns → pas de redirect ──
        for i, fb in enumerate(feedbacks):
            icon    = "👍" if fb.get("rating") == "positive" else "👎"
            ts      = fb.get("timestamp", "")[:16].replace("T", " ")
            q_text  = fb.get("question", "")[:60]
            comment = fb.get("comment", "") or "—"
            comment = comment[:50]

            rc = st.columns([0.06, 0.13, 0.40, 0.30, 0.11])
            rc[0].markdown(f"<div style='text-align:center;font-size:1rem;'>{icon}</div>",
                           unsafe_allow_html=True)
            rc[1].caption(ts)
            rc[2].markdown(f"<small style='color:#111;'>{html.escape(q_text)}</small>",
                           unsafe_allow_html=True)
            rc[3].markdown(f"<small style='color:#666;font-style:italic;'>{html.escape(comment)}</small>",
                           unsafe_allow_html=True)
            # FIX : bouton Streamlit natif → pas de redirect, reste sur la même page
            if rc[4].button("🗑", key=f"del_{i}", help="Supprimer ce feedback"):
                st.session_state.delete_fb_idx = i
                st.rerun()

        st.markdown("")
        if st.button("🗑 Supprimer tous les feedbacks", type="secondary",
                     key="btn_delete_all_fb"):
            save_feedbacks([])
            st.success("Tous les feedbacks supprimés.")
            st.rerun()
        
elif selected_tab == "📈 Analytics":
    st.markdown("### 📈 Analytics — Requêtes utilisateurs")
    st.caption("Analyse comportementale basée sur les logs de production")

    data = call_api_endpoint("/analytics")

    if not data or data.get("empty"):
        st.info("Aucune donnée disponible. Posez quelques questions d'abord.")
    else:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use("Agg")

        total = data.get("total_requests", 0)
        sr    = data.get("success_rate", 0)
        gmean = data.get("global_mean_ms", 0)
        cache = data.get("cache", {})

        # ── Métriques résumé ──
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total requêtes",   total)
        r2.metric("Taux de succès",   f"{sr}%")
        r3.metric("Latence moy.",     f"{gmean:.0f} ms")
        r4.metric("Cache hit rate",   f"{cache.get('hit_rate', 0)}%")

        st.markdown("---")
        col_left, col_right = st.columns(2)

        # ── Graphique 1 : Répartition par template ──
        with col_left:
            st.markdown("#### Répartition par template")
            tpl_counts = data.get("template_counts", {})
            if tpl_counts:
                fig1, ax1 = plt.subplots(figsize=(6, 4))
                labels = [k.replace("get_", "") for k in tpl_counts.keys()]
                values = list(tpl_counts.values())
                colors = ["#4CAF50", "#2196F3", "#FF9800", "#9C27B0",
                          "#e53935", "#00BCD4", "#FF5722", "#795548",
                          "#607D8B", "#E91E63"]
                ax1.barh(labels, values,
                         color=colors[:len(labels)], alpha=0.85)
                ax1.set_xlabel("Nb requêtes")
                ax1.set_title("Templates les plus utilisés")
                for i, v in enumerate(values):
                    ax1.text(v + 0.3, i, str(v), va="center", fontsize=9)
                fig1.tight_layout()
                st.pyplot(fig1)
                plt.close(fig1)

        # ── Graphique 2 : Volume par jour ──
        with col_right:
            st.markdown("#### Volume journalier (7 derniers jours)")
            daily = data.get("daily_volume", {})
            if daily:
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                days   = list(daily.keys())
                counts = list(daily.values())
                ax2.plot(days, counts, color="#2196F3",
                         marker="o", linewidth=2, markersize=6)
                ax2.fill_between(days, counts, alpha=0.15, color="#2196F3")
                ax2.set_ylabel("Requêtes")
                ax2.set_title("Évolution du volume journalier")
                ax2.tick_params(axis="x", rotation=30)
                for i, v in enumerate(counts):
                    ax2.annotate(str(v), (days[i], counts[i]),
                                 textcoords="offset points",
                                 xytext=(0, 8), ha="center", fontsize=9)
                fig2.tight_layout()
                st.pyplot(fig2)
                plt.close(fig2)

        st.markdown("---")
        col_l2, col_r2 = st.columns(2)

        # ── Graphique 3 : Latence par template ──
        with col_l2:
            st.markdown("#### Latence par template (sans cache)")
            lat_tpl = data.get("latency_by_template", {})
            if lat_tpl:
                fig3, ax3 = plt.subplots(figsize=(6, 4))
                tpls   = [k.replace("get_", "") for k in lat_tpl.keys()]
                means  = [v["mean"] for v in lat_tpl.values()]
                p95s   = [v["p95"]  for v in lat_tpl.values()]
                x = range(len(tpls))
                w = 0.35
                ax3.bar([i - w/2 for i in x], means,
                        width=w, color="#4CAF50", alpha=0.85, label="Moyenne")
                ax3.bar([i + w/2 for i in x], p95s,
                        width=w, color="#FF9800", alpha=0.85, label="P95")
                ax3.set_xticks(list(x))
                ax3.set_xticklabels(tpls, rotation=30, ha="right", fontsize=8)
                ax3.set_ylabel("ms")
                ax3.set_title("Latence moyenne vs P95 par template")
                ax3.legend(fontsize=9)
                fig3.tight_layout()
                st.pyplot(fig3)
                plt.close(fig3)

        # ── Graphique 4 : Cache cold vs warm ──
        with col_r2:
            st.markdown("#### Impact du cache sur la latence")
            cold_m = cache.get("cold_mean", 0)
            warm_m = cache.get("warm_mean", 0)
            if cold_m > 0 or warm_m > 0:
                fig4, ax4 = plt.subplots(figsize=(6, 4))
                cats = ["Sans cache\n(cold)", "Avec cache\n(warm)"]
                vals = [cold_m, warm_m]
                bars = ax4.bar(cats, vals,
                               color=["#FF9800", "#4CAF50"], alpha=0.85, width=0.4)
                ax4.set_ylabel("Latence moy. (ms)")
                ax4.set_title("Comparaison latence cache hit vs miss")
                for bar, val in zip(bars, vals):
                    ax4.text(bar.get_x() + bar.get_width()/2,
                             bar.get_height() + 5,
                             f"{val:.0f} ms",
                             ha="center", fontsize=11, fontweight="bold")
                if cold_m > 0 and warm_m < cold_m:
                    gain = round((1 - warm_m/cold_m) * 100, 1)
                    ax4.set_title(
                        f"Gain cache : {gain}% de réduction de latence",
                        fontsize=11)
                fig4.tight_layout()
                st.pyplot(fig4)
                plt.close(fig4)
            else:
                st.info("Pas encore de données cache warm.")

        st.markdown("---")

        # ── Tableau : Top questions ──
        st.markdown("#### Top 10 questions les plus posées")
        top_q = data.get("top_questions", {})
        if top_q:
            df_topq = pd.DataFrame([
                {"Question": q[:80], "Nb": n}
                for q, n in top_q.items()
            ])
            st.dataframe(df_topq, use_container_width=True, hide_index=True)

        # ── Tableau : Taux de succès par template ──
        st.markdown("#### Taux de succès par template")
        sbt = data.get("success_by_template", {})
        if sbt:
            df_sbt = pd.DataFrame([
                {"Template": k.replace("get_", ""), "Taux succès (%)": v}
                for k, v in sorted(sbt.items(), key=lambda x: -x[1])
            ])
            st.dataframe(df_sbt, use_container_width=True, hide_index=True)