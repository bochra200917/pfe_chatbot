# ui/pdf_export.py
# Génère un rapport PDF complet : résumé + tableau + graphique
# Utilise reportlab — pip install reportlab

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image
)

GREEN       = colors.HexColor("#2e7d32")
GREEN_LIGHT = colors.HexColor("#e8f5e9")
GRAY_BG     = colors.HexColor("#f8f9fa")
GRAY_BORDER = colors.HexColor("#dee2e6")
WHITE       = colors.white
BLACK       = colors.HexColor("#1a1a2e")


def _styles():
    base = getSampleStyleSheet()
    n    = base["Normal"]
    return {
        "title": ParagraphStyle("T", parent=n, fontSize=16, fontName="Helvetica-Bold",
                                textColor=BLACK, spaceAfter=4),
        "sub":   ParagraphStyle("S", parent=n, fontSize=9, fontName="Helvetica",
                                textColor=colors.HexColor("#6c757d"), spaceAfter=12),
        "sec":   ParagraphStyle("SE", parent=n, fontSize=11, fontName="Helvetica-Bold",
                                textColor=GREEN, spaceBefore=12, spaceAfter=6),
        "body":  ParagraphStyle("B", parent=n, fontSize=9, fontName="Helvetica",
                                textColor=BLACK, leading=13),
        "sql":   ParagraphStyle("SQL", fontName="Courier", fontSize=7.5,
                                textColor=colors.HexColor("#1a237e"),
                                backColor=colors.HexColor("#f3f4f6"),
                                leftIndent=6, rightIndent=6, leading=11,
                                borderPadding=(4, 6, 4, 6)),
        "foot":  ParagraphStyle("F", fontName="Helvetica", fontSize=7,
                                textColor=colors.HexColor("#aaaaaa")),
        "th":    ParagraphStyle("TH", fontName="Helvetica-Bold", fontSize=7.5,
                                textColor=WHITE),
        "td":    ParagraphStyle("TD", fontName="Helvetica", fontSize=7.5,
                                textColor=BLACK),
    }


def generate_pdf_report(
    question: str,
    summary: str,
    template: str,
    duration_ms: float,
    row_count: int,
    logs_id: str,
    table_data: list,
    chart_fig=None,
    from_cache: bool = False,
    sql_query: str = "",
) -> bytes:
    """Retourne les bytes d'un PDF rapport complet."""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"Rapport — {template}",
        author="Chatbot ZAI Informatique",
    )
    s     = _styles()
    story = []

    # ── En-tête ──
    story.append(Paragraph("Rapport d'analyse — Chatbot ZAI Informatique", s["title"]))
    story.append(Paragraph(
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}",
        s["sub"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN_LIGHT, spaceAfter=8))

    # ── Métadonnées ──
    story.append(Paragraph("Résumé de la requête", s["sec"]))
    meta = [
        ["Question",  question],
        ["Réponse",   summary],
        ["Template",  template],
        ["Durée",     f"{duration_ms:.0f} ms" + (" (cache)" if from_cache else "")],
        ["Résultats", f"{row_count} ligne(s)"],
        ["ID audit",  logs_id[:20] + "..." if len(logs_id) > 20 else logs_id],
    ]
    mt = Table(meta, colWidths=[3.5*cm, 13.5*cm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(0,-1), GREEN_LIGHT),
        ("TEXTCOLOR",     (0,0),(0,-1), GREEN),
        ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,0),(1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("ROWBACKGROUNDS",(1,0),(1,-1), [WHITE, GRAY_BG]),
        ("GRID",          (0,0),(-1,-1), 0.4, GRAY_BORDER),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
    ]))
    story.append(mt)

    # ── SQL ──
    if sql_query:
        story.append(Paragraph("Requête SQL exécutée", s["sec"]))
        story.append(Paragraph(
            sql_query.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                     .replace("\n","<br/>").strip(),
            s["sql"]
        ))

    # ── Tableau ──
    if table_data:
        story.append(Paragraph(f"Données ({row_count} ligne(s))", s["sec"]))
        cols    = list(table_data[0].keys())
        col_w   = (17*cm) / len(cols)
        rows    = [[Paragraph(f"<b>{c}</b>", s["th"]) for c in cols]]
        for row in table_data:
            rows.append([
                Paragraph(str(row.get(c,"") or ""), s["td"])
                for c in cols
            ])
        tbl = Table(rows, colWidths=[col_w]*len(cols), repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),  GREEN),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, GRAY_BG]),
            ("GRID",          (0,0),(-1,-1), 0.3, GRAY_BORDER),
            ("FONTSIZE",      (0,0),(-1,-1), 7.5),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 5),
            ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ]))
        story.append(tbl)

    # ── Graphique ──
    if chart_fig is not None:
        story.append(Paragraph("Visualisation graphique", s["sec"]))
        try:
            img_buf = io.BytesIO()
            chart_fig.savefig(img_buf, format="png", dpi=150, bbox_inches="tight")
            img_buf.seek(0)
            story.append(Image(img_buf, width=14*cm, height=7*cm))
        except Exception as e:
            story.append(Paragraph(f"Graphique non disponible : {e}", s["body"]))

    # ── Pied de page ──
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY_BORDER))
    story.append(Paragraph(
        f"Chatbot ZAI Informatique — NL2SQL V3 — "
        f"{datetime.now().strftime('%d/%m/%Y')} — ID : {logs_id[:8]}...",
        s["foot"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()