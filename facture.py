"""
facture.py — Génération de factures PDF professionnelles (ReportLab)
"""
import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, HRFlowable, KeepTogether,
)
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF

# ── Palette ────────────────────────────────────────────────────────────────────
ORANGE   = colors.HexColor("#FF6B35")
DARK     = colors.HexColor("#0D0F14")
GREY_BG  = colors.HexColor("#F4F5F7")
GREY_TXT = colors.HexColor("#6B7280")
WHITE    = colors.white
BLACK    = colors.HexColor("#1A1A2E")
GREEN    = colors.HexColor("#22C55E")
RED_C    = colors.HexColor("#EF4444")

# ── Styles typographiques ───────────────────────────────────────────────────────
def _styles():
    return {
        "title": ParagraphStyle(
            "title", fontName="Helvetica-Bold", fontSize=26,
            textColor=ORANGE, leading=30,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName="Helvetica", fontSize=10,
            textColor=GREY_TXT, leading=14,
        ),
        "heading": ParagraphStyle(
            "heading", fontName="Helvetica-Bold", fontSize=9,
            textColor=GREY_TXT, leading=12,
            spaceAfter=2, textTransform="uppercase",
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=10,
            textColor=BLACK, leading=14,
        ),
        "body_bold": ParagraphStyle(
            "body_bold", fontName="Helvetica-Bold", fontSize=10,
            textColor=BLACK, leading=14,
        ),
        "small": ParagraphStyle(
            "small", fontName="Helvetica", fontSize=8,
            textColor=GREY_TXT, leading=11,
        ),
        "total_label": ParagraphStyle(
            "total_label", fontName="Helvetica-Bold", fontSize=11,
            textColor=WHITE, leading=16, alignment=TA_RIGHT,
        ),
        "total_val": ParagraphStyle(
            "total_val", fontName="Helvetica-Bold", fontSize=13,
            textColor=WHITE, leading=18, alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            "footer", fontName="Helvetica", fontSize=7.5,
            textColor=GREY_TXT, leading=11, alignment=TA_CENTER,
        ),
        "right": ParagraphStyle(
            "right", fontName="Helvetica", fontSize=10,
            textColor=BLACK, leading=14, alignment=TA_RIGHT,
        ),
        "right_bold": ParagraphStyle(
            "right_bold", fontName="Helvetica-Bold", fontSize=10,
            textColor=BLACK, leading=14, alignment=TA_RIGHT,
        ),
        "num": ParagraphStyle(
            "num", fontName="Helvetica-Bold", fontSize=14,
            textColor=BLACK, leading=18,
        ),
    }


# ── Fonction principale ─────────────────────────────────────────────────────────
def generer_facture_pdf(data: dict) -> bytes:
    """
    Génère une facture PDF et retourne les bytes.

    data keys:
      numero_facture, date_facture, date_echeance (opt)
      emetteur: {nom, adresse, ville, telephone, email, rccm, ifu}
      client:   {nom, adresse, ville, telephone, email}
      lignes:   [{description, qte, unite, prix_unitaire}]
      taux_tva: float (ex 0.18)
      notes: str
      statut_paiement: "Payé" | "En attente" | "Partiel"
      moyen_paiement: str
    """
    buf = io.BytesIO()
    s   = _styles()
    W, H = A4  # 595.28 x 841.89 pts

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.8*cm,  bottomMargin=2*cm,
        title=f"Facture {data.get('numero_facture','')}",
    )

    story = []

    # ── HEADER BAND ──────────────────────────────────────────────────────────
    emetteur = data.get("emetteur", {})
    statut   = data.get("statut_paiement", "En attente")
    statut_color = {"Payé": GREEN, "En attente": ORANGE, "Partiel": RED_C}.get(statut, GREY_TXT)

    # Left: company name + coords | Right: FACTURE label + number
    header_data = [[
        Table([[
            [Paragraph(emetteur.get("nom","Mon Imprimerie"), s["title"])],
            [Paragraph(emetteur.get("adresse",""), s["subtitle"])],
            [Paragraph(f"{emetteur.get('ville','')}  ·  {emetteur.get('telephone','')}  ·  {emetteur.get('email','')}", s["subtitle"])],
        ]], colWidths=[9.5*cm], style=TableStyle([
            ("ALIGN",    (0,0),(0,-1),"LEFT"),
            ("VALIGN",   (0,0),(0,-1),"TOP"),
            ("TOPPADDING",(0,0),(0,-1),0),
            ("BOTTOMPADDING",(0,0),(0,-1),2),
        ])),
        Table([[
            [Paragraph("FACTURE", ParagraphStyle("fac", fontName="Helvetica-Bold",
                fontSize=9, textColor=GREY_TXT, leading=11,
                spaceBefore=0, textTransform="uppercase"))],
            [Paragraph(data.get("numero_facture","F-0000"), s["num"])],
            [Paragraph(f"Date : {data.get('date_facture', str(date.today()))}", s["subtitle"])],
            [Paragraph(f"Échéance : {data.get('date_echeance','À réception')}", s["subtitle"])],
            [_statut_badge(statut, statut_color)],
        ]], colWidths=[7*cm], style=TableStyle([
            ("ALIGN",    (0,0),(0,-1),"RIGHT"),
            ("VALIGN",   (0,0),(0,-1),"TOP"),
            ("TOPPADDING",(0,0),(0,-1),0),
            ("BOTTOMPADDING",(0,0),(0,-1),2),
        ])),
    ]]
    header_tbl = Table(header_data, colWidths=[9.5*cm, 7*cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN",  (0,0),(-1,-1),"TOP"),
        ("ALIGN",   (1,0),(1,0), "RIGHT"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE, spaceAfter=5*mm))

    # ── EMETTEUR / CLIENT ────────────────────────────────────────────────────
    client = data.get("client", {})
    billed_rows = [
        [Paragraph("DE", s["heading"]),
         Paragraph("FACTURER À", s["heading"])],
        [Paragraph(emetteur.get("nom",""), s["body_bold"]),
         Paragraph(client.get("nom","—"), s["body_bold"])],
        [Paragraph(emetteur.get("adresse",""), s["body"]),
         Paragraph(client.get("adresse",""), s["body"])],
        [Paragraph(emetteur.get("ville",""), s["body"]),
         Paragraph(client.get("ville",""), s["body"])],
        [Paragraph(f"Tél : {emetteur.get('telephone','')}", s["small"]),
         Paragraph(f"Tél : {client.get('telephone','')}", s["small"])],
        [Paragraph(f"Email : {emetteur.get('email','')}", s["small"]),
         Paragraph(f"Email : {client.get('email','')}", s["small"])],
    ]
    if emetteur.get("rccm"):
        billed_rows.append([
            Paragraph(f"RCCM : {emetteur['rccm']}", s["small"]),
            Paragraph("", s["small"]),
        ])
    if emetteur.get("ifu"):
        billed_rows.append([
            Paragraph(f"IFU : {emetteur['ifu']}", s["small"]),
            Paragraph("", s["small"]),
        ])

    billed_tbl = Table(billed_rows, colWidths=[8*cm, 8.5*cm])
    billed_tbl.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LINEAFTER",    (0,0),(0,-1),  0.5, GREY_BG),
        ("BACKGROUND",   (1,0),(1,-1),  GREY_BG),
        ("LEFTPADDING",  (1,0),(1,-1),  10),
        ("RIGHTPADDING", (1,0),(1,-1),  10),
        ("TOPPADDING",   (1,0),(1,-1),  4),
        ("BOTTOMPADDING",(1,0),(1,-1),  4),
        ("ROUNDEDCORNERS",(0,0),(0,0),  6),
    ]))
    story.append(billed_tbl)
    story.append(Spacer(1, 6*mm))

    # ── TABLEAU DES LIGNES ───────────────────────────────────────────────────
    lignes = data.get("lignes", [])
    col_w  = [8.5*cm, 1.8*cm, 2.2*cm, 2.8*cm, 2.5*cm]

    rows = [[
        Paragraph("DESCRIPTION", s["heading"]),
        Paragraph("QTÉ",         s["heading"]),
        Paragraph("UNITÉ",       s["heading"]),
        Paragraph("P.U. (FCFA)", s["heading"]),
        Paragraph("TOTAL (FCFA)",s["heading"]),
    ]]
    montant_ht = 0
    for i, lg in enumerate(lignes):
        qte   = float(lg.get("qte", 0))
        pu    = float(lg.get("prix_unitaire", 0))
        total = qte * pu
        montant_ht += total
        bg = WHITE if i % 2 == 0 else GREY_BG
        rows.append([
            Paragraph(lg.get("description","—"), s["body"]),
            Paragraph(f"{qte:,.0f}", ParagraphStyle("c", fontName="Helvetica", fontSize=10, alignment=TA_CENTER, textColor=BLACK)),
            Paragraph(lg.get("unite","—"), ParagraphStyle("c2", fontName="Helvetica", fontSize=10, alignment=TA_CENTER, textColor=BLACK)),
            Paragraph(f"{pu:,.0f}", ParagraphStyle("r", fontName="Helvetica", fontSize=10, alignment=TA_RIGHT, textColor=BLACK)),
            Paragraph(f"{total:,.0f}", ParagraphStyle("r2", fontName="Helvetica-Bold", fontSize=10, alignment=TA_RIGHT, textColor=BLACK)),
        ])

    items_tbl = Table(rows, colWidths=col_w, repeatRows=1)
    row_styles = [
        ("BACKGROUND",   (0,0),(-1,0),  DARK),
        ("TEXTCOLOR",    (0,0),(-1,0),  WHITE),
        ("FONTNAME",     (0,0),(-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0),(-1,0),  8),
        ("TOPPADDING",   (0,0),(-1,0),  8),
        ("BOTTOMPADDING",(0,0),(-1,0),  8),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,1),(-1,-1), 7),
        ("BOTTOMPADDING",(0,1),(-1,-1), 7),
        ("GRID",         (0,1),(-1,-1), 0.3, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, GREY_BG]),
        ("LEFTPADDING",  (0,0),(0,-1),  6),
        ("RIGHTPADDING", (-1,0),(-1,-1),6),
    ]
    items_tbl.setStyle(TableStyle(row_styles))
    story.append(items_tbl)
    story.append(Spacer(1, 4*mm))

    # ── TOTAUX ───────────────────────────────────────────────────────────────
    taux_tva  = float(data.get("taux_tva", 0.18))
    montant_tva  = montant_ht * taux_tva
    montant_ttc  = montant_ht + montant_tva

    def _row(label, val, bold=False, highlight=False):
        lbl_s = ParagraphStyle("lbl", fontName="Helvetica-Bold" if bold else "Helvetica",
                               fontSize=10, textColor=WHITE if highlight else BLACK,
                               alignment=TA_RIGHT)
        val_s = ParagraphStyle("val", fontName="Helvetica-Bold",
                               fontSize=12 if highlight else 10,
                               textColor=WHITE if highlight else BLACK,
                               alignment=TA_RIGHT)
        bg    = ORANGE if highlight else (GREY_BG if not bold else WHITE)
        return [Paragraph("", s["body"]), Paragraph(label, lbl_s), Paragraph(val, val_s)], bg

    r1, b1 = _row(f"Sous-total HT :", f"{montant_ht:,.0f} FCFA")
    r2, b2 = _row(f"TVA ({int(taux_tva*100)}%) :", f"{montant_tva:,.0f} FCFA")
    r3, b3 = _row("TOTAL TTC :", f"{montant_ttc:,.0f} FCFA", bold=True, highlight=True)

    totaux_data  = [r1, r2, r3]
    totaux_bg    = [b1, b2, b3]
    totaux_table = Table(totaux_data, colWidths=[9*cm, 4.5*cm, 4*cm])
    t_styles = [
        ("VALIGN",       (0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",   (0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("ALIGN",        (1,0),(-1,-1),"RIGHT"),
        ("RIGHTPADDING", (2,0),(2,-1), 6),
    ]
    for i, bg in enumerate(totaux_bg):
        t_styles.append(("BACKGROUND",(1,i),(2,i),bg))
        if bg == ORANGE:
            t_styles.append(("ROUNDEDCORNERS",(1,i),(2,i),4))
    totaux_table.setStyle(TableStyle(t_styles))
    story.append(totaux_table)
    story.append(Spacer(1, 6*mm))

    # ── NOTES + PAIEMENT ─────────────────────────────────────────────────────
    bottom_data = []
    if data.get("notes"):
        bottom_data.append([
            Paragraph("Notes :", s["heading"]),
            Paragraph("", s["body"]),
        ])
        bottom_data.append([
            Paragraph(data["notes"], s["body"]),
            Paragraph("", s["body"]),
        ])

    moyen = data.get("moyen_paiement","")
    if moyen:
        bottom_data.append([
            Paragraph(f"Mode de règlement : <b>{moyen}</b>", s["body"]),
            Paragraph("", s["body"]),
        ])

    if bottom_data:
        note_tbl = Table(bottom_data, colWidths=[17.5*cm])
        note_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), GREY_BG),
            ("TOPPADDING",   (0,0),(-1,-1), 5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ("LEFTPADDING",  (0,0),(-1,-1), 10),
        ]))
        story.append(note_tbl)
        story.append(Spacer(1, 4*mm))

    # ── FOOTER ───────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY_TXT, spaceBefore=6*mm, spaceAfter=3*mm))
    footer_txt = (
        f"{emetteur.get('nom','')}"
        + (f" — RCCM : {emetteur['rccm']}" if emetteur.get("rccm") else "")
        + (f" — IFU : {emetteur['ifu']}"   if emetteur.get("ifu")  else "")
        + f"<br/>Document généré le {date.today().strftime('%d/%m/%Y')} — Merci de votre confiance."
    )
    story.append(Paragraph(footer_txt, s["footer"]))

    doc.build(story)
    return buf.getvalue()


def _statut_badge(label: str, color) -> Table:
    badge = Table([[Paragraph(
        label,
        ParagraphStyle("b", fontName="Helvetica-Bold", fontSize=8.5,
                       textColor=WHITE, alignment=TA_CENTER),
    )]], colWidths=[3*cm])
    badge.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,0), color),
        ("TOPPADDING",   (0,0),(0,0), 4),
        ("BOTTOMPADDING",(0,0),(0,0), 4),
        ("LEFTPADDING",  (0,0),(0,0), 8),
        ("RIGHTPADDING", (0,0),(0,0), 8),
        ("ROUNDEDCORNERS",(0,0),(0,0), 4),
    ]))
    return badge
