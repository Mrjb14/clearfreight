import copy
import hashlib
import io
import json
import os
import re
import random
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from scenarios import SCENARIOS

# Optional Claude API — graceful fallback if key missing or package absent
try:
    import anthropic
    from pypdf import PdfReader
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

CLAUDE_ENABLED = _ANTHROPIC_AVAILABLE and bool(os.getenv("ANTHROPIC_API_KEY"))

app = FastAPI(title="ClearFreight API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

LEADS_FILE = "leads.json"

# ──────────────────────────────────────────────
# Scenario selection
# ──────────────────────────────────────────────

def pick_by_filename(filename: str) -> dict:
    name = filename.lower()
    if any(k in name for k in ["msc", "surestarie", "dnd", "demurrage"]):
        return SCENARIOS[2]
    if any(k in name for k in ["hapag", "multi", "probleme"]):
        return SCENARIOS[3]
    if any(k in name for k in ["maersk", "normale"]):
        return SCENARIOS[0]
    if any(k in name for k in ["cma", "baf", "cmacgm"]):
        return SCENARIOS[1]
    idx = int(hashlib.md5(filename.encode()).hexdigest(), 16) % len(SCENARIOS)
    return SCENARIOS[idx]


def pick_by_carrier(carrier: str) -> dict | None:
    c = carrier.lower()
    if "msc" in c or "mediterranean" in c:
        return SCENARIOS[2]
    if "hapag" in c:
        return SCENARIOS[3]
    if "maersk" in c:
        return SCENARIOS[0]
    if "cma" in c:
        return SCENARIOS[1]
    return None


# ──────────────────────────────────────────────
# Phase 3 — Amount variation ±5%
# ──────────────────────────────────────────────

_AMT_PAT = re.compile(r"^([\d\s]+)\s*(USD|EUR)$")


def vary_amounts(scenario: dict) -> dict:
    """Deep-copy scenario and vary each USD/EUR amount by ±5%."""
    data = copy.deepcopy(scenario)
    for line in data["lines"]:
        m = _AMT_PAT.match(line["amount"])
        if m:
            num = int(m.group(1).replace(" ", ""))
            varied = round(num * (1 + random.uniform(-0.05, 0.05)))
            formatted = f"{varied:,}".replace(",", " ")
            line["amount"] = f"{formatted} {m.group(2)}"
    return data


# ──────────────────────────────────────────────
# Phase 4 — Claude API extraction
# ──────────────────────────────────────────────

async def extract_carrier_from_pdf(pdf_bytes: bytes) -> str | None:
    """Extract carrier name from PDF text using Claude. Returns None on any failure."""
    if not CLAUDE_ENABLED:
        return None
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages[:2])
        if not text.strip():
            return None

        client = anthropic.Anthropic()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": (
                    "Extract only the shipping carrier company name from this freight invoice. "
                    "Reply with ONLY the carrier name (e.g. 'MSC', 'Maersk', 'CMA CGM', 'Hapag-Lloyd'). "
                    "No explanation, no punctuation.\n\n"
                    f"{text[:3000]}"
                ),
            }],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None


# ──────────────────────────────────────────────
# PDF report generation
# ──────────────────────────────────────────────

def build_pdf(data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    navy   = colors.HexColor("#0A1628")
    green  = colors.HexColor("#10B981")
    orange = colors.HexColor("#F59E0B")
    red    = colors.HexColor("#EF4444")
    gray   = colors.HexColor("#4B5563")
    light  = colors.HexColor("#F9FAFB")
    white  = colors.white

    T = ParagraphStyle("T", fontName="Helvetica-Bold", fontSize=22, textColor=navy, spaceAfter=2)
    S = ParagraphStyle("S", fontName="Helvetica",      fontSize=11, textColor=gray, spaceAfter=16)
    H = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=11, textColor=navy, spaceAfter=6, spaceBefore=14)
    B = ParagraphStyle("B", fontName="Helvetica",      fontSize=10, textColor=colors.HexColor("#1F2937"), leading=16)
    F = ParagraphStyle("F", fontName="Helvetica",      fontSize=8,  textColor=colors.HexColor("#9CA3AF"), alignment=1)

    score = data["score"]
    score_color = green if score < 15 else orange if score < 30 else red
    score_label = "Faible" if score < 15 else "Modere" if score < 30 else "Eleve"
    route = data["route"].replace("→", ">")

    story = [
        Paragraph("ClearFreight", T),
        Paragraph("Rapport d'analyse de facture de fret maritime", S),
        Paragraph("Informations generales", H),
    ]

    info_rows = [
        ["Transporteur",              data["carrier"]],
        ["Route",                     route],
        ["Periode",                   data["period"]],
        ["Score de surfacturation",   f"{score}% - Risque {score_label}"],
        ["Anomalies detectees",       f"{data['anomalies_count']} anomalie(s) sur {len(data['lines'])} lignes"],
        ["Montant recuperable estime", data["recoverable"]],
    ]

    info_table = Table(info_rows, colWidths=[5.5 * cm, 11 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",       (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",       (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",      (0, 0), (0, -1), gray),
        ("TEXTCOLOR",      (1, 0), (1, -1), colors.HexColor("#1F2937")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [light, white]),
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("TEXTCOLOR",      (1, 3), (1, 3), score_color),
        ("FONTNAME",       (1, 3), (1, 3), "Helvetica-Bold"),
        ("TEXTCOLOR",      (1, 5), (1, 5), score_color),
        ("FONTNAME",       (1, 5), (1, 5), "Helvetica-Bold"),
    ]))
    story.append(info_table)
    story.append(Paragraph("Detail ligne par ligne", H))

    STATUS_LABEL = {"ok": "Conforme", "warn": "Attention", "err": "Anomalie"}
    STATUS_COLOR = {"ok": green, "warn": orange, "err": red}

    rows = [["Code", "Description", "Montant", "Statut"]]
    for line in data["lines"]:
        rows.append([line["code"], line["desc"], line["amount"], STATUS_LABEL[line["status"]]])

    lines_table = Table(rows, colWidths=[4 * cm, 7 * cm, 2.5 * cm, 2.5 * cm], repeatRows=1)
    ts = [
        ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("BACKGROUND",     (0, 0), (-1, 0), navy),
        ("TEXTCOLOR",      (0, 0), (-1, 0), white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [light, white]),
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
        ("GRID",           (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
    ]
    for i, line in enumerate(data["lines"], 1):
        ts += [
            ("TEXTCOLOR", (3, i), (3, i), STATUS_COLOR[line["status"]]),
            ("FONTNAME",  (3, i), (3, i), "Helvetica-Bold"),
        ]
    lines_table.setStyle(TableStyle(ts))
    story.append(lines_table)

    story.append(Paragraph("Synthese", H))
    clean = re.sub(r"<[^>]+>", "", data["summary"])
    story.append(Paragraph(clean, B))
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph(
        "ClearFreight - Prototype MVP 2026  |  Donnees simulees a des fins de demonstration  |  Aucune donnee conservee",
        F,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# ──────────────────────────────────────────────
# Contestation email generation
# ──────────────────────────────────────────────

def build_contestation_email(data: dict) -> str:
    today = datetime.now().strftime("%d %B %Y")

    anomaly_lines = [l for l in data["lines"] if l["status"] in ("err", "warn")]

    def clean_verdict(v: str) -> str:
        # Strip everything before the first letter, digit, or +/- sign
        return re.sub(r"^[^\w+\-]+", "", v, flags=re.UNICODE).strip()

    items = "\n".join(
        f"  - {l['code']} ({l['amount']}) : {clean_verdict(l['verdict'])}"
        for l in anomaly_lines
    )

    has_errors = any(l["status"] == "err" for l in anomaly_lines)
    tone = "mettons en demeure" if has_errors else "demandons"

    return f"""Objet : Contestation de facturation — {data['carrier']} — {data['anomalies_count']} anomalie(s) — Recuperable : {data['recoverable']}

Madame, Monsieur,

Suite a la reception de votre facture relative au transport {data['route']} ({data['period']}), nous avons procede a un audit independant de vos charges.

Cet audit a mis en evidence {data['anomalies_count']} anomalie(s) de facturation pour un montant total contestable estime a {data['recoverable']} :

CHARGES CONTESTEES :
{items}

Par la presente, nous vous {tone} d'emettre sans delai une note de credit ou une facture rectificative a hauteur de {data['recoverable']}.

Nous vous saurions gre de bien vouloir traiter cette demande dans un delai de 15 jours ouvres a compter de la reception du present courrier. A defaut de reponse satisfaisante dans ce delai, nous nous verrons contraints de :
  - suspendre le reglement du montant conteste
  - saisir le mediateur sectoriel competent
  - deposer une plainte aupres de la Federal Maritime Commission (routes US/EU concernees)

Nous restons a votre disposition pour tout echange ou complement d'information.

Veuillez agreer, Madame, Monsieur, l'expression de nos sinceres salutations.

---
[Votre nom et prenom]
[Votre fonction]
[Votre entreprise]
Date : {today}"""


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

_HTML = Path(__file__).parent.parent / "clearfreight.html"


@app.get("/")
async def serve_frontend():
    return FileResponse(_HTML, media_type="text/html")


@app.get("/health")
async def health():
    return {"status": "ok", "claude_enabled": CLAUDE_ENABLED}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Seuls les fichiers PDF sont acceptes."})

    pdf_bytes = await file.read()

    # Phase 4: Claude extracts carrier from PDF content
    scenario = None
    carrier = await extract_carrier_from_pdf(pdf_bytes)
    if carrier:
        scenario = pick_by_carrier(carrier)

    # Fallback: filename-based selection
    if scenario is None:
        scenario = pick_by_filename(file.filename)

    # Phase 3: Apply ±5% amount variation
    result = vary_amounts(scenario)
    return JSONResponse(content=result)


@app.post("/leads")
async def save_lead(data: dict):
    email = data.get("email", "").strip()
    if not email or "@" not in email:
        return JSONResponse(status_code=400, content={"error": "Email invalide"})

    leads = []
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE) as f:
            try:
                leads = json.load(f)
            except Exception:
                leads = []

    leads.append({"email": email, "timestamp": datetime.now().isoformat()})
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2)

    return {"ok": True}


@app.post("/report")
async def generate_report(data: dict):
    pdf_bytes = build_pdf(data)
    carrier = data.get("carrier", "rapport").lower().replace(" ", "-")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=clearfreight-{carrier}.pdf"},
    )


@app.post("/contestation")
async def get_contestation(data: dict):
    email_text = build_contestation_email(data)
    return {"email": email_text}
