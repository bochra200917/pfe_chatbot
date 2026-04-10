"""
Interface Admin — Gestion des Templates SQL
Chatbot Dolibarr (PFE Bochra Ben Yedder)

Lancement : streamlit run admin_templates.py
"""

import streamlit as st
import json
import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import requests as req
from datetime import datetime

matplotlib.use("Agg")

# ─── Configuration page ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Admin — Templates SQL",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS personnalisé ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Sora', sans-serif;
    }
    code, pre, .stCode {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #94a3b8 !important;
    }

    /* Header principal */
    .admin-header {
        background: linear-gradient(135deg, #0f172a, #1e3a5f);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 24px 32px;
        margin-bottom: 28px;
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .admin-header h1 {
        color: #f1f5f9;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .admin-header p {
        color: #64748b;
        margin: 4px 0 0 0;
        font-size: 0.85rem;
    }

    /* Cards de stats */
    .stat-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #38bdf8;
        font-family: 'JetBrains Mono', monospace;
    }
    .stat-label {
        color: #94a3b8;
        font-size: 0.8rem;
        margin-top: 4px;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .badge-active   { background: #052e16; color: #4ade80; border: 1px solid #166534; }
    .badge-inactive { background: #1c1917; color: #a8a29e; border: 1px solid #44403c; }
    .badge-select   { background: #0c1e3d; color: #60a5fa; border: 1px solid #1e3a5f; }

    /* Bloc SQL */
    .sql-block {
        background: #0f172a;
        border: 1px solid #1e3a5f;
        border-left: 3px solid #38bdf8;
        border-radius: 8px;
        padding: 14px 18px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #93c5fd;
        white-space: pre-wrap;
        margin: 8px 0;
        line-height: 1.6;
    }

    /* Alerte sécurité */
    .security-warning {
        background: #2d1b00;
        border: 1px solid #92400e;
        border-left: 3px solid #f59e0b;
        border-radius: 8px;
        padding: 12px 16px;
        color: #fcd34d;
        font-size: 0.83rem;
        margin: 8px 0;
    }
    .security-ok {
        background: #052e16;
        border: 1px solid #166534;
        border-left: 3px solid #4ade80;
        border-radius: 8px;
        padding: 12px 16px;
        color: #86efac;
        font-size: 0.83rem;
        margin: 8px 0;
    }

    /* Boutons custom */
    .stButton > button {
        border-radius: 8px;
        font-family: 'Sora', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        transition: all 0.2s ease;
    }

    /* Expander styling */
    [data-testid="stExpander"] {
        border: 1px solid #334155;
        border-radius: 10px;
        background: #1e293b;
    }

    /* Version badge */
    .version-tag {
        background: #172554;
        color: #93c5fd;
        border: 1px solid #1e40af;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.72rem;
        font-family: 'JetBrains Mono', monospace;
    }

    hr { border-color: #1e293b; }
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
    "m38h_facture", "m38h_facturedet", "m38h_commande", "m38h_commandedet",
    "m38h_societe", "m38h_socpeople", "m38h_product", "m38h_product_stock",
    "m38h_stock_mouvement", "m38h_entrepot", "m38h_paiement",
    "m38h_paiement_facture", "m38h_accounting_account",
    "m38h_accounting_bookkeeping", "m38h_bank", "m38h_bank_account",
    "m38h_user", "m38h_salary", "m38h_projet", "m38h_projet_task",
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
        errors.append("❌ La requête doit commencer par SELECT.")

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(r'\b' + kw + r'\b', sql_upper):
            errors.append(f"❌ Mot-clé interdit détecté : `{kw}`")

    if "LIMIT" not in sql_upper:
        errors.append("⚠️  Aucun LIMIT détecté — ajoute LIMIT :limit pour sécuriser.")

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
    """Appelle l'API hybride (port 8001) et retourne le JSON."""
    try:
        r = req.get(f"{HYBRID_API_URL}{endpoint}", timeout=5)
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
    st.markdown("### 🛠️ Admin Panel")
    st.markdown("---")
    page = st.radio(
        "Navigation",
        [
            "📋 Liste des templates",
            "➕ Nouveau template",
            "🔍 Tester un template",
            "📊 Statistiques",
            "📈 Analytics hybride",
            "⚙️ Paramètres",
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
    if st.button("🔄 Recharger depuis fichier", use_container_width=True):
        st.session_state.data = load_templates()
        st.rerun()


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="admin-header">
    <div>
        <h1>🛠️ Interface Admin — Templates SQL</h1>
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
# PAGE 1 — Liste des templates
# ════════════════════════════════════════════════════════════════════════════════
if page == "📋 Liste des templates":

    templates = st.session_state.data.get("templates", {})

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        search = st.text_input("🔎 Rechercher", placeholder="nom, intent, mot-clé SQL…")
    with col_f2:
        filter_status = st.selectbox("Statut", ["Tous", "Actifs", "Inactifs"])
    with col_f3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Tout sauvegarder", use_container_width=True, type="primary"):
            save_templates(st.session_state.data)
            st.session_state.msg = ("success", "✅ Templates sauvegardés avec succès.")
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
        st.info("Aucun template trouvé. Crée-en un depuis **➕ Nouveau template**.")
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
                        '<div class="security-ok">✔ Requête valide (SELECT-only, pas de mots interdits)</div>',
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
                    if st.button("💾 Sauvegarder", key=f"save_{tid}", use_container_width=True, type="primary"):
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
                            st.session_state.msg = ("success", f"✅ Template `{tid}` mis à jour.")
                        st.rerun()
                with cb:
                    toggle_label = "⏸ Désactiver" if active else "▶ Activer"
                    if st.button(toggle_label, key=f"toggle_{tid}", use_container_width=True):
                        st.session_state.data["templates"][tid]["active"] = not active
                        save_templates(st.session_state.data)
                        st.session_state.msg = ("success", f"Template `{tid}` {'désactivé' if active else 'activé'}.")
                        st.rerun()
                with cc:
                    if st.button("🗑️ Supprimer", key=f"del_{tid}", use_container_width=True):
                        del st.session_state.data["templates"][tid]
                        save_templates(st.session_state.data)
                        st.session_state.msg = ("warning", f"⚠️ Template `{tid}` supprimé.")
                        st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 2 — Nouveau template
# ════════════════════════════════════════════════════════════════════════════════
elif page == "➕ Nouveau template":

    st.subheader("➕ Créer un nouveau template SQL")
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
        submitted = st.form_submit_button("✅ Valider et créer", type="primary", use_container_width=True)

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
            st.session_state.msg = ("success", f"✅ Template `{new_id.strip()}` créé avec succès !")
            st.rerun()

    with st.expander("📄 Voir la structure JSON d'un template"):
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
elif page == "🔍 Tester un template":

    st.subheader("🔍 Tester un template (simulation sans DB)")
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
        st.markdown(
            f'<div class="sql-block">{t.get("sql", "")}</div>',
            unsafe_allow_html=True
        )

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

                st.markdown("**SQL généré :**")
                st.markdown(
                    f'<div class="sql-block">{sql_result}</div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    '<div class="security-ok">✔ SQL prêt à l\'exécution (simulation — non connecté à la DB)</div>',
                    unsafe_allow_html=True
                )
                st.code(sql_result, language="sql")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 4 — Statistiques templates
# ════════════════════════════════════════════════════════════════════════════════
elif page == "📊 Statistiques":

    st.subheader("📊 Statistiques des templates")
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
            label="📥 Exporter templates.json",
            data=json.dumps(st.session_state.data, ensure_ascii=False, indent=2),
            file_name=f"templates_v{stats['version']}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
        st.info("Aucun template à afficher.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 5 — Analytics hybride (NOUVEAU)
# ════════════════════════════════════════════════════════════════════════════════
elif page == "📈 Analytics hybride":

    st.subheader("📈 Analytics — Moteur hybride NL2SQL")
    st.caption("Statistiques sur les requêtes traitées par le moteur hybride (port 8001)")

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Actualiser", use_container_width=True):
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
                label="📥 Exporter les logs bruts (JSONL)",
                data=raw_logs.encode("utf-8"),
                file_name=f"hybrid_logs_{datetime.now().strftime('%Y%m%d')}.jsonl",
                mime="application/json",
                use_container_width=True,
            )


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 6 — Paramètres
# ════════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Paramètres":

    st.subheader("⚙️ Paramètres de la whitelist")
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
    if health and health.get("status") == "ok":
        st.markdown(
            f'<div style="background:#052e16;border:1px solid #166534;border-left:3px solid #4ade80;'
            f'border-radius:8px;padding:12px 16px;color:#86efac;font-size:0.83rem;">'
            f'✔ API hybride opérationnelle — '
            f'{health.get("active_templates", 0)} templates actifs / '
            f'{health.get("templates_loaded", 0)} chargés</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div style="background:#2d1b00;border:1px solid #92400e;border-left:3px solid #f59e0b;'
            'border-radius:8px;padding:12px 16px;color:#fcd34d;font-size:0.83rem;">'
            '⚠️ API hybride inaccessible sur le port 8001</div>',
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
                    st.session_state.msg = ("success", "✅ Templates importés avec succès.")
                    st.rerun()
        except json.JSONDecodeError:
            st.error("Fichier JSON invalide.")

    st.markdown("---")
    with st.expander("🚨 Zone dangereuse"):
        st.warning("Supprimer tous les templates est irréversible.")
        if st.button("🗑️ Vider tous les templates", type="secondary"):
            st.session_state.data["templates"] = {}
            save_templates(st.session_state.data)
            st.session_state.msg = ("warning", "⚠️ Tous les templates ont été supprimés.")
            st.rerun()