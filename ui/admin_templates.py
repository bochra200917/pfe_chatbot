# ui/admin_templates.py

import streamlit as st
import json
import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import requests as req
from datetime import datetime
import sqlparse

matplotlib.use("Agg")

# ─── Configuration page ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Admin — Templates SQL",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS personnalisé – Style Dolibarr/Cieloo amélioré ────────────────────────
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

    /* Tokens de couleurs (ref. Dolibarr) */
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

    /* ========== SIDEBAR REPENSÉE (couleur dans le thème) ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #eef2ff 0%, #ffffff 80%);
        border-right: 1px solid #e0e7ef;
        box-shadow: 2px 0 12px rgba(0,0,0,0.03);
    }
    [data-testid="stSidebar"] * {
        color: var(--ink-doli) !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: var(--muted-doli) !important;
        font-weight: 500;
        padding: 0.5rem 0.75rem;
        border-radius: 10px;
        transition: background 0.2s, color 0.2s;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #e0e7ff;
        color: var(--blue-doli) !important;
    }
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] label {
        background: linear-gradient(90deg, #e0e7ff, #ffffff);
        color: var(--blue-doli) !important;
        font-weight: 700;
        border-left: 3px solid var(--blue-doli);
        padding-left: 0.6rem;
    }
    /* Titre "Admin Panel" dans la sidebar */
    /* Titre "Admin Panel" dans la sidebar */
.sidebar .stMarkdown h3, [data-testid="stSidebar"] h3 {
    font-size: 1.5rem;   /* au lieu de 1.1rem */
    font-weight: 800;     /* plus gras */
    color: var(--blue-doli);
    letter-spacing: -0.3px;
    margin-bottom: 0.5rem;
}
    /* Séparateur dans sidebar */
    [data-testid="stSidebar"] hr {
        margin: 1rem 0;
        border-color: #e2e8f0;
    }

    /* Header principal – effet glassmorphisme léger */
    .admin-header {
        background: linear-gradient(135deg, #2563eb, #3b82f6);
        border: none;
        border-radius: var(--radius-doli);
        padding: 24px 32px;
        margin-bottom: 28px;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: 0 12px 24px rgba(37,99,235,0.18), 0 1px 2px rgba(0,0,0,0.02);
        position: relative;
        overflow: hidden;
    }
    .admin-header::before {
        content: '';
        position: absolute;
        top: -30%;
        right: -10%;
        width: 200px;
        height: 200px;
        background: rgba(255,255,255,0.08);
        border-radius: 50%;
        pointer-events: none;
    }
    .admin-header h1 {
        color: #ffffff;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
        text-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .admin-header p {
        color: rgba(255,255,255,0.85);
        margin: 4px 0 0 0;
        font-size: 0.85rem;
    }

    /* Cartes de statistiques – effet premium */
    .stat-card {
        background: var(--card-doli);
        border: 1px solid var(--border-doli);
        border-radius: var(--radius-doli);
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 20px rgba(0,0,0,0.02), 0 2px 4px rgba(0,0,0,0.02);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 18px 32px rgba(0,0,0,0.06), 0 2px 6px rgba(0,0,0,0.02);
        border-color: #d9e2ef;
    }
    .stat-number {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--blue-doli);
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.02em;
    }
    .stat-label {
        color: var(--muted-doli);
        font-size: 0.8rem;
        margin-top: 8px;
        font-weight: 500;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 30px;
        font-size: 0.7rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .badge-active   { background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
    .badge-inactive { background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; }
    .badge-select   { background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }

    /* Bloc SQL */
    .sql-block {
        background: #f8fafc;
        border: 1px solid var(--border-doli);
        border-left: 4px solid var(--blue-doli);
        border-radius: 12px;
        padding: 14px 18px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: var(--ink-doli);
        white-space: pre-wrap;
        margin: 12px 0;
        line-height: 1.5;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.01), 0 1px 2px rgba(0,0,0,0.02);
    }

    /* Alertes sécurité */
    .security-warning {
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-left: 4px solid #f59e0b;
        border-radius: 10px;
        padding: 12px 16px;
        color: #92400e;
        font-size: 0.83rem;
        margin: 12px 0;
    }
    .security-ok {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 4px solid #22c55e;
        border-radius: 10px;
        padding: 12px 16px;
        color: #15803d;
        font-size: 0.83rem;
        margin: 12px 0;
    }

    /* Boutons modernes */
    .stButton > button {
        border-radius: 10px;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94);
        background: linear-gradient(135deg, var(--blue-doli), var(--blue-2));
        color: white;
        border: none;
        box-shadow: 0 2px 8px rgba(37,99,235,0.2);
        padding: 0.4rem 1rem;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(37,99,235,0.3);
        background: linear-gradient(135deg, #1d4ed8, #2563eb);
    }
    .stButton > button:active {
        transform: translateY(1px);
    }

    /* Expander styling – plus aéré */
    [data-testid="stExpander"] {
        border: 1px solid #eef2f6;
        border-radius: 16px;
        background: var(--card-doli);
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        margin-bottom: 12px;
        transition: box-shadow 0.2s;
    }
    [data-testid="stExpander"]:hover {
        box-shadow: 0 8px 20px rgba(0,0,0,0.04);
        border-color: #e2e8f0;
    }
    [data-testid="stExpander"] details {
        padding: 0;
    }
    [data-testid="stExpander"] summary {
        padding: 1rem 1.2rem;
        font-weight: 600;
    }

    /* Version badge */
    .version-tag {
        background: #f1f5f9;
        color: var(--muted-doli);
        border: 1px solid #e2e8f0;
        border-radius: 30px;
        padding: 2px 14px;
        font-size: 0.7rem;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
    }

    hr {
        border-color: #edf2f7;
        margin: 1.5rem 0;
    }

    /* Tableaux scrollables – plus de confort */
    .scroll-table, .fb-scroll {
        background: var(--card-doli) !important;
        border: 1px solid #edf2f7 !important;
        border-radius: 16px;
        max-height: 380px;
        overflow-y: auto;
        scrollbar-width: thin;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .scroll-table::-webkit-scrollbar, .fb-scroll::-webkit-scrollbar {
        width: 5px;
        height: 5px;
    }
    .scroll-table::-webkit-scrollbar-thumb, .fb-scroll::-webkit-scrollbar-thumb {
        background: #cbd5e0;
        border-radius: 10px;
    }
    .scroll-table-header, .fb-header {
        display: flex;
        background: #fafcff !important;
        padding: 8px 12px;
        font-size: 0.75rem;
        font-weight: 700;
        color: var(--ink-doli);
        border-bottom: 1px solid var(--border-doli);
        position: sticky;
        top: 0;
        z-index: 2;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .scroll-table-row {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        border-bottom: 1px solid #f0f2f5;
        font-size: 0.85rem;
        background: var(--card-doli) !important;
        color: var(--ink-doli);
        transition: background 0.1s;
    }
    .scroll-table-row:nth-child(even) {
        background: #fafcff !important;
    }
    .scroll-table-row:hover {
        background: #f1f5f9 !important;
    }
    .col-rank  { width: 8%; text-align: center; font-weight: 600; }
    .col-ques  { width: 76%; }
    .col-count { width: 16%; text-align: center; font-weight: 700; color: #2e7d32; }

    /* Messages information */
    .stAlert {
        border-radius: 12px;
        border-left-width: 4px;
    }
    /* Inputs plus propres */
    .stTextInput > div > input, .stSelectbox > div > select, .stTextArea textarea {
        border-radius: 10px;
        border: 1px solid #e0e7ef;
        transition: border 0.15s, box-shadow 0.15s;
    }
    .stTextInput > div > input:focus, .stSelectbox > div > select:focus, .stTextArea textarea:focus {
        border-color: var(--blue-doli);
        box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ─── Constantes ───────────────────────────────────────────────────────────────
TEMPLATES_FILE = os.path.join(os.path.dirname(__file__), "templates.json")
HYBRID_API_URL = "http://localhost:8001"

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "EXEC", "EXECUTE", "GRANT", "REVOKE", "UNION",
]

ALLOWED_TABLES = [
    "m38h_facture", "m38h_facturedet", "m38h_facture_fourn", "m38h_facture_fourn_det",
    "m38h_commande", "m38h_commandedet", "m38h_commande_fournisseur", "m38h_commande_fournisseur_det",
    "m38h_societe", "m38h_socpeople",
    "m38h_product", "m38h_product_stock", "m38h_product_price",
    "m38h_stock_mouvement", "m38h_entrepot",
    "m38h_paiement", "m38h_paiement_facture",
    "m38h_projet", "m38h_projet_task",
    "m38h_categorie", "m38h_categorie_product",
    "m38h_accounting_account", "m38h_accounting_bookkeeping",
    "m38h_bank", "m38h_bank_account",
    "m38h_user", "m38h_salary",
    "m38h_bom_bom", "m38h_bom_bom_line",
    "m38h_mrp_mo",
    "m38h_holiday", "m38h_usergroup",
    "m38h_const", "m38h_cashdaily", "m38h_cashcontrol"
]

# ─── Fonctions utilitaires ─────────────────────────────────────────────────────
def load_templates() -> dict:
    if not os.path.exists(TEMPLATES_FILE):
        return {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "templates": {}
        }
    with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_templates(data: dict):
    data["updated_at"] = datetime.now().isoformat()
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def validate_sql(sql: str) -> tuple:
    errors = []
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        errors.append('<i class="fa-regular fa-circle-xmark"></i> La requête doit commencer par SELECT.')
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + kw + r'\b', sql_upper):
            errors.append(f'<i class="fa-regular fa-circle-xmark"></i> Mot-clé interdit détecté : `{kw}`')
    if "LIMIT" not in sql_upper:
        errors.append('<i class="fa-solid fa-triangle-exclamation"></i> Aucun LIMIT détecté — ajoute LIMIT :limit pour sécuriser.')
    return len(errors) == 0, errors

def extract_params(sql: str) -> list:
    return list(set(re.findall(r':(\w+)', sql)))

def get_stats(data: dict) -> dict:
    templates = data.get("templates", {})
    active = sum(1 for t in templates.values() if t.get("active", True))
    return {
        "total":    len(templates),
        "active":   active,
        "inactive": len(templates) - active,
        "version":  data.get("version", "1.0"),
    }

def call_hybrid_api(endpoint: str) -> dict:
    try:
        r = req.get(f"{HYBRID_API_URL}{endpoint}", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

def call_api_endpoint(endpoint: str, method: str = "GET") -> dict:
    API_USER = "admin"
    API_PASS = "1234"
    try:
        fn = req.get if method == "GET" else req.post
        r = fn(f"http://localhost:8000{endpoint}", auth=(API_USER, API_PASS), timeout=10)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

# ─── Initialisation session state ─────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = load_templates()
if "msg" not in st.session_state:
    st.session_state.msg = None

# ─── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('### <i class="fa-solid fa-screwdriver-wrench"></i> Admin Panel', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio(
        "Navigation",
        [
            "Liste des templates",
            "Nouveau template",
            "Tester un template",
            "Statistiques",
            "Analytics (hybride)",
            "Cache & Audit",
            "Analytics (requêtes)",
            "Paramètres",
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    stats = get_stats(st.session_state.data)
    st.markdown(f"""
    **Version whitelist :** `{stats['version']}`
    **Templates actifs :** `{stats['active']} / {stats['total']}`
    **Dernière MAJ :** `{st.session_state.data.get('updated_at','—')[:10]}`
    """)
    st.markdown("---")
    if st.button("⟳ Recharger depuis fichier", use_container_width=True):
        st.session_state.data = load_templates()
        st.rerun()

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="admin-header">
    <div>
        <h1><i class="fa-solid fa-screwdriver-wrench"></i> Interface Admin — Templates SQL</h1>
        <p>Chatbot Dolibarr · Gestion sécurisée des requêtes NL2SQL</p>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.msg:
    mtype, mtxt = st.session_state.msg
    if mtype == "success":
        st.success(mtxt)
    elif mtype == "error":
        st.error(mtxt)
    elif mtype == "warning":
        st.warning(mtxt)
    st.session_state.msg = None

# ════════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Liste des templates (contenu inchangé)
# ════════════════════════════════════════════════════════════════════════════════
if page == "Liste des templates":

    templates = st.session_state.data.get("templates", {})

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        search = st.text_input("⌕ Rechercher", placeholder="nom, intent, mot-clé SQL…")
    with col_f2:
        filter_status = st.selectbox("Statut", ["Tous", "Actifs", "Inactifs"])
    with col_f3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Tout sauvegarder", use_container_width=True, type="primary"):
            save_templates(st.session_state.data)
            st.session_state.msg = ("success", "✓ Templates sauvegardés avec succès.")
            st.rerun()

    st.markdown("---")

    filtered = {}
    for tid, t in templates.items():
        active = t.get("active", True)
        if filter_status == "Actifs" and not active:
            continue
        if filter_status == "Inactifs" and active:
            continue
        if search:
            s = search.lower()
            haystack = (
                tid + t.get("intent", "") + t.get("description", "") + t.get("sql", "")
            ).lower()
            if s not in haystack:
                continue
        filtered[tid] = t

    if not filtered:
        st.info("Aucun template trouvé. Crée-en un depuis **Nouveau template**.")
    else:
        for tid, t in filtered.items():
            active = t.get("active", True)
            status_badge = (
                '<span class="badge badge-active">● ACTIF</span>'
                if active else
                '<span class="badge badge-inactive">○ INACTIF</span>'
            )
            params = extract_params(t.get("sql", ""))
            params_html = " ".join(
                f'<span class="badge badge-select">:{p}</span>' for p in params
            ) or "<em style='color:#64748b'>aucun</em>"

            with st.expander(
                f"**{t.get('intent', tid)}** — {t.get('description', '')[:60]}…"
            ):
                st.markdown(
                    f"{status_badge} &nbsp; <span class='version-tag'>id: {tid}</span>",
                    unsafe_allow_html=True
                )
                st.markdown(f"**Paramètres :** {params_html}", unsafe_allow_html=True)
                st.markdown("**Requête SQL :**")
                st.markdown(
                    f'<div class="sql-block">{t.get("sql", "— vide —")}</div>',
                    unsafe_allow_html=True
                )

                valid, errs = validate_sql(t.get("sql", ""))
                if valid:
                    st.markdown(
                        '<div class="security-ok"><i class="fa-regular fa-circle-check"></i> Requête valide (SELECT-only, pas de mots interdits)</div>',
                        unsafe_allow_html=True
                    )
                else:
                    for e in errs:
                        st.markdown(
                            f'<div class="security-warning">{e}</div>',
                            unsafe_allow_html=True
                        )

                st.markdown("---")
                c1, c2 = st.columns(2)
                with c1:
                    new_desc = st.text_input(
                        "Description", value=t.get("description", ""), key=f"desc_{tid}"
                    )
                    new_intent = st.text_input(
                        "Intent", value=t.get("intent", ""), key=f"intent_{tid}"
                    )
                with c2:
                    new_sql = st.text_area(
                        "SQL", value=t.get("sql", ""), key=f"sql_{tid}", height=120
                    )
                    new_active = st.toggle(
                        "Actif", value=active, key=f"active_{tid}"
                    )

                kw_raw = st.text_input(
                    "Mots-clés déclencheurs (séparés par virgule)",
                    value=", ".join(t.get("keywords", [])),
                    key=f"kw_{tid}"
                )

                ca, cb, cc = st.columns(3)
                with ca:
                    if st.button("Sauvegarder", key=f"save_{tid}", use_container_width=True, type="primary"):
                        valid_new, errs_new = validate_sql(new_sql)
                        if not valid_new:
                            st.session_state.msg = ("error", "SQL invalide : " + " | ".join(errs_new))
                        else:
                            st.session_state.data["templates"][tid].update({
                                "description": new_desc,
                                "intent":      new_intent,
                                "sql":         new_sql,
                                "active":      new_active,
                                "keywords":    [k.strip() for k in kw_raw.split(",") if k.strip()],
                                "updated_at":  datetime.now().isoformat(),
                            })
                            save_templates(st.session_state.data)
                            st.session_state.msg = ("success", f"✓ Template `{tid}` mis à jour.")
                        st.rerun()
                with cb:
                    toggle_label = "⏸ Désactiver" if active else "▶ Activer"
                    if st.button(toggle_label, key=f"toggle_{tid}", use_container_width=True):
                        st.session_state.data["templates"][tid]["active"] = not active
                        save_templates(st.session_state.data)
                        st.session_state.msg = ("success", f"Template `{tid}` {'désactivé' if active else 'activé'}.")
                        st.rerun()
                with cc:
                    if st.button("✖ Supprimer", key=f"del_{tid}", use_container_width=True):
                        del st.session_state.data["templates"][tid]
                        save_templates(st.session_state.data)
                        st.session_state.msg = ("warning", f"⚠️ Template `{tid}` supprimé.")
                        st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Nouveau template
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Nouveau template":

    st.subheader("Créer un nouveau template SQL")
    st.markdown("Tous les templates sont validés (SELECT-only) avant sauvegarde.")
    st.markdown("---")

    with st.form("new_template_form"):
        c1, c2 = st.columns(2)
        with c1:
            new_id = st.text_input(
                "Identifiant unique *",
                placeholder="ex: factures_par_periode",
                help="Clé JSON unique, pas d'espaces."
            )
            new_intent = st.text_input(
                "Intent NLP *",
                placeholder="ex: get_invoices_by_date"
            )
            new_desc = st.text_input(
                "Description courte *",
                placeholder="ex: Factures entre deux dates avec total HT/TTC"
            )
        with c2:
            new_keywords_raw = st.text_area(
                "Mots-clés déclencheurs (un par ligne)",
                placeholder="facture\nentre\ndu ... au\npériode",
                height=120
            )
            new_active = st.toggle("Actif dès la création", value=True)

        new_sql = st.text_area(
            "Requête SQL * (utilise :param pour les paramètres)",
            height=160,
            placeholder=(
                "SELECT f.ref, s.nom AS client,\n"
                "       f.total_ht, f.total_ttc\n"
                "FROM m38h_facture f\n"
                "JOIN m38h_societe s ON f.fk_soc = s.rowid\n"
                "WHERE f.datef BETWEEN :date_debut AND :date_fin\n"
                "  AND f.entity = 1\n"
                "LIMIT :limit"
            )
        )

        st.markdown("---")
        submitted = st.form_submit_button("✓ Valider et créer", type="primary", use_container_width=True)

    if submitted:
        errors_form = []
        if not new_id.strip():
            errors_form.append("L'identifiant est obligatoire.")
        if " " in new_id.strip():
            errors_form.append("L'identifiant ne doit pas contenir d'espaces.")
        if new_id.strip() in st.session_state.data.get("templates", {}):
            errors_form.append(f"L'identifiant `{new_id}` existe déjà.")
        if not new_sql.strip():
            errors_form.append("La requête SQL est obligatoire.")

        sql_valid, sql_errors = validate_sql(new_sql)
        errors_form.extend(sql_errors)

        if errors_form:
            for e in errors_form:
                st.markdown(f'<div class="security-warning">{e}</div>', unsafe_allow_html=True)
        else:
            keywords = [k.strip() for k in new_keywords_raw.splitlines() if k.strip()]
            params   = extract_params(new_sql)

            st.session_state.data.setdefault("templates", {})[new_id.strip()] = {
                "intent":      new_intent.strip(),
                "description": new_desc.strip(),
                "sql":         new_sql.strip(),
                "params":      params,
                "keywords":    keywords,
                "active":      new_active,
                "created_at":  datetime.now().isoformat(),
                "updated_at":  datetime.now().isoformat(),
            }
            save_templates(st.session_state.data)
            st.session_state.msg = ("success", f"✓ Template `{new_id.strip()}` créé avec succès !")
            st.rerun()

    with st.expander("⌘ Voir la structure JSON d'un template"):
        example = {
            "intent":      "get_invoices_by_date",
            "description": "Factures entre deux dates avec total HT/TTC",
            "sql":         "SELECT f.ref, s.nom AS client, f.total_ht, f.total_ttc FROM m38h_facture f JOIN m38h_societe s ON f.fk_soc = s.rowid WHERE f.datef BETWEEN :date_debut AND :date_fin AND f.entity = 1 LIMIT :limit",
            "params":      ["date_debut", "date_fin", "limit"],
            "keywords":    ["facture", "entre", "période"],
            "active":      True,
            "created_at":  "2026-04-10T09:00:00",
            "updated_at":  "2026-04-10T09:00:00"
        }
        st.json(example)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 3 — Tester un template
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Tester un template":

    st.subheader("Tester un template (simulation sans DB)")
    st.markdown("Injecte des valeurs dans les paramètres et visualise le SQL final.")
    st.markdown("---")

    templates = st.session_state.data.get("templates", {})
    if not templates:
        st.info("Aucun template disponible. Crée-en un d'abord.")
    else:
        active_templates = {k: v for k, v in templates.items() if v.get("active", True)}
        choices = {f"{v.get('intent', '—')} ({k})": k for k, v in active_templates.items()}

        selected_label = st.selectbox("Choisir un template", list(choices.keys()))
        selected_id    = choices[selected_label]
        t              = templates[selected_id]

        st.markdown(f"**Description :** {t.get('description', '—')}")
        formatted_sql = sqlparse.format(t.get("sql", ""), reindent=True, keyword_case='upper')
        st.markdown(f'<div class="sql-block"><pre>{formatted_sql}</pre></div>', unsafe_allow_html=True)

        params = extract_params(t.get("sql", ""))
        if not params:
            st.info("Ce template n'a pas de paramètres.")
        else:
            st.markdown("---")
            st.markdown("**Valeurs des paramètres :**")
            param_values = {}
            cols = st.columns(min(len(params), 3))
            for i, p in enumerate(params):
                with cols[i % 3]:
                    if "date" in p.lower():
                        val = st.date_input(f":{p}", key=f"test_{p}")
                        param_values[p] = str(val)
                    elif "limit" in p.lower():
                        val = st.number_input(f":{p}", value=100, min_value=1, max_value=500, key=f"test_{p}")
                        param_values[p] = str(int(val))
                    else:
                        val = st.text_input(f":{p}", key=f"test_{p}")
                        param_values[p] = val

            if st.button("▶ Générer SQL avec valeurs", type="primary"):
                sql_result = t.get("sql", "")
                for p, v in param_values.items():
                    sql_result = sql_result.replace(f":{p}", f"'{v}'")

                sql_result_formatted = sqlparse.format(sql_result, reindent=True, keyword_case='upper')

                st.markdown("**SQL généré :**")
                st.code(sql_result_formatted, language="sql")
                st.markdown(
        '<div class="security-ok"><i class="fa-regular fa-circle-check"></i> SQL prêt à l\'exécution (simulation — non connecté à la DB)</div>',
        unsafe_allow_html=True
    )

# ════════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Statistiques templates
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Statistiques":

    st.subheader("Statistiques des templates")
    st.markdown("---")

    stats     = get_stats(st.session_state.data)
    templates = st.session_state.data.get("templates", {})

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (stats["total"],    "Templates total"),
        (stats["active"],   "Actifs"),
        (stats["inactive"], "Inactifs"),
        (stats["version"],  "Version whitelist"),
    ]
    for col, (val, label) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{val}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    if templates:
        st.markdown("**Récapitulatif des templates :**")
        rows = []
        for tid, t in templates.items():
            params = extract_params(t.get("sql", ""))
            valid, _ = validate_sql(t.get("sql", ""))
            rows.append({
                "ID":          tid,
                "Intent":      t.get("intent", "—"),
                "Paramètres":  ", ".join(params) if params else "—",
                "Actif":       "✅" if t.get("active", True) else "⏸",
                "SQL valide":  "✅" if valid else "❌",
                "Créé le":     t.get("created_at", "—")[:10],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.download_button(
            label="↓ Exporter templates.json",
            data=json.dumps(st.session_state.data, ensure_ascii=False, indent=2),
            file_name=f"templates_v{stats['version']}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.info("Aucun template à afficher.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Analytics hybride (renommé et fusionné)
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Analytics (hybride)":

    st.subheader("Analytics - Moteur hybride NL2SQL")
    st.caption("Statistiques sur les requêtes traitées par le moteur hybride (port 8001)")

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("⟳ Actualiser", use_container_width=True):
            st.rerun()

    data = call_hybrid_api("/analytics")

    if not data:
        st.error("⚠️ API hybride inaccessible. Vérifiez que le serveur tourne sur le port 8001.")
        st.code("uvicorn hybrid_router:app --host 0.0.0.0 --port 8001 --reload", language="bash")
    elif data.get("empty"):
        st.info("Aucune donnée disponible. Posez des questions via l'API hybride d'abord.")
    else:
        # ── Métriques principales ─────────────────────────────────────────────
        st.markdown("### Vue d'ensemble")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total requêtes",    data.get("total_requests", 0))
        c2.metric("Taux appel LLM",    f"{data.get('llm_call_rate_pct', 0)}%")
        c3.metric("Template hit rate", f"{data.get('template_hit_rate_pct', 0)}%")
        c4.metric("Taux erreur",       f"{data.get('error_rate_pct', 0)}%")

        st.markdown("---")

        # ── Latence ───────────────────────────────────────────────────────────
        st.markdown("### Latence (ms)")
        lat = data.get("latency", {})
        lc1, lc2, lc3, lc4 = st.columns(4)
        lc1.metric("Moyenne",  f"{lat.get('mean_ms', 0):.0f} ms")
        lc2.metric("Médiane",  f"{lat.get('median_ms', 0):.0f} ms")
        lc3.metric("P95",      f"{lat.get('p95_ms', 0):.0f} ms")
        lc4.metric("P99",      f"{lat.get('p99_ms', 0):.0f} ms")

        st.markdown("---")

        col1, col2 = st.columns(2)

        # ── Distribution des modes ────────────────────────────────────────────
        with col1:
            st.markdown("### Distribution des modes")
            modes = data.get("mode_distribution", {})
            if modes:
                colors_map = {
                    "template":       "#4CAF50",
                    "llm_router":     "#2196F3",
                    "llm_sql":        "#FF9800",
                    "fallback_error": "#e53935",
                }
                bar_colors = [colors_map.get(k, "#9E9E9E") for k in modes.keys()]

                fig, ax = plt.subplots(figsize=(5, 3))
                ax.bar(list(modes.keys()), list(modes.values()),
                       color=bar_colors, alpha=0.85)
                ax.set_ylabel("Nb requêtes")
                ax.set_title("Répartition par mode de traitement")
                ax.tick_params(axis="x", rotation=20)
                for i, (k, v) in enumerate(modes.items()):
                    ax.text(i, v + 0.3, str(v), ha="center", fontsize=9, fontweight="bold")
                fig.tight_layout()
                st.pyplot(fig)
                plt.close(fig)

                # Tableau détaillé
                df_modes = pd.DataFrame([
                    {"Mode": k, "Nb requêtes": v, "% du total": f"{v/data['total_requests']*100:.1f}%"}
                    for k, v in modes.items()
                ])
                st.dataframe(df_modes, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune donnée de mode disponible.")

        # ── Top intents ───────────────────────────────────────────────────────
        with col2:
            st.markdown("### Top 10 intents détectés")
            intents = data.get("top_intents", {})
            if intents:
                fig2, ax2 = plt.subplots(figsize=(5, 3))
                labels = list(intents.keys())
                values = list(intents.values())
                ax2.barh(labels, values, color="#38bdf8", alpha=0.85)
                ax2.set_xlabel("Nb requêtes")
                ax2.set_title("Intents les plus fréquents")
                for i, v in enumerate(values):
                    ax2.text(v + 0.1, i, str(v), va="center", fontsize=9)
                fig2.tight_layout()
                st.pyplot(fig2)
                plt.close(fig2)

                df_intents = pd.DataFrame([
                    {"Intent": k, "Nb": v}
                    for k, v in intents.items()
                ])
                st.dataframe(df_intents, use_container_width=True, hide_index=True)
            else:
                st.info("Aucun intent enregistré.")

        st.markdown("---")

        # ── Top questions ─────────────────────────────────────────────────────
        st.markdown("### Top 10 questions les plus posées")
        top_q = data.get("top_questions", {})
        if top_q:
            df_topq = pd.DataFrame([
                {"Question": q[:90] + ("…" if len(q) > 90 else ""), "Nb": n}
                for q, n in top_q.items()
            ])
            st.dataframe(df_topq, use_container_width=True, hide_index=True)
        else:
            st.info("Aucune question enregistrée.")

        st.markdown("---")

        # ── Lien vers les logs bruts ──────────────────────────────────────────
        logs_path = "logs/hybrid_requests.jsonl"
        if os.path.exists(logs_path):
            with open(logs_path, "r", encoding="utf-8") as f:
                raw_logs = f.read()
            st.download_button(
                label="↓ Exporter les logs bruts (JSONL)",
                data=raw_logs.encode("utf-8"),
                file_name=f"hybrid_logs_{datetime.now().strftime('%Y%m%d')}.jsonl",
                mime="application/json",
                use_container_width=True,
            )


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 6 — Cache & Audit (nouvel onglet déplacé depuis app.py)
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Cache & Audit":

    st.markdown("### Monitoring - Cache & Audit")
    c1, c2 = st.columns(2)

    # ──────────────────── COLONNE CACHE ────────────────────
    with c1:
        st.markdown("#### Cache")
        if st.button("⟳ Actualiser", key="btn_cache_refresh"):
            stats = call_api_endpoint("/cache/stats")
            if stats:
                st.metric("Taille", f"{stats.get('size', 0)} / {stats.get('max_size', 100)}")
                st.metric("Hit rate", f"{stats.get('hit_rate', 0)}%")
                col_a, col_b = st.columns(2)
                col_a.metric("Hits",   stats.get("hits", 0))
                col_b.metric("Misses", stats.get("misses", 0))
                by_tpl = stats.get("by_template", {})
                if by_tpl:
                    st.dataframe(pd.DataFrame(list(by_tpl.items()),
                                              columns=["Template", "Entrées"]))
            else:
                st.info("API non disponible.")
        if st.button("✖ Vider le cache", type="secondary", key="btn_cache_clear"):
            call_api_endpoint("/cache/clear", method="POST")
            st.success("Cache vidé.")

        # ── Top questions (déplacé ici) ──
        # Récupération des données d'audit
        audit = call_api_endpoint("/audit")
        if audit and "total_requests" in audit:
            top_q = audit.get("top_questions", {})
            if top_q:
                st.markdown("**Top questions**")

                # Suppression de la variante sans majuscule
                if "chiffre d affaires de janvier 2026" in top_q:
                    del top_q["chiffre d affaires de janvier 2026"]

                # Dédoublonnage (normalisation)
                import unicodedata
                def normalize_q(text: str) -> str:
                    text = text.strip().lower()
                    text = unicodedata.normalize("NFD", text)
                    text = text.encode("ascii", "ignore").decode("utf-8")
                    return text

                merged = {}
                for q_text, cnt in top_q.items():
                    key = normalize_q(q_text)
                    if key not in merged:
                        merged[key] = {"display": q_text, "count": cnt}
                    else:
                        merged[key]["count"] += cnt
                        current = merged[key]["display"]
                        if q_text[0].isupper() and not current[0].isupper():
                            merged[key]["display"] = q_text
                        elif len(q_text) > len(current):
                            merged[key]["display"] = q_text

                sorted_merged = sorted(merged.values(), key=lambda x: -x["count"])

                header = (
                    '<div class="scroll-table">'
                    '<div class="scroll-table-header">'
                    '<span class="col-rank">#</span>'
                    '<span class="col-ques">Question</span>'
                    '<span class="col-count">Nb</span>'
                    '</div>'
                )
                rows_html = ""
                for rank, item in enumerate(sorted_merged, 1):
                    q_esc = item["display"][:70] + ("…" if len(item["display"]) > 70 else "")
                    rows_html += (
                        f'<div class="scroll-table-row">'
                        f'<span class="col-rank">{rank}</span>'
                        f'<span class="col-ques">{q_esc}</span>'
                        f'<span class="col-count">{item["count"]}</span>'
                        f'</div>'
                    )
                st.markdown(header + rows_html + "</div>", unsafe_allow_html=True)
        else:
            st.info("Données d'audit non disponibles.")

    # ──────────────────── COLONNE AUDIT ────────────────────
    with c2:
        st.markdown("#### Audit")
        audit = call_api_endpoint("/audit")
        if audit and "total_requests" in audit:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total requêtes", audit.get("total_requests", 0))
            m2.metric("Succès",         audit.get("success_count", 0))
            m3.metric("Erreurs",        audit.get("error_count", 0))
            m4.metric("Rejetées",       audit.get("rejected_count", 0))

            st.markdown("**Latence (ms)**")
            latency = audit.get("latency", {})
            lc1, lc2, lc3, lc4 = st.columns(4)
            lc1.metric("Moyenne", f"{latency.get('mean_ms', 0):.0f} ms")
            lc2.metric("Médiane", f"{latency.get('median_ms', 0):.0f} ms")
            lc3.metric("P95",     f"{latency.get('p95_ms', 0):.0f} ms")
            lc4.metric("P99",     f"{latency.get('p99_ms', 0):.0f} ms")

            st.markdown("**Cache**")
            cache = audit.get("cache", {})
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Hit rate", f"{cache.get('hit_rate_pct', 0):.1f}%")
            cc2.metric("Hits",     cache.get("cache_hits", 0))
            cc3.metric("Misses",   cache.get("cache_misses", 0))

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
                st.success("✓ Aucune alerte — système nominal")

            trends = audit.get("trends", {})
            if trends.get("recent_24h", {}).get("count", 0) > 0:
                st.markdown("**Tendance 24h**")
                delta = trends.get("delta_pct", 0)
                trend = trends.get("trend", "stable")
                tc1, tc2 = st.columns(2)
                tc1.metric(
                    "Requêtes dernières 24h",
                    trends["recent_24h"]["count"],
                    delta=f"{trends['recent_24h']['mean_ms']:.0f} ms moy."
                )
                tc2.metric(
                    "Tendance latence",
                    trend.capitalize(),
                    delta=f"{delta:+.1f}%"
                )
        else:
            st.info("API non disponible.")

    # ── Feedback utilisateurs (reste en bas, sous les deux colonnes) ──
    st.markdown("---")
    st.markdown("#### Feedback utilisateurs")
    # ... (le reste du code feedback inchangé)
    
    FEEDBACK_FILE_ADMIN = "logs/feedback.jsonl"

    def load_feedbacks_admin() -> list:
        if not os.path.exists(FEEDBACK_FILE_ADMIN):
            return []
        items = []
        with open(FEEDBACK_FILE_ADMIN, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except Exception:
                        pass
        return items    

    def save_feedbacks_admin(items: list):
        os.makedirs("logs", exist_ok=True)
        with open(FEEDBACK_FILE_ADMIN, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Initialisation du state pour suppression
    if "delete_fb_idx_admin" not in st.session_state:
        st.session_state.delete_fb_idx_admin = -1

    # Traitement suppression
    if st.session_state.delete_fb_idx_admin >= 0:
        feedbacks_tmp = load_feedbacks_admin()
        idx = st.session_state.delete_fb_idx_admin
        if 0 <= idx < len(feedbacks_tmp):
            feedbacks_tmp.pop(idx)
            save_feedbacks_admin(feedbacks_tmp)
        st.session_state.delete_fb_idx_admin = -1
        st.rerun()

    feedbacks = load_feedbacks_admin()

    if not feedbacks:
        st.info("Aucun feedback enregistré. Utilisez ✓/✗ dans l'onglet Chatbot.")
    else:
        pos = sum(1 for f in feedbacks if f.get("rating") == "positive")
        neg = sum(1 for f in feedbacks if f.get("rating") == "negative")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total",       len(feedbacks))
        m2.metric("✓ Positifs", pos)
        m3.metric("✗ Négatifs", neg)

        df_fb = pd.DataFrame(feedbacks)

        def df_to_csv_bytes_fb(df: pd.DataFrame) -> bytes:
            return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

        st.download_button("⬇ Exporter tout en CSV",
                           data=df_to_csv_bytes_fb(df_fb),
                           file_name="feedbacks.csv", mime="text/csv",
                           key="btn_export_fb_admin")

        st.markdown("##### Liste des feedbacks")
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

        for i, fb in enumerate(feedbacks):
            icon    = "✓" if fb.get("rating") == "positive" else "✗"
            ts      = fb.get("timestamp", "")[:16].replace("T", " ")
            q_text  = fb.get("question", "")[:60]
            comment = (fb.get("comment", "") or "—")[:50]

            rc = st.columns([0.06, 0.13, 0.40, 0.30, 0.11])
            rc[0].markdown(f"<div style='text-align:center;font-size:1rem;'>{icon}</div>",
                           unsafe_allow_html=True)
            rc[1].caption(ts)
            rc[2].markdown(f"<small style='color:#111;'>{q_text}</small>",
                           unsafe_allow_html=True)
            rc[3].markdown(f"<small style='color:#666;font-style:italic;'>{comment}</small>",
                           unsafe_allow_html=True)
            if rc[4].button("🗑", key=f"del_admin_{i}", help="Supprimer ce feedback"):
                st.session_state.delete_fb_idx_admin = i
                st.rerun()

        st.markdown("")
        if st.button("✖ Supprimer tous les feedbacks", type="secondary", key="btn_delete_all_fb_admin"):
            save_feedbacks_admin([])
            st.success("Tous les feedbacks supprimés.")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════════
# PAGE 7 — Analytics (requêtes) - déplacé depuis app.py
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Analytics (requêtes)":

    st.markdown("### Analytics - Requêtes utilisateurs")
    st.caption("Analyse comportementale basée sur les logs de production")

    data = call_api_endpoint("/analytics")

    if not data or data.get("empty"):
        st.info("Aucune donnée disponible. Posez quelques questions d'abord.")
    else:
        total = data.get("total_requests", 0)
        sr    = data.get("success_rate", 0)
        gmean = data.get("global_mean_ms", 0)
        cache = data.get("cache", {})

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total requêtes", total)
        r2.metric("Taux de succès", f"{sr}%")
        r3.metric("Latence moy.",   f"{gmean:.0f} ms")
        r4.metric("Cache hit rate", f"{cache.get('hit_rate', 0)}%")

        st.markdown("---")
        col_left, col_right = st.columns(2)

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
                ax1.barh(labels, values, color=colors[:len(labels)], alpha=0.85)
                ax1.set_xlabel("Nb requêtes")
                ax1.set_title("Templates les plus utilisés")
                for i, v in enumerate(values):
                    ax1.text(v + 0.3, i, str(v), va="center", fontsize=9)
                fig1.tight_layout()
                st.pyplot(fig1)
                plt.close(fig1)

        with col_right:
            st.markdown("#### Volume journalier (7 derniers jours)")
            daily = data.get("daily_volume", {})
            if daily:
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                days   = list(daily.keys())
                counts = list(daily.values())
                ax2.plot(days, counts, color="#2196F3", marker="o", linewidth=2, markersize=6)
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

        with col_l2:
            st.markdown("#### Latence par template (sans cache)")
            lat_tpl = data.get("latency_by_template", {})
            if lat_tpl:
                fig3, ax3 = plt.subplots(figsize=(6, 4))
                tpls  = [k.replace("get_", "") for k in lat_tpl.keys()]
                means = [v["mean"] for v in lat_tpl.values()]
                p95s  = [v["p95"]  for v in lat_tpl.values()]
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

        with col_r2:
            st.markdown("#### Impact du cache sur la latence")
            cold_m = cache.get("cold_mean", 0)
            warm_m = cache.get("warm_mean", 0)
            if cold_m > 0 or warm_m > 0:
                fig4, ax4 = plt.subplots(figsize=(6, 4))
                cats = ["Sans cache\n(cold)", "Avec cache\n(warm)"]
                vals = [cold_m, warm_m]
                bars = ax4.bar(cats, vals, color=["#FF9800", "#4CAF50"], alpha=0.85, width=0.4)
                ax4.set_ylabel("Latence moy. (ms)")
                ax4.set_title("Comparaison latence cache hit vs miss")
                for bar, val in zip(bars, vals):
                    ax4.text(bar.get_x() + bar.get_width() / 2,
                             bar.get_height() + 5,
                             f"{val:.0f} ms",
                             ha="center", fontsize=11, fontweight="bold")
                if cold_m > 0 and warm_m < cold_m:
                    gain = round((1 - warm_m / cold_m) * 100, 1)
                    ax4.set_title(f"Gain cache : {gain}% de réduction de latence", fontsize=11)
                fig4.tight_layout()
                st.pyplot(fig4)
                plt.close(fig4)
            else:
                st.info("Pas encore de données cache warm.")

        st.markdown("---")

        st.markdown("#### Top 10 questions les plus posées")
        top_q = data.get("top_questions", {})
        if top_q:
            df_topq = pd.DataFrame([
                {"Question": q[:80], "Nb": n}
                for q, n in top_q.items()
            ])
            st.dataframe(df_topq, use_container_width=True, hide_index=True)

        st.markdown("#### Taux de succès par template")
        sbt = data.get("success_by_template", {})
        if sbt:
            df_sbt = pd.DataFrame([
                {"Template": k.replace("get_", ""), "Taux succès (%)": v}
                for k, v in sorted(sbt.items(), key=lambda x: -x[1])
            ])
            st.dataframe(df_sbt, use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 8 — Paramètres
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Paramètres":

    st.subheader("Paramètres de la whitelist")
    st.markdown("---")

    st.markdown("**Version de la whitelist**")
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        new_version = st.text_input(
            "Version",
            value=st.session_state.data.get("version", "1.0"),
            label_visibility="collapsed"
        )
    with col_v2:
        if st.button("Mettre à jour", use_container_width=True):
            st.session_state.data["version"] = new_version
            save_templates(st.session_state.data)
            st.session_state.msg = ("success", f"Version mise à jour : {new_version}")
            st.rerun()

    st.markdown("---")
    st.markdown("**Tables autorisées (whitelist)**")
    st.code("\n".join(ALLOWED_TABLES), language="text")
    st.info("Pour modifier les tables autorisées, édite `ALLOWED_TABLES` dans `admin_templates.py`.")

    st.markdown("---")
    st.markdown("**Mots-clés SQL interdits**")
    st.code(" | ".join(FORBIDDEN_KEYWORDS), language="text")

    st.markdown("---")

    # ── Statut API hybride ────────────────────────────────────────────────────
    st.markdown("**Statut du moteur hybride (port 8001)**")
    health = call_hybrid_api("/health")

# Calculer les vrais chiffres depuis les templates en session
    templates_data = st.session_state.data.get("templates", {})
    total_actifs = sum(1 for t in templates_data.values() if t.get("active", True))
    total_charges = len(templates_data)

    if health and health.get("status") == "ok":
        st.markdown(
        f'<div style="background:#052e16;border:1px solid #166534;border-left:3px solid #4ade80;'
        f'border-radius:8px;padding:12px 16px;color:#86efac;font-size:0.83rem;">'
        f'<i class="fa-regular fa-circle-check" style="color:#86efac;"></i> API hybride opérationnelle — '
        f'{total_actifs} templates actifs / '
        f'{total_charges} chargés</div>',
        unsafe_allow_html=True
    )
    else:
        st.markdown(
        '<div style="background:#2d1b00;border:1px solid #92400e;border-left:3px solid #f59e0b;'
        'border-radius:8px;padding:12px 16px;color:#fcd34d;font-size:0.83rem;">'
        '<i class="fa-solid fa-triangle-exclamation" style="color:#fcd34d;"></i> API hybride inaccessible sur le port 8001</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("**Importer un fichier templates.json**")
    uploaded = st.file_uploader("Choisir un fichier JSON", type=["json"])
    if uploaded:
        try:
            imported = json.load(uploaded)
            if "templates" not in imported:
                st.error("Fichier invalide : clé `templates` manquante.")
            else:
                preview_count = len(imported["templates"])
                st.success(f"Fichier valide — {preview_count} template(s) détecté(s).")
                if st.button("⬆️ Importer et remplacer", type="primary"):
                    st.session_state.data = imported
                    save_templates(st.session_state.data)
                    st.session_state.msg = ("success", "✓ Templates importés avec succès.")
                    st.rerun()
        except json.JSONDecodeError:
            st.error("Fichier JSON invalide.")

    st.markdown("---")
    with st.expander("🚨 Zone dangereuse"):
        st.warning("Supprimer tous les templates est irréversible.")
        if st.button("🗑 Vider tous les templates", type="secondary"):
            st.session_state.data["templates"] = {}
            save_templates(st.session_state.data)
            st.session_state.msg = ("warning", "⚠️ Tous les templates ont été supprimés.")
            st.rerun()