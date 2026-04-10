# scripts/latency_by_template.py
# Breakdown détaillé des temps de réponse par template
# Complète memory_analysis.py avec une analyse focalisée sur la latence
#
# Usage :
#   python scripts/latency_by_template.py
#   python scripts/latency_by_template.py --csv reports/memory_detail_TIMESTAMP.csv
#
# pip install requests pandas matplotlib psutil

import argparse
import time
import os
import tracemalloc
from datetime import datetime

import requests
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
API_URL  = "http://localhost:8000/ask"
API_USER = "admin"
API_PASS = "1234"
OUTPUT_DIR = "reports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────
# Questions par template — 5 variantes chacune
# pour une distribution statistiquement robuste
# ─────────────────────────────────────────────
QUESTIONS_BY_TEMPLATE = {
    "get_factures_between": [
        "factures entre 2026-01-01 et 2026-01-31",
        "factures entre 2025-12-01 et 2026-02-28",
        "factures entre 2026-01-15 et 2026-02-15",
        "factures entre 2026-02-01 et 2026-02-28",
        "liste des factures entre 2025-12-15 et 2026-01-15",
    ],
    "get_factures_non_payees": [
        "factures non payees",
        "liste des factures impayees",
        "quelles factures n ont pas ete reglees",
        "factures en attente de paiement",
        "affiche les factures non reglees",
    ],
    "get_factures_partiellement_payees": [
        "factures partiellement payees",
        "factures avec paiement partiel",
        "factures en cours de paiement",
        "affiche les paiements partiels",
        "factures dont le solde restant est positif",
    ],
    "get_clients_multiple_commandes": [
        "clients avec plus de 2 commandes",
        "clients ayant passe plus de 3 commandes",
        "clients avec plus de 5 commandes",
        "clients fideles avec plus de 2 commandes",
        "liste des clients avec plusieurs commandes",
    ],
    "get_produits_stock_faible": [
        "produits avec stock inferieur a 5",
        "produits stock inferieur a 10",
        "produits en rupture de stock",
        "produits dont le stock est inferieur a 3",
        "articles avec moins de 7 unites en stock",
    ],
    "get_total_ventes_mois": [
        "chiffre d affaires de janvier 2026",
        "chiffre d affaires de fevrier 2026",
        "ca du mois de mars 2026",
        "revenus du mois de decembre 2025",
        "ca de novembre 2025",
    ],
}

# ─────────────────────────────────────────────
# Mesure d'une requête unique
# ─────────────────────────────────────────────

def measure_one(question: str) -> dict:
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        r    = requests.post(API_URL, json={"question": question},
                             auth=(API_USER, API_PASS), timeout=30)
        data = r.json() if r.status_code == 200 else {}
    except Exception:
        data = {}
    t1 = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    meta = data.get("metadata", {})
    return {
        "question":        question,
        "template":        meta.get("template", "unknown"),
        "status":          meta.get("status", "error"),
        "duration_ms":     round((t1 - t0) * 1000, 2),
        "api_duration_ms": meta.get("duration_ms", 0),
        "mem_peak_kb":     round(peak / 1024, 2),
        "row_count":       meta.get("row_count", 0),
        "from_cache":      meta.get("from_cache", False),
        "timestamp":       datetime.now().isoformat(),
    }

# ─────────────────────────────────────────────
# Exécution live — 3 passes par question
# ─────────────────────────────────────────────

def run_live(n_passes: int = 3) -> pd.DataFrame:
    records = []
    total   = sum(len(v) for v in QUESTIONS_BY_TEMPLATE.values()) * n_passes
    done    = 0

    print(f"\n{'='*60}")
    print(f"  Latence par template — {total} mesures ({n_passes} passes)")
    print(f"{'='*60}\n")

    for pass_idx in range(n_passes):
        print(f"── Passe {pass_idx + 1}/{n_passes} ──")
        for tpl, questions in QUESTIONS_BY_TEMPLATE.items():
            for q in questions:
                done += 1
                r = measure_one(q)
                r["expected_template"] = tpl
                r["pass"]              = pass_idx + 1
                records.append(r)
                cache_tag = " [cache]" if r["from_cache"] else ""
                correct   = "OK" if r["template"] == tpl else "XX"
                print(f"  [{done:03d}/{total}] {correct} {r['duration_ms']:6.1f} ms  "
                      f"{r['template']:<35}{cache_tag}")
                time.sleep(0.05)

    return pd.DataFrame(records)

# ─────────────────────────────────────────────
# Chargement depuis CSV existant (optionnel)
# ─────────────────────────────────────────────

def load_from_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"template", "duration_ms", "from_cache"}
    if not required.issubset(df.columns):
        raise ValueError(f"CSV manque les colonnes : {required - set(df.columns)}")
    # Si expected_template absent, on l'initialise avec template (mode CSV externe)
    if "expected_template" not in df.columns:
        df["expected_template"] = df["template"]
    print(f"OK Donnees chargees depuis : {path}  ({len(df)} lignes)")
    return df

# ─────────────────────────────────────────────
# Filtre cohérent réutilisé partout
# ─────────────────────────────────────────────

def _cold_df(df: pd.DataFrame) -> pd.DataFrame:
    """Requêtes sans cache + template connu + template correct."""
    if "expected_template" in df.columns:
        return df[
            (df["from_cache"] == False) &
            (df["template"] != "unknown") &
            (df["template"] == df["expected_template"])
        ].copy()
    return df[
        (df["from_cache"] == False) &
        (df["template"] != "unknown")
    ].copy()

# ─────────────────────────────────────────────
# Statistiques par template
# ─────────────────────────────────────────────

def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    # Accuracy globale
    if "expected_template" in df.columns:
        accuracy      = (df["template"] == df["expected_template"]).mean() * 100
        error_rate    = (df["template"] == "unknown").mean() * 100
        mismatch_rate = (df["template"] != df["expected_template"]).mean() * 100
        print(f"\nAccuracy mapping template : {accuracy:.1f}%")
        print(f"Error rate (unknown)      : {error_rate:.1f}%")
        print(f"Mismatch rate             : {mismatch_rate:.1f}%")

    cold = _cold_df(df)

    if cold.empty:
        print("Aucun data valide pour calculer les stats.")
        return pd.DataFrame()

    stats = (
        cold.groupby("template")["duration_ms"]
        .agg(
            n      = "count",
            mean   = "mean",
            median = "median",
            std    = "std",
            min    = "min",
            max    = "max",
            p25    = lambda x: x.quantile(0.25),
            p75    = lambda x: x.quantile(0.75),
            p95    = lambda x: x.quantile(0.95),
            p99    = lambda x: x.quantile(0.99),
        )
        .reset_index()
    )

    # FIX : labels sans emojis — compatibles matplotlib toutes versions/polices
    def perf_label(mean_ms):
        if mean_ms < 500:   return "[OK] Rapide"
        if mean_ms < 1500:  return "[~] Acceptable"
        if mean_ms < 3000:  return "[!] Lent"
        return                     "[X] Tres lent"

    stats["performance"] = stats["mean"].apply(perf_label)

    for col in ["mean", "median", "std", "min", "max", "p25", "p75", "p95", "p99"]:
        stats[col] = stats[col].round(1)

    return stats

# ─────────────────────────────────────────────
# Graphiques
# ─────────────────────────────────────────────

def plot_latency(df: pd.DataFrame, stats: pd.DataFrame, ts: str) -> str:
    # FIX : même filtre que compute_stats — cohérence graphiques / stats
    cold      = _cold_df(df)
    hot       = df[df["from_cache"] == True].copy()
    templates = stats["template"].tolist()
    x         = np.arange(len(templates))
    short     = [t.replace("get_", "").replace("_", "\n") for t in templates]

    fig = plt.figure(figsize=(18, 14))
    fig.suptitle(
        "Breakdown des temps de reponse par template\nChatbot ZAI Informatique V3",
        fontsize=13, fontweight="bold", y=0.99
    )
    gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.55, wspace=0.4)

    # ── 1. Moyenne + P95 par template ──
    ax1 = fig.add_subplot(gs[0, 0])
    w   = 0.35
    b1  = ax1.bar(x - w/2, stats["mean"], width=w, color="#4CAF50", alpha=0.88, label="Moyenne")
    b2  = ax1.bar(x + w/2, stats["p95"],  width=w, color="#FF9800", alpha=0.88, label="P95")
    ax1.set_xticks(x); ax1.set_xticklabels(short, fontsize=8)
    ax1.set_ylabel("ms"); ax1.set_title("Latence moyenne vs P95 (sans cache)")
    ax1.legend(fontsize=8)
    ax1.bar_label(b1, fmt="%.0f", fontsize=7, padding=2)
    ax1.bar_label(b2, fmt="%.0f", fontsize=7, padding=2)

    # ── 2. Boxplot par template ──
    ax2 = fig.add_subplot(gs[0, 1])
    bp_data = [
        cold[cold["template"] == t]["duration_ms"].dropna().tolist()
        for t in templates
    ]
    # Eviter crash si une liste est vide
    bp_data_safe = [d if d else [0] for d in bp_data]
    bp = ax2.boxplot(bp_data_safe, tick_labels=short, patch_artist=True, notch=False)
    colors_box = ["#e8f5e9", "#e3f2fd", "#fff3e0", "#fce4ec", "#f3e5f5", "#e0f2f1"]
    for patch, color in zip(bp["boxes"], colors_box[:len(bp["boxes"])]):
        patch.set_facecolor(color)
    ax2.set_xticklabels(short, fontsize=8)
    ax2.set_ylabel("ms")
    ax2.set_title("Distribution des latences par template (sans cache)")

    # ── 3. Cache vs Sans cache ──
    ax3 = fig.add_subplot(gs[1, 0])
    mean_cold = [
        cold[cold["template"] == t]["duration_ms"].mean()
        if len(cold[cold["template"] == t]) > 0 else 0
        for t in templates
    ]
    mean_hot = [
        hot[hot["template"] == t]["duration_ms"].mean()
        if len(hot[hot["template"] == t]) > 0 else np.nan
        for t in templates
    ]
    ax3.bar(x - w/2, mean_cold, width=w, color="#4CAF50", alpha=0.88, label="Sans cache")
    ax3.bar(x + w/2, [v if not np.isnan(v) else 0 for v in mean_hot],
            width=w, color="#2196F3", alpha=0.88, label="Avec cache")
    ax3.set_xticks(x); ax3.set_xticklabels(short, fontsize=8)
    ax3.set_ylabel("ms"); ax3.set_title("Impact du cache sur la latence")
    ax3.legend(fontsize=8)

    # ── 4. Heatmap latence ──
    ax4 = fig.add_subplot(gs[1, 1])
    pivot_data   = []
    pivot_labels = []
    for tpl in templates:
        sub = cold[cold["template"] == tpl].sort_values("timestamp")
        if len(sub) > 0:
            pivot_data.append(sub["duration_ms"].tolist()[:5])
            pivot_labels.append(tpl.replace("get_", ""))
    if pivot_data:
        max_len = max(len(r) for r in pivot_data)
        matrix  = np.array([r + [np.nan] * (max_len - len(r)) for r in pivot_data])
        im = ax4.imshow(matrix, cmap="RdYlGn_r", aspect="auto",
                        vmin=np.nanmin(matrix), vmax=np.nanmax(matrix))
        ax4.set_yticks(range(len(pivot_labels)))
        ax4.set_yticklabels([l.replace("_", "\n") for l in pivot_labels], fontsize=7.5)
        ax4.set_xlabel("N mesure")
        ax4.set_title("Heatmap latences (vert=rapide, rouge=lent)")
        plt.colorbar(im, ax=ax4, label="ms", shrink=0.8)
        mean_val = np.nanmean(matrix)
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                if not np.isnan(matrix[i, j]):
                    ax4.text(j, i, f"{matrix[i,j]:.0f}", ha="center", va="center",
                             fontsize=6.5,
                             color="white" if matrix[i, j] > mean_val else "black")
    else:
        ax4.set_title("Heatmap — pas de donnees valides")
        ax4.axis("off")

    # ── 5. Évolution dans le temps ──
    ax5 = fig.add_subplot(gs[2, 0])
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    cmap_t    = plt.get_cmap("tab10")
    tpl_idx   = {t: i for i, t in enumerate(templates)}
    for idx, row in df_sorted.iterrows():
        cidx   = tpl_idx.get(row["template"], len(templates))
        color  = cmap_t(cidx % 10)
        marker = "^" if row["from_cache"] else "o"
        ax5.scatter(idx, row["duration_ms"], color=color, s=20, alpha=0.8, marker=marker)
    ax5.plot(df_sorted.index, df_sorted["duration_ms"],
             color="#ddd", linewidth=0.5, zorder=0)
    handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=cmap_t(tpl_idx[t] % 10),
                   markersize=7, label=t.replace("get_", ""))
        for t in templates
    ]
    handles.append(plt.Line2D([0], [0], marker="^", color="#555",
                               markersize=7, label="cache", linestyle="None"))
    ax5.legend(handles=handles, fontsize=6.5, ncol=2, loc="upper right")
    ax5.set_xlabel("N requete"); ax5.set_ylabel("ms")
    ax5.set_title("Evolution latence dans le temps (^=cache)")

    # ── 6. Tableau récapitulatif ──
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.axis("off")
    col_labels = ["Template", "Moy.", "Med.", "P95", "P99", "Perf."]
    table_data = [
        [
            r["template"].replace("get_", ""),
            f"{r['mean']:.0f}",
            f"{r['median']:.0f}",
            f"{r['p95']:.0f}",
            f"{r['p99']:.0f}",
            r["performance"],
        ]
        for _, r in stats.iterrows()
    ]
    tbl = ax6.table(cellText=table_data, colLabels=col_labels,
                    loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.5)
    tbl.scale(1, 1.4)
    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor("#2e7d32")
        tbl[0, j].set_text_props(color="white", fontweight="bold")
    for i in range(1, len(table_data) + 1):
        for j in range(len(col_labels)):
            tbl[i, j].set_facecolor("#f1f8e9" if i % 2 == 0 else "white")
    ax6.set_title("Recapitulatif latences (ms, sans cache)", fontweight="bold", pad=12)

    path_fig = os.path.join(OUTPUT_DIR, "latency_by_template.png")
    fig.savefig(path_fig, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"OK Graphique : {path_fig}")
    return path_fig

# ─────────────────────────────────────────────
# Rapport Markdown
# ─────────────────────────────────────────────

def _df_to_markdown(df: pd.DataFrame) -> str:
    cols   = list(df.columns)
    header = "| " + " | ".join(cols) + " |"
    sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows   = ["| " + " | ".join(str(v) for v in row) + " |"
              for _, row in df.iterrows()]
    return "\n".join([header, sep] + rows)


def write_report(df: pd.DataFrame, stats: pd.DataFrame, path_fig: str, ts: str):
    cold = _cold_df(df)
    hot  = df[df["from_cache"] == True].copy()

    overall_mean = cold["duration_ms"].mean() if len(cold) > 0 else 0
    overall_p95  = cold["duration_ms"].quantile(0.95) if len(cold) > 0 else 0
    overall_p99  = cold["duration_ms"].quantile(0.99) if len(cold) > 0 else 0
    cache_gain   = None
    if len(hot) > 0 and len(cold) > 0 and cold["duration_ms"].mean() > 0:
        cache_gain = (1 - hot["duration_ms"].mean() / cold["duration_ms"].mean()) * 100

    slowest      = stats.loc[stats["mean"].idxmax(), "template"] if not stats.empty else "N/A"
    fastest      = stats.loc[stats["mean"].idxmin(), "template"] if not stats.empty else "N/A"
    slowest_mean = stats.loc[stats["mean"].idxmax(), "mean"]     if not stats.empty else 0
    fastest_mean = stats.loc[stats["mean"].idxmin(), "mean"]     if not stats.empty else 0

    display_cols = ["template", "n", "mean", "median", "p95", "p99", "std", "performance"]
    lines = [
        "# Breakdown des temps de reponse par template",
        "",
        f"**Genere le** : {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}",
        f"**Total mesures** : {len(df)} ({len(cold)} sans cache, {len(hot)} avec cache)",
        "",
        "## Resume global (sans cache)",
        "",
        "| Metrique | Valeur |",
        "|---|---|",
        f"| Latence moyenne globale | **{overall_mean:.1f} ms** |",
        f"| Latence P95 globale     | **{overall_p95:.1f} ms** |",
        f"| Latence P99 globale     | **{overall_p99:.1f} ms** |",
        f"| Template le plus rapide | **{fastest}** ({fastest_mean:.0f} ms) |",
        f"| Template le plus lent   | **{slowest}** ({slowest_mean:.0f} ms) |",
    ]
    if cache_gain is not None:
        lines.append(f"| Gain du cache | **{cache_gain:.1f}%** de reduction de latence |")

    lines += [
        "",
        "## Detail par template",
        "",
        _df_to_markdown(stats[display_cols].rename(columns={
            "template":    "Template",
            "n":           "N",
            "mean":        "Moy. (ms)",
            "median":      "Med. (ms)",
            "p95":         "P95 (ms)",
            "p99":         "P99 (ms)",
            "std":         "Ecart-type",
            "performance": "Performance",
        })),
        "",
        "## Visualisation",
        "",
        f"![Latence par template]({os.path.basename(path_fig)})",
        "",
        "## Analyse",
        "",
        "### Observations principales",
        "",
        f"- La latence moyenne globale est de **{overall_mean:.0f} ms**, "
        "ce qui inclut le round-trip HTTP local + traitement NLP + execution SQL.",
        f"- Le template **{slowest}** est le plus lent en raison du volume de donnees "
        "retournees et/ou de la complexite de la jointure SQL.",
        f"- Le template **{fastest}** est le plus rapide car il necessite "
        "une requete SQL simple sans jointure complexe.",
    ]
    if cache_gain is not None:
        lines.append(
            f"- Le cache reduit la latence de **{cache_gain:.1f}%** en moyenne — "
            "valide l'interet du mecanisme de cache pour les requetes repetitives."
        )
    lines += [
        "",
        "### Recommandations",
        "",
        "- **Connexion persistante DB** : remplacer la creation de connexion a chaque "
        "requete par un pool (SQLAlchemy `pool_size=5`) — gain estime : -300 a -500 ms.",
        "- **Cache chaud** : pre-charger les templates les plus utilises au demarrage "
        "pour eliminer la latence de la premiere requete.",
        "- **Timeout adaptatif** : fixer un timeout par template en fonction du P99 "
        "observe (ex: 5s pour `get_factures_between`, 3s pour les autres).",
        "- **Objectif V3+** : descendre sous 800 ms en moyenne avec pool de connexions "
        "et cache chaud.",
        "",
        "---",
        f"*Chatbot ZAI Informatique — NL2SQL V3 — {datetime.now().strftime('%d/%m/%Y')}*",
    ]

    path_md = os.path.join(OUTPUT_DIR, "latency_by_template.md")
    with open(path_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"OK Rapport : {path_md}")
    return path_md

# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Breakdown latence par template")
    parser.add_argument("--csv", default=None,
                        help="Chemin vers un CSV memory_detail existant (optionnel)")
    parser.add_argument("--passes", type=int, default=3,
                        help="Nombre de passes si mesures live (defaut: 3)")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.csv:
        df = load_from_csv(args.csv)
    else:
        df = run_live(n_passes=args.passes)

    stats = compute_stats(df)

    if not stats.empty:
        print(f"\n{'='*60}")
        print("  RESUME PAR TEMPLATE (sans cache)")
        print(f"{'='*60}")
        print(stats[["template", "n", "mean", "p95", "p99", "performance"]].to_string(index=False))

        path_csv = os.path.join(OUTPUT_DIR, "latency_by_template.csv")
        stats.to_csv(path_csv, index=False, encoding="utf-8-sig")
        print(f"\nOK CSV : {path_csv}")

        path_fig = plot_latency(df, stats, ts)
        write_report(df, stats, path_fig, ts)

    print(f"\n{'='*60}")
    print("  Termine. Fichiers dans : reports/")
    print(f"{'='*60}\n")