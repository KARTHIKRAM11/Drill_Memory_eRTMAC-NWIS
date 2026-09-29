"""
NWIS backend - FastAPI application.

Run with: uvicorn main:app --reload --port 8000
On first run, seeds the SQLite DB with synthetic wells/events and trains
the risk model automatically if not already present.
"""
import os
import math
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import SessionLocal, Well, DrillingEvent, Report, init_db
import base64

import seed_data
import ml_model
import extraction
import ocr

app = FastAPI(title="NWIS - Nearby Wells Intelligence System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # prototype only - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_REPORTS_DIR = os.path.join(os.path.dirname(__file__), "sample_reports")


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    well_count = db.query(Well).count()
    db.close()
    if well_count == 0:
        seed_data.seed()
    # ensure model exists / trained
    ml_model.load_model()


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def well_to_dict(w: Well):
    return {
        "id": w.id,
        "name": w.name,
        "field_name": w.field_name,
        "latitude": w.latitude,
        "longitude": w.longitude,
        "total_depth_m": w.total_depth_m,
        "spud_date": w.spud_date,
        "status": w.status,
        "formation_sequence": w.formation_sequence,
    }


def event_to_dict(e: DrillingEvent):
    return {
        "id": e.id,
        "well_id": e.well_id,
        "event_type": e.event_type,
        "depth_m": e.depth_m,
        "formation": e.formation,
        "severity": e.severity,
        "description": e.description,
        "mitigation": e.mitigation,
        "date": e.date,
    }


# ---------- Wells ----------

@app.get("/api/wells")
def list_wells():
    db = SessionLocal()
    wells = db.query(Well).all()
    result = [well_to_dict(w) for w in wells]
    db.close()
    return result


@app.get("/api/wells/nearby")
def nearby_wells(lat: float, lon: float, radius_km: float = 15, exclude_id: Optional[int] = None):
    db = SessionLocal()
    wells = db.query(Well).all()
    result = []
    for w in wells:
        if exclude_id and w.id == exclude_id:
            continue
        dist = haversine_km(lat, lon, w.latitude, w.longitude)
        if dist <= radius_km:
            d = well_to_dict(w)
            d["distance_km"] = round(dist, 2)
            result.append(d)
    db.close()
    result.sort(key=lambda x: x["distance_km"])
    return result


@app.get("/api/wells/{well_id}")
def well_detail(well_id: int):
    db = SessionLocal()
    w = db.query(Well).filter(Well.id == well_id).first()
    if not w:
        db.close()
        raise HTTPException(status_code=404, detail="Well not found")
    events = [event_to_dict(e) for e in w.events]
    reports = [{"id": r.id, "report_type": r.report_type, "filename": r.filename} for r in w.reports]
    result = well_to_dict(w)
    result["events"] = events
    result["reports"] = reports
    db.close()
    return result


@app.get("/api/wells/{well_id}/events")
def well_events(well_id: int):
    db = SessionLocal()
    events = db.query(DrillingEvent).filter(DrillingEvent.well_id == well_id).all()
    result = [event_to_dict(e) for e in events]
    db.close()
    return result


# ---------- Search (knowledge repository) ----------

@app.get("/api/search")
def search(q: str):
    if not q or len(q) < 2:
        return []
    db = SessionLocal()
    like = f"%{q}%"
    events = db.query(DrillingEvent).filter(
        or_(DrillingEvent.description.ilike(like),
            DrillingEvent.mitigation.ilike(like),
            DrillingEvent.formation.ilike(like),
            DrillingEvent.event_type.ilike(like))
    ).all()
    result = []
    for e in events:
        d = event_to_dict(e)
        d["well_name"] = e.well.name
        d["field_name"] = e.well.field_name
        result.append(d)
    db.close()
    return result


# ---------- Extraction ----------

@app.get("/api/sample_reports")
def list_sample_reports():
    return sorted(os.listdir(SAMPLE_REPORTS_DIR))


@app.get("/api/sample_reports/{filename}")
def get_sample_report_text(filename: str):
    """For .txt reports, returns raw text directly. For image reports,
    returns the image itself as a base64 data URL so the frontend can
    display the 'scanned document' before OCR runs on it."""
    path = os.path.join(SAMPLE_REPORTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    if filename.lower().endswith(".txt"):
        with open(path) as f:
            return {"filename": filename, "kind": "text", "raw_text": f.read()}
    else:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        ext = filename.rsplit(".", 1)[-1].lower()
        return {"filename": filename, "kind": "image", "image_data_url": f"data:image/{ext};base64,{b64}"}


@app.post("/api/extract")
async def extract_uploaded_report(file: UploadFile = File(...)):
    content = await file.read()
    try:
        text, was_ocr = ocr.extract_text_from_upload(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    extracted = extraction.extract_report(text)
    return {"filename": file.filename, "ocr_used": was_ocr, "raw_text": text, "extracted": extracted}


@app.post("/api/extract_sample/{filename}")
def extract_sample_report(filename: str):
    path = os.path.join(SAMPLE_REPORTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    with open(path, "rb") as f:
        content = f.read()
    try:
        text, was_ocr = ocr.extract_text_from_upload(filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    extracted = extraction.extract_report(text)
    return {"filename": filename, "ocr_used": was_ocr, "raw_text": text, "extracted": extracted}


# ---------- Cross-well correlation ----------

@app.get("/api/wells/{well_id}/formation_risk_profile")
def formation_risk_profile(well_id: int, radius_km: float = 15):
    """
    Correlates drilling events across every offset well within radius,
    grouped by formation and event type. This is the field-level
    "institutional memory" view: before spudding a well, an engineer can
    see which formations have historically caused the most trouble in
    this specific area, independent of any single active well's depth.
    """
    db = SessionLocal()
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        db.close()
        raise HTTPException(status_code=404, detail="Well not found")

    all_wells = db.query(Well).all()
    offset_ids = [w.id for w in all_wells if haversine_km(well.latitude, well.longitude, w.latitude, w.longitude) <= radius_km]

    events = db.query(DrillingEvent).filter(DrillingEvent.well_id.in_(offset_ids)).all()
    db.close()

    profile = {}
    for e in events:
        f = profile.setdefault(e.formation, {"total": 0, "by_type": {}, "by_severity": {"low": 0, "medium": 0, "high": 0}})
        f["total"] += 1
        f["by_type"][e.event_type] = f["by_type"].get(e.event_type, 0) + 1
        f["by_severity"][e.severity] = f["by_severity"].get(e.severity, 0) + 1

    ranked = sorted(profile.items(), key=lambda kv: kv[1]["total"], reverse=True)
    return {
        "well_id": well_id,
        "radius_km": radius_km,
        "offset_well_count": len(offset_ids) - 1,
        "formations": [{"formation": f, **stats} for f, stats in ranked],
    }


# ---------- Predictive risk ----------

class RiskRequest(BaseModel):
    formation: str
    depth_m: float
    rop_m_hr: float = 15.0
    mud_weight_sg: float = 1.2
    torque_knm: float = 18.0
    downhole_pressure_sg: float = 1.2
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: float = 15.0


@app.post("/api/predict/risk")
def predict_risk(req: RiskRequest):
    proba = ml_model.predict_risk(
        formation=req.formation,
        depth_m=req.depth_m,
        rop_m_hr=req.rop_m_hr,
        mud_weight_sg=req.mud_weight_sg,
        torque_knm=req.torque_knm,
        downhole_pressure_sg=req.downhole_pressure_sg,
    )

    # Pull similar historical events from offset wells: same formation,
    # within +/- 150m depth, optionally restricted to a geographic radius.
    db = SessionLocal()
    query = db.query(DrillingEvent).filter(
        DrillingEvent.formation == req.formation,
        DrillingEvent.depth_m.between(req.depth_m - 150, req.depth_m + 150),
    )
    candidate_events = query.all()

    similar = []
    for e in candidate_events:
        if req.lat is not None and req.lon is not None:
            dist = haversine_km(req.lat, req.lon, e.well.latitude, e.well.longitude)
            if dist > req.radius_km:
                continue
        else:
            dist = None
        d = event_to_dict(e)
        d["well_name"] = e.well.name
        d["field_name"] = e.well.field_name
        d["distance_km"] = round(dist, 2) if dist is not None else None
        similar.append(d)
    db.close()

    similar.sort(key=lambda x: abs(x["depth_m"] - req.depth_m))
    similar = similar[:5]

    risk_level = "high" if proba > 0.65 else "medium" if proba > 0.35 else "low"

    return {
        "risk_probability": round(proba, 3),
        "risk_level": risk_level,
        "similar_offset_events": similar,
        "recommendation": _recommend(risk_level, similar),
    }


def _recommend(risk_level: str, similar_events: List[dict]) -> str:
    if risk_level == "low" or not similar_events:
        return "No significant offset-well risk pattern detected at this depth/formation. Continue per standard drilling program."
    top = similar_events[0]
    return (
        f"Similar {top['event_type'].replace('_', ' ')} event recorded in offset well "
        f"{top['well_name']} at {top['depth_m']}m ({top['formation']}). "
        f"Suggested mitigation based on offset-well history: {top['mitigation']}"
    )


@app.get("/")
def root():
    return {"status": "ok", "service": "NWIS backend"}
