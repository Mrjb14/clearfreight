#!/usr/bin/env python3
"""
Genere 4 fausses factures de fret maritime pour tester ClearFreight.
Usage : python generate_test_invoices.py
Output: test_invoices/ (4 PDFs)

Nommage des fichiers choisi pour que le backend detecte le bon scenario :
  facture_maersk_normale.pdf    -> scenario "normale"    (score 12%)
  facture_cmacgm_baf.pdf        -> scenario "baf_eleve"  (score 34%)
  facture_msc_surestaries.pdf   -> scenario "surestaries"(score 28%)
  facture_hapag_anomalies.pdf   -> scenario "multi"      (score 52%)
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_invoices")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Palette
NAVY  = colors.HexColor("#0A1628")
GRAY  = colors.HexColor("#4B5563")
LGRAY = colors.HexColor("#9CA3AF")
BGRAY = colors.HexColor("#F3F4F6")
WHITE = colors.white
LINE  = colors.HexColor("#E5E7EB")


def s(name, **kw):
    return PS(name, **kw)


def lbl(text):
    return Paragraph(text, s("lb", fontName="Helvetica-Bold", fontSize=7, textColor=LGRAY))


def val(text):
    return Paragraph(text, s("vl", fontName="Helvetica", fontSize=9, textColor=NAVY, leading=13))


def small(text):
    return Paragraph(text, s("sm", fontName="Helvetica", fontSize=8, textColor=GRAY, leading=12))


def section_hdr(text):
    return Paragraph(
        text,
        s("sc", fontName="Helvetica-Bold", fontSize=8, textColor=GRAY, spaceBefore=10, spaceAfter=5),
    )


def kv_block(pairs):
    rows = [[lbl(k), val(v)] for k, v in pairs]
    t = Table(rows, colWidths=[3.2 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def charges_table(rows, currency):
    """rows = [(code, description, qty, amount)]"""
    wh = s("wh", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE)
    header = [
        Paragraph("Code",                wh),
        Paragraph("Description",         wh),
        Paragraph("Qte",                 PS("q", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE, alignment=1)),
        Paragraph(f"Montant {currency}", PS("m", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE, alignment=2)),
    ]
    data = [header]
    for code, desc, qty, amount in rows:
        data.append([
            Paragraph(code,   s("rc", fontName="Helvetica-Bold", fontSize=8, textColor=NAVY)),
            Paragraph(desc,   s("rd", fontName="Helvetica",      fontSize=8, textColor=GRAY, leading=11)),
            Paragraph(qty,    PS("rq", fontName="Helvetica",     fontSize=8, textColor=GRAY, alignment=1)),
            Paragraph(amount, PS("ra", fontName="Helvetica-Bold",fontSize=8, textColor=NAVY, alignment=2)),
        ])
    t = Table(data, colWidths=[3.5 * cm, 8.5 * cm, 1.5 * cm, 3.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, BGRAY]),
        ("GRID",          (0, 0), (-1, -1), 0.3, LINE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def total_table(lines):
    """lines = [(label, amount_str)] — last line = grand total"""
    rows = []
    for i, (label, amount) in enumerate(lines):
        last = i == len(lines) - 1
        fn, sz = ("Helvetica-Bold", 10) if last else ("Helvetica", 9)
        rows.append([
            Paragraph(label,  s(f"tl{i}", fontName=fn, fontSize=sz, textColor=NAVY)),
            Paragraph(amount, PS(f"ta{i}", fontName=fn, fontSize=sz, textColor=NAVY, alignment=2)),
        ])
    t = Table(rows, colWidths=[10 * cm, 7 * cm])
    style = [
        ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]
    if len(lines) > 1:
        style.append(("LINEABOVE", (0, -1), (-1, -1), 0.5, NAVY))
    t.setStyle(TableStyle(style))
    return t


# ==================== BUILDER ====================

def build_invoice(
    filename, carrier_name, carrier_color, carrier_addr,
    inv_no, inv_date, due_date,
    bl, booking, container, ctype, bl_date,
    bill_to, shipper, pol, pod,
    charges_usd, charges_eur, totals,
    payment_note="",
):
    path = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    story = []

    # HEADER
    hdr = Table([[
        Paragraph(carrier_name, s("cn", fontName="Helvetica-Bold", fontSize=20, textColor=carrier_color)),
        Paragraph("FREIGHT INVOICE", PS("fi", fontName="Helvetica-Bold", fontSize=14, textColor=NAVY, alignment=2)),
    ]], colWidths=[10 * cm, 7 * cm])
    hdr.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(hdr)
    story.append(small(carrier_addr))
    story.append(HRFlowable(width="100%", thickness=1.5, color=carrier_color, spaceAfter=8))

    # INVOICE META
    meta_left  = [("N° Facture", inv_no), ("Date", inv_date), ("Echeance", due_date)]
    meta_right = [("Reference B/L", bl), ("N° Booking", booking), ("Conteneur", container), ("Type conteneur", ctype), ("Date B/L", bl_date)]
    meta_tbl = Table([[kv_block(meta_left), kv_block(meta_right)]], colWidths=[8.5 * cm, 8.5 * cm])
    meta_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # PARTIES
    story.append(section_hdr("PARTIES & ACHEMINEMENT"))
    pty = Table([
        [lbl("FACTURE A / BILL TO"), lbl("CHARGEUR / SHIPPER"), lbl("ACHEMINEMENT")],
        [val(bill_to), val(shipper), val(f"POL: {pol}\nPOD: {pod}")],
    ], colWidths=[6 * cm, 6 * cm, 5 * cm])
    pty.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), BGRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(pty)
    story.append(Spacer(1, 0.3 * cm))

    # CHARGES
    if charges_usd:
        story.append(section_hdr("DETAIL DES CHARGES — USD"))
        story.append(charges_table(charges_usd, "USD"))
        story.append(Spacer(1, 0.2 * cm))
    if charges_eur:
        story.append(section_hdr("DETAIL DES CHARGES — EUR"))
        story.append(charges_table(charges_eur, "EUR"))
        story.append(Spacer(1, 0.2 * cm))

    # TOTALS
    story.append(Spacer(1, 0.1 * cm))
    tt = Table([[total_table(totals)]], colWidths=[17 * cm])
    tt.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
    story.append(tt)

    # PAYMENT
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=6))
    story.append(section_hdr("MODALITES DE PAIEMENT"))
    story.append(small("Virement bancaire - IBAN: FR76 3000 6000 0112 3456 7890 189  BIC: BNPAFRPPXXX"))
    story.append(small("Delai: 30 jours date de facture. Tout retard entraine des penalites de 3%/mois."))
    if payment_note:
        story.append(Spacer(1, 0.15 * cm))
        story.append(small(f"Note: {payment_note}"))

    # FOOTER
    story.append(Spacer(1, 0.4 * cm))
    story.append(small(
        "Toute contestation doit etre formulee dans les 30 jours suivant la date de facturation. "
        "Pour les frais D&D, la reglementation FMC 2024 s'applique (deduction des jours non ouvres)."
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        "[ DOCUMENT FICTIF GENERE A DES FINS DE TEST — ClearFreight Prototype 2026 ]",
        PS("dm", fontName="Helvetica-Oblique", fontSize=7, textColor=LGRAY, alignment=1),
    ))

    doc.build(story)
    print(f"  OK  {filename}")
    return path


# ==================== FACTURES ====================

print("Generation des factures de test...")

# ---- 1. Maersk — Normale (score 12%) ----
build_invoice(
    filename="facture_maersk_normale.pdf",
    carrier_name="Maersk Line",
    carrier_color=colors.HexColor("#42B0D5"),
    carrier_addr="Copenhagen Tower  Dampfaergevej 26  DK-2100 Copenhagen O, Danemark  |  maersk.com",
    inv_no="MSK-FR-2026-004217",
    inv_date="14 mars 2026",
    due_date="13 avril 2026",
    bl="MAEU7614523890",
    booking="BKG-MSK-20260228-7741",
    container="MSKU7654321-8",
    ctype="40' High Cube (HC)",
    bl_date="06 janvier 2026",
    bill_to="Beaumont Distribution SAS\n12 Rue de la Logistique\n69003 Lyon, France\nSIRET: 412 345 678 00021",
    shipper="Shenzhen Global Exports Co., Ltd\nBld 7, Longhua Industrial Zone\nShenzhen 518109, Chine",
    pol="Shanghai / CNSHA\nSIPG Waigaoqiao Terminal 5\nETD: 04 jan. 2026",
    pod="Le Havre / FRLEH\nPort 2000 — Terminal TL2\nETA: 02 mars 2026",
    charges_usd=[
        ("Ocean Freight", "Fret de base 40'HC — tarif contractuel Q1 2026",     "1 EVP", "2 100,00"),
        ("BAF Q1 2026",   "Bunker Adjustment Factor — VLSFO ref. janv. 2026",   "1 EVP",   "290,00"),
        ("CAF",           "Currency Adjustment Factor — USD/EUR janv. 2026",     "1 EVP",    "38,00"),
    ],
    charges_eur=[
        ("THC ROTTERDAM", "Terminal Handling Charge — ECT Delta Rotterdam",      "1 EVP",   "185,00"),
        ("DOCUMENTATION", "Bill of Lading original + Telex Release + Surrender", "1 B/L",   "225,00"),
    ],
    totals=[
        ("Sous-total USD",        "2 428,00 USD"),
        ("Sous-total EUR",          "410,00 EUR"),
        ("TOTAL DU (equivalent)", "2 805,00 USD"),
    ],
    payment_note=(
        "Conteneur disponible au terminal Port 2000 Le Havre depuis le 04 mars 2026. "
        "Jours francs: 5 jours ouvres a partir de la date de disponibilite. "
        "Frais de surestaries en cas de depassement: 110 USD/jour/EVP."
    ),
)

# ---- 2. CMA CGM — BAF eleve (score 34%) ----
build_invoice(
    filename="facture_cmacgm_baf.pdf",
    carrier_name="CMA CGM",
    carrier_color=colors.HexColor("#003087"),
    carrier_addr="4 Quai d'Arenc  CS 81686  13235 Marseille Cedex 02, France  |  cmacgm.com",
    inv_no="CMA-FR-2026-198443",
    inv_date="28 fevrier 2026",
    due_date="30 mars 2026",
    bl="CMDU9876543210",
    booking="BKG-CMA-20260115-3389",
    container="CMAU1234567-0",
    ctype="20' Standard (DC)",
    bl_date="17 janvier 2026",
    bill_to="Textile Import France SARL\n45 Avenue du Commerce\n75015 Paris, France\nSIRET: 523 678 901 00034",
    shipper="Guangzhou Textile Group Co.\nNo.88 Zhongshan Ave, Tianhe\nGuangzhou 510620, Chine",
    pol="Shanghai / CNSHA\nSIPG Yangshan Terminal 4\nETD: 20 jan. 2026",
    pod="Le Havre / FRLEH\nPort 2000 — Terminal TL1\nETA: 18 fevr. 2026",
    charges_usd=[
        ("Ocean Freight", "Fret de base 20'DC — tarif contractuel Q1 2026",         "1 EVP", "1 850,00"),
        ("BAF Q1 2026",   "Bunker Adjustment Factor — VLSFO T1 2026",                "1 EVP",   "312,00"),
        ("GREEN LEVY ETS","EU Emissions Trading Scheme — prix EUA ref. B/L date",   "1 EVP",   "127,00"),
        ("PSS",           "Peak Season Surcharge — applicable oct. a janv. inclus", "1 EVP",    "85,00"),
        ("CAF",           "Currency Adjustment Factor — USD/EUR janv. 2026",         "1 EVP",    "43,00"),
    ],
    charges_eur=[
        ("THC LE HAVRE",  "Terminal Handling Charge — Port 2000 Terminal TL1",       "1 EVP",   "210,00"),
        ("DOCUMENTATION", "Bill of Lading + frais documentaires export/import",      "1 B/L",   "185,00"),
    ],
    totals=[
        ("Sous-total USD",        "2 417,00 USD"),
        ("Sous-total EUR",          "395,00 EUR"),
        ("TOTAL DU (equivalent)", "2 790,00 USD"),
    ],
    payment_note=(
        "Conteneur disponible au terminal Port 2000 depuis le 20 fevrier 2026. "
        "Jours francs: 7 jours ouvres. Frais de surestaries: 95 USD/jour a partir du 8eme jour. "
        "PSS applicable uniquement pour embarquements entre le 1er octobre et le 31 janvier."
    ),
)

# ---- 3. MSC — Surestaries (score 28%) ----
build_invoice(
    filename="facture_msc_surestaries.pdf",
    carrier_name="MSC — Mediterranean Shipping Co.",
    carrier_color=colors.HexColor("#0033A0"),
    carrier_addr="12-14 Chemin Rieu  CH-1208 Geneve, Suisse  |  Agent France: MSC France SAS, 75009 Paris",
    inv_no="MSC-FR-2026-087321",
    inv_date="05 mars 2026",
    due_date="04 avril 2026",
    bl="MEDUB1234567A",
    booking="BKG-MSC-20260110-8821",
    container="MSCU4567890-5",
    ctype="40' Standard (DC)",
    bl_date="14 janvier 2026",
    bill_to="Electroparts Distribution SA\n8 Zone Industrielle Sud\n13300 Salon-de-Provence, France\nSIRET: 398 012 345 00056",
    shipper="Ningbo Precision Parts Ltd\n188 Xinqi Industrial Park\nNingbo 315336, Chine",
    pol="Ningbo / CNNGB\nNingbo Zhoushan Port — Terminal 3\nETD: 17 jan. 2026",
    pod="Marseille Fos / FRFOS\nTerminal Fos-Distriport\nETA: 14 fevr. 2026",
    charges_usd=[
        ("Ocean Freight", "Fret de base 40' — tarif spot Q1 2026",                       "1 EVP", "1 620,00"),
        ("LSS / BAF",     "Low Sulphur Surcharge — VLSFO ref. janv. 2026",               "1 EVP",   "245,00"),
        ("ECA",           "Emission Control Area — zone SECA Mediterranee (applicab.)",  "1 EVP",    "78,00"),
        ("D&D DEMURRAGE", "Surestaries terminal: 8 jours x 75,00 USD/j/EVP",             "8 J",     "600,00"),
    ],
    charges_eur=[
        ("THC MARSEILLE", "Terminal Handling Charge — Fos-Distriport (tarif 2026)", "1 EVP",   "195,00"),
        ("DOCUMENTATION", "Connaissement original (3 OB/L) + Telex Release",        "1 B/L",   "170,00"),
    ],
    totals=[
        ("Sous-total USD",        "2 543,00 USD"),
        ("Sous-total EUR",          "365,00 EUR"),
        ("TOTAL DU (equivalent)", "2 890,00 USD"),
    ],
    payment_note=(
        "Detail surestaries: Arrivee terminal Fos: 15/02/2026 — Jours francs: 5 jours ouvres "
        "— Debut depassement: 21/02/2026 — Enlevement effectif: 04/03/2026 — Duree facturee: 8 jours. "
        "Note: week-end des 22-23/02 et 01-02/03 inclus dans le calcul (4 jours non ouvres non deduits)."
    ),
)

# ---- 4. Hapag-Lloyd — Multiples anomalies (score 52%) ----
build_invoice(
    filename="facture_hapag_anomalies.pdf",
    carrier_name="Hapag-Lloyd AG",
    carrier_color=colors.HexColor("#E2231A"),
    carrier_addr="Ballindamm 25  20095 Hamburg, Allemagne  |  Agent France: Hapag-Lloyd France SAS, 75008 Paris",
    inv_no="HL-FR-2026-512009",
    inv_date="20 mars 2026",
    due_date="19 avril 2026",
    bl="HLCU1234567890A",
    booking="BKG-HL-20260205-4412",
    container="HLXU9876543-2",
    ctype="40' High Cube (HC)",
    bl_date="10 fevrier 2026",
    bill_to="Lyon Industries Groupe SAS\n22 Rue de l'Industrie — ZI Ouest\n69800 Saint-Priest, France\nSIRET: 487 123 456 00012",
    shipper="Busan Manufacturing Corp.\n55 Gamcheon Industrial Road\nBusan 49241, Coree du Sud",
    pol="Busan / KRPUS\nBusan New Port — Terminal 3\nETD: 13 fevr. 2026",
    pod="Le Havre / FRLEH (via Hambourg)\nPort 2000 — Terminal TL2\nETA: 18 mars 2026",
    charges_usd=[
        ("Ocean Freight", "Fret de base 40'HC — tarif spot + surcharge transbord",  "1 EVP", "2 850,00"),
        ("BAF MARS 2026", "Bunker Adjustment Factor — VLSFO ref. Rotterdam T1 2026","1 EVP",   "510,00"),
        ("PSS",           "Peak Season Surcharge — applicable oct. a janv. inclus", "1 EVP",   "120,00"),
        ("ETS GREEN LEVY","EU Emissions Trading — EUA ref. date B/L 10/02/2026",   "1 EVP",   "198,00"),
        ("CAF",           "Currency Adjustment Factor — USD/EUR fevr. 2026",         "1 EVP",    "55,00"),
    ],
    charges_eur=[
        ("THC LE HAVRE",  "Terminal Handling Charge — Port 2000 TL2 (tarif 2026)",  "1 EVP",   "210,00"),
        ("DOCUMENTATION", "Bill of Lading + Surrender Fee + frais administratifs",  "1 B/L",   "215,00"),
    ],
    totals=[
        ("Sous-total USD",        "3 733,00 USD"),
        ("Sous-total EUR",          "425,00 EUR"),
        ("TOTAL DU (equivalent)", "4 185,00 USD"),
    ],
    payment_note=(
        "Transbordement effectue a Hambourg le 28/02/2026 (HLBU6543210). "
        "Conteneur disponible au Port 2000 Le Havre depuis le 20 mars 2026. "
        "Jours francs: 5 jours ouvres. PSS applicable uniquement pour embarquements oct.-janv."
    ),
)

print(f"\nTermine. 4 factures generees dans : {OUTPUT_DIR}")
