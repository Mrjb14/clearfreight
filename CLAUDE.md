# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

ClearFreight is a SaaS tool that automatically verifies maritime freight invoices before payment. It detects anomalies (overbilling, incorrect surcharges, contestable demurrage), quantifies the recoverable amount, and generates an audit report. Target users: French SMEs and freight forwarders.

The current state is a single-file HTML MVP (`clearfreight.html`) used to validate the concept. The planned product is a full-stack app (FastAPI + React + Claude API).

The product sheet is in `ClearFreight_Fiche_Produit.docx`.

## Running the current MVP

Open `clearfreight.html` directly in a browser. No server, no dependencies beyond Google Fonts.

```
npx live-server .
# or
python -m http.server 8080
```

## Planned stack (next prototype)

| Layer | Tech |
|---|---|
| Backend API | Python · FastAPI |
| Database | PostgreSQL |
| Async jobs | Redis |
| Frontend | React |
| PDF parsing | Claude API (Anthropic) + Tesseract / AWS Textract |
| Scraping | Custom (terminal portals: Le Havre, Marseille…) |

## Analysis pipeline (3 layers)

**Layer 1 — Parsing**: PDF → OCR → LLM extraction (Claude API) → validated JSON via regex → carrier mapping dictionary (MSC, CMA-CGM, Maersk, Hapag-Lloyd each use different codes for the same charges). The mapping dictionary is an editorial asset, not ML.

**Layer 2 — Verification**: Line-by-line comparison against reference values:
- Ocean freight base: checked against Freightos Baltic Index (FBX) — detects anomalies at +40%, not +12%
- BAF (fuel surcharge): formula varies by carrier and is not officially published — must be reverse-engineered from accumulated client invoices
- THC, B/L fees: compared to known port tariffs

**Layer 3 — Demurrage (D&D)**: Reconstructs real container timeline (terminal arrival, availability, pickup) vs contracted free days to validate or contest the billed amount. Scraping terminal portals is the most fragile layer — the robust alternative is letting clients forward carrier notification emails into ClearFreight.

## Domain vocabulary

- **BAF** — Bunker Adjustment Factor (fuel surcharge)
- **CAF** — Currency Adjustment Factor
- **PSS** — Peak Season Surcharge (only applicable Oct–Jan)
- **ETS / Green Levy** — EU carbon market surcharge
- **THC** — Terminal Handling Charge
- **D&D / Surestaries** — Demurrage & Detention (75–300 $/day/container depending on port and carrier)
- **FBX** — Freightos Baltic Index (public ocean freight rate benchmark)
- **B/L** — Bill of Lading

## Key business figures (from product sheet)

- 5–8% of freight invoices contain errors in non-automated programs
- 3–5% of annual freight budget lost to undetected errors
- $15.4B in D&D fees collected by 9 carriers (2020–2025) — source: Federal Maritime Commission (fmc.gov)
- 22% of invoices require manual intervention (Ardent Partners 2025)
- Average cost to correct one error: $53.50 (IOFM 2025)

## Current HTML file architecture

Everything in `clearfreight.html` — HTML, CSS (`<style>`), and JS (`<script>`). No external JS dependencies.

**UI flow:**
1. User selects or drags a PDF onto the upload zone
2. `onFileSelected()` enables the analyze button
3. `runAnalysis()` shows a fake progress bar with timed steps
4. `showResult()` renders hardcoded demo data (CMA CGM · Shanghai → Le Havre · Q1 2026)

**The analysis is entirely simulated** — no PDF parsing, no API calls. All result data is hardcoded in `showResult()`. The "Générer le rapport PDF" button is a placeholder (`alert()`).

## Design tokens

CSS custom properties on `:root`: `--navy` (#0A1628), `--accent` (#00C896 green), `--blue` (#1A56DB). Semantic: `--danger`, `--warn`, `--success`. Fonts: Sora (headings/numbers) and Inter (body) from Google Fonts.

## Critical implementation notes

- LLM extraction of invoice amounts **must** be validated by regex post-extraction — hallucination risk on numeric values is non-negotiable to handle
- Carrier surcharge code mapping (e.g. "ECA" at Maersk = "LSS" at MSC) requires a manually maintained dictionary — this is editorial work, not ML
- Terminal portal scraping breaks frequently — plan for email forwarding as a fallback data source for D&D verification
