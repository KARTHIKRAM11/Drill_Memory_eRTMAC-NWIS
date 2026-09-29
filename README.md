# eRTMAC-NWIS — Nearby Wells Intelligence System
### SIH 2026 Prototype · Oil India Limited · Problem Statement 26121

An AI-powered offset well knowledge and decision-support platform that sits
alongside eRTMAC, giving drilling teams instant access to nearby wells,
historical drilling events, and proactive risk alerts based on offset-well
history.

## What's actually implemented (not mocked)

| Requirement from PS | Status |
|---|---|
| Geospatial map of nearby wells within a radius | ✅ Real haversine radius query + Leaflet map |
| Searchable knowledge repository of drilling events | ✅ Real full-text search over SQLite |
| AI/NLP/OCR extraction from historical reports | ✅ **Real Tesseract OCR** on a scanned report image, feeding a regex/section-based NLP extraction pipeline |
| Correlate drilling data across wells by depth/formation | ✅ Two correlation views: per-prediction similar-event lookup, and a field-wide formation risk profile aggregated across every offset well in radius |
| Predictive analytics for drilling risk | ✅ Real RandomForest classifier (scikit-learn), trained on domain-patterned synthetic data, 96%+ test AUC |
| Real-time alerts & recommendations | ✅ Live drilling simulation triggers alerts as depth crosses risky intervals |
| Dashboard for field/office personnel | ✅ React dashboard, 4 tabs |
| Live eRTMAC data stream integration | 🔶 Simulated (documented as the integration point — see below) |

Being upfront about the 🔶 item is intentional: judges know a prototype
round can't have real OIL data access. What's real here is the AI pipeline,
the ML model, and the correlation logic — that's what should be defended in
Q&A.

## Architecture

```
┌─────────────────┐      REST/JSON      ┌──────────────────────┐
│  React Frontend │ ◄──────────────────► │   FastAPI Backend     │
│  (Leaflet map,  │                      │                        │
│   dashboard)    │                      │  ┌──────────────────┐  │
└─────────────────┘                      │  │ extraction.py     │  │
                                          │  │ (NLP/regex        │  │
                                          │  │  section parser)  │  │
                                          │  └──────────────────┘  │
                                          │  ┌──────────────────┐  │
                                          │  │ ml_model.py       │  │
                                          │  │ (RandomForest      │  │
                                          │  │  risk classifier)  │  │
                                          │  └──────────────────┘  │
                                          │  ┌──────────────────┐  │
                                          │  │ SQLite (wells,     │  │
                                          │  │ events, reports)   │  │
                                          │  └──────────────────┘  │
                                          └──────────────────────┘
```

Production swap-ins: SQLite → PostGIS (native spatial radius queries),
regex extraction → fine-tuned NER model behind Tesseract OCR, synthetic
training data → real DDR/WCR time-series labeled with actual NPT events.

## Setup & Run

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate     # optional but recommended
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
First run auto-seeds ~28 synthetic wells (~115 historical events) around
OIL's Upper Assam fields (Duliajan, Naharkatiya, Moran, Lakwa, Kumchai,
Jorajan) and trains the risk model (takes a few seconds).

Backend runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173` and proxies `/api` calls to the backend.

## Demo script (for judges)

1. **Offset Well Map tab** — click any well marker. Side panel shows its
   formation sequence and full historical event timeline. Drag the radius
   slider to show nearby offset wells appearing/disappearing live.
2. **Knowledge Search tab** — search "stuck pipe" or "Barail Group" to show
   the searchable institutional-memory repository across all wells.
3. **Document Extraction tab** — select `LAK-003_DDR_scanned.png` (a
   synthetic scanned report image) and click "Run OCR + AI Extraction."
   You'll see all three real stages side by side: the scanned image →
   Tesseract's raw OCR output (including its natural imperfections) →
   the structured JSON. This is your strongest technical proof point:
   it's genuinely running OCR, not narrating that OCR "would" happen.
   Switch to the two `.txt` reports to show the same parser handling
   clean digital input.
4. **Predictive Risk & Alerts tab** — this is the closing "wow" moment.
   Select an active well, set formation to "Barail Group," click
   **"Start live drilling simulation."** Watch the depth increase and the
   risk gauge climb; when it crosses into the red zone, the alert banner
   fires with a specific offset-well precedent and mitigation — exactly the
   proactive alert the problem statement asks for.

## OCR pipeline (`ocr.py`)

Real Tesseract OCR, not a stub. `ocr.py` dispatches by file type: `.txt`
reports skip straight to `extraction.py`; `.png`/`.jpg`/`.pdf` reports go
through `pytesseract.image_to_string()` (PDFs via `pdf2image` page
rasterization) first, then a light post-OCR normalization pass fixes the
character confusions Tesseract commonly makes on numeric text (0/o, 5/s)
before the same downstream extraction logic runs. `generate_scan_sample.py`
regenerates the demo's synthetic scanned report image if you want to try a
different source text or noise level.

Try it yourself: `POST /api/extract` accepts any `.txt`, `.png`, `.jpg` or
`.pdf` file upload — you can drop in your own scanned report image via the
`/docs` Swagger UI at `http://localhost:8000/docs` and watch it OCR live.

## Correlation across offset wells

Two distinct correlation views, both real queries (not mocked):
- **Per-prediction**: `/api/predict/risk` finds historical events in the
  same formation within a ±150m depth window across every well in the
  chosen radius, ranked by proximity to the queried depth.
- **Field-wide**: `/api/wells/{id}/formation_risk_profile` aggregates
  every offset-well event by formation and event type across the whole
  radius — the "what has historically gone wrong here, regardless of any
  one well's depth" view, shown on the map tab's side panel.

## Notes on the data

All well names, coordinates (jittered around real OIL field locations),
dates, and events are synthetic, generated for demo purposes only. The risk
model is trained on a synthetic dataset built from domain-informed rules
(deeper Barail Group intervals + low mud weight + high torque → higher
risk) plus noise — this produces a genuinely learnable pattern for the
classifier rather than random labels, while being transparent that it is
not trained on real OIL well data.
