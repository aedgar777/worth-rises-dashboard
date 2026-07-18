from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.enrichment import enrich_results_with_places
from app.jurisdictions import jurisdiction_count, load_jurisdictions
from app.jurisdictions_db import get_jurisdictions_db, init_jurisdictions_db, seed_jurisdictions_from_csv
from app.models import MatchedRate, ProviderFacility, Upload
from app.places import PlacesClient
from app.transform.columns import normalize_raw_columns
from app.transform.matcher import match_jurisdictions
import logging
import pandas as pd
import io
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Worth Rises Telecom Matcher", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_places_client() -> PlacesClient:
    return PlacesClient(api_key=settings.google_places_api_key)


def _persist_provider_facilities(
    db: Session,
    upload_id: int,
    raw_df: pd.DataFrame,
) -> int:
    normalized = normalize_raw_columns(raw_df.copy())
    count = 0
    for _, row in normalized.iterrows():
        facility_name = str(row.get("facility_name", "") or "").strip()
        if not facility_name:
            continue
        state = str(row.get("state", "") or "").upper().strip()[:2]
        if not state:
            continue
        county_val = row.get("county")
        county = None
        if county_val is not None and not pd.isna(county_val):
            county_str = str(county_val).strip()
            county = county_str or None
        facility_id_val = row.get("facility_id")
        facility_id = None
        if facility_id_val is not None and not pd.isna(facility_id_val):
            facility_id = str(facility_id_val).strip() or None

        db.add(
            ProviderFacility(
                upload_id=upload_id,
                state=state,
                county=county,
                facility_id=facility_id,
                facility_name=facility_name,
                provider=str(row.get("provider") or "") or None,
                in_state_rate=_optional_float(row.get("in_state_rate")),
                out_of_state_rate=_optional_float(row.get("out_of_state_rate")),
                facility_address=None,
            )
        )
        count += 1
    return count


def _enrich_facility_addresses(
    db: Session,
    rows: list[ProviderFacility],
    places: PlacesClient,
) -> int:
    if not places.enabled:
        return 0

    pending = [row for row in rows if not row.facility_address]
    if pending:
        place_results = places.lookup_many(
            [(row.facility_name, row.state, row.county) for row in pending]
        )
        enriched = 0
        for row, place in zip(pending, place_results):
            if place and place.formatted_address:
                row.facility_address = place.formatted_address
                enriched += 1
    else:
        enriched = 0

    if enriched:
        db.commit()
    return enriched


def _optional_float(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _delete_previous_uploads(db: Session, keep_upload_id: int) -> int:
    """Remove all uploads except the current one to limit Cloud SQL storage."""
    old_ids = [
        row[0] for row in db.query(Upload.id).filter(Upload.id != keep_upload_id).all()
    ]
    if not old_ids:
        return 0

    db.query(MatchedRate).filter(MatchedRate.upload_id.in_(old_ids)).delete(
        synchronize_session=False
    )
    db.query(ProviderFacility).filter(ProviderFacility.upload_id.in_(old_ids)).delete(
        synchronize_session=False
    )
    deleted = (
        db.query(Upload).filter(Upload.id.in_(old_ids)).delete(synchronize_session=False)
    )
    db.commit()
    logger.info(
        "Deleted previous uploads: count=%d kept_upload_id=%d",
        deleted,
        keep_upload_id,
    )
    return deleted


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    init_jurisdictions_db()
    downloads_csv = (
        Path.home()
        / "Downloads"
        / "2026.07 - Staff Technologist Data Test (for applicant) v2 - Jurisdictions to Match.csv"
    )
    seed_jurisdictions_from_csv(downloads_csv if downloads_csv.exists() else None)


@app.get("/health")
def health(jdb: Session = Depends(get_jurisdictions_db)) -> dict:
    return {
        "status": "ok",
        "places_api": bool(settings.google_places_api_key),
        "jurisdictions_in_db": jurisdiction_count(jdb),
    }


@app.post("/api/process")
async def process_csv(
    raw_provider: UploadFile = File(...),
    db: Session = Depends(get_db),
    jdb: Session = Depends(get_jurisdictions_db),
) -> dict:
    started = time.perf_counter()
    logger.info("Upload started: filename=%s", raw_provider.filename)

    try:
        jurisdictions_df = load_jurisdictions(jdb)
        raw_df = pd.read_csv(io.BytesIO(await raw_provider.read()))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {exc}") from exc

    logger.info(
        "CSV parsed: rows=%d jurisdictions=%d elapsed=%.2fs",
        len(raw_df),
        len(jurisdictions_df),
        time.perf_counter() - started,
    )

    upload = Upload(
        filename=raw_provider.filename or "raw-provider.csv",
        status="processing",
        jurisdiction_count=len(jurisdictions_df),
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    places = get_places_client()

    try:
        step = time.perf_counter()
        results = match_jurisdictions(jurisdictions_df, raw_df, places=places)
        logger.info(
            "Matching complete: results=%d elapsed=%.2fs",
            len(results),
            time.perf_counter() - step,
        )

        step = time.perf_counter()
        enrich_results_with_places(results, places)
        logger.info("Places enrichment complete: elapsed=%.2fs", time.perf_counter() - step)

        step = time.perf_counter()
        facility_count = _persist_provider_facilities(db, upload.id, raw_df)
        logger.info(
            "Provider facilities persisted: count=%d elapsed=%.2fs",
            facility_count,
            time.perf_counter() - step,
        )
    except ValueError as exc:
        upload.status = "failed"
        db.commit()
        logger.exception("Upload failed during processing: upload_id=%s", upload.id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    step = time.perf_counter()
    matched_count = 0
    for result in results:
        if result.match_status == "matched":
            matched_count += 1
        db.add(
            MatchedRate(
                upload_id=upload.id,
                jurisdiction_type=result.jurisdiction_type,
                state=result.state,
                county=result.county,
                facility_name=result.facility_name,
                provider=result.provider,
                in_state_rate=result.in_state_rate,
                out_of_state_rate=result.out_of_state_rate,
                match_status=result.match_status,
                match_confidence=result.match_confidence,
                notes=result.notes,
                facility_rules=result.facility_rules,
                latitude=result.latitude,
                longitude=result.longitude,
                place_id=result.place_id,
                place_description=result.place_description,
            )
        )

    upload.status = "complete"
    upload.matched_count = matched_count
    db.commit()
    _delete_previous_uploads(db, upload.id)
    logger.info(
        "Results saved: rows=%d elapsed=%.2fs",
        len(results),
        time.perf_counter() - step,
    )
    logger.info(
        "Upload complete: upload_id=%d matched=%d elapsed=%.2fs",
        upload.id,
        matched_count,
        time.perf_counter() - started,
    )

    return {
        "upload_id": upload.id,
        "jurisdiction_count": upload.jurisdiction_count,
        "matched_count": matched_count,
        "review_count": sum(1 for r in results if r.match_status == "review"),
        "unmatched_count": sum(1 for r in results if r.match_status == "unmatched"),
    }


@app.get("/api/uploads")
def list_uploads(db: Session = Depends(get_db)) -> list[dict]:
    uploads = db.query(Upload).order_by(Upload.created_at.desc()).limit(20).all()
    return [
        {
            "id": u.id,
            "filename": u.filename,
            "status": u.status,
            "jurisdiction_count": u.jurisdiction_count,
            "matched_count": u.matched_count,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in uploads
    ]


@app.get("/api/uploads/{upload_id}/results")
def get_results(upload_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = (
        db.query(MatchedRate)
        .filter(MatchedRate.upload_id == upload_id)
        .order_by(MatchedRate.state, MatchedRate.county)
        .all()
    )
    if not rows:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        return []

    return [
        {
            "id": r.id,
            "jurisdiction_type": r.jurisdiction_type,
            "state": r.state,
            "county": r.county,
            "facility_name": r.facility_name,
            "provider": r.provider,
            "in_state_rate": r.in_state_rate,
            "out_of_state_rate": r.out_of_state_rate,
            "match_status": r.match_status,
            "match_confidence": r.match_confidence,
            "notes": r.notes,
            "facility_rules": r.facility_rules,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "place_id": r.place_id,
            "place_description": r.place_description,
        }
        for r in rows
    ]


@app.get("/api/uploads/{upload_id}/summary")
def get_summary(upload_id: int, db: Session = Depends(get_db)) -> dict:
    rows = db.query(MatchedRate).filter(MatchedRate.upload_id == upload_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No results for upload")

    rates_in = [r.in_state_rate for r in rows if r.in_state_rate is not None]
    rates_out = [r.out_of_state_rate for r in rows if r.out_of_state_rate is not None]

    by_state: dict[str, dict] = {}
    for r in rows:
        bucket = by_state.setdefault(
            r.state,
            {"state": r.state, "matched": 0, "review": 0, "unmatched": 0, "avg_in_state": None},
        )
        bucket[r.match_status] = bucket.get(r.match_status, 0) + 1

    for state, bucket in by_state.items():
        state_rates = [r.in_state_rate for r in rows if r.state == state and r.in_state_rate is not None]
        bucket["avg_in_state"] = round(sum(state_rates) / len(state_rates), 4) if state_rates else None

    return {
        "total": len(rows),
        "matched": sum(1 for r in rows if r.match_status == "matched"),
        "review": sum(1 for r in rows if r.match_status == "review"),
        "unmatched": sum(1 for r in rows if r.match_status == "unmatched"),
        "avg_in_state_rate": round(sum(rates_in) / len(rates_in), 4) if rates_in else None,
        "avg_out_of_state_rate": round(sum(rates_out) / len(rates_out), 4) if rates_out else None,
        "by_state": list(by_state.values()),
    }


@app.get("/api/uploads/{upload_id}/facility-states")
def get_facility_states(upload_id: int, db: Session = Depends(get_db)) -> list[str]:
    rows = (
        db.query(ProviderFacility.state)
        .filter(ProviderFacility.upload_id == upload_id)
        .distinct()
        .order_by(ProviderFacility.state)
        .all()
    )
    if not rows:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        return []
    return [row[0] for row in rows]


@app.get("/api/uploads/{upload_id}/facilities")
def get_facilities(
    upload_id: int,
    state: str,
    db: Session = Depends(get_db),
    places: PlacesClient = Depends(get_places_client),
) -> list[dict]:
    state_code = state.upper().strip()[:2]
    started = time.perf_counter()
    rows = (
        db.query(ProviderFacility)
        .filter(
            ProviderFacility.upload_id == upload_id,
            ProviderFacility.state == state_code,
        )
        .order_by(ProviderFacility.facility_name)
        .all()
    )
    if not rows:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        return []

    enriched = _enrich_facility_addresses(db, rows, places)
    if enriched:
        logger.info(
            "Facility addresses enriched: upload_id=%d state=%s count=%d elapsed=%.2fs",
            upload_id,
            state_code,
            enriched,
            time.perf_counter() - started,
        )

    return [
        {
            "id": row.id,
            "state": row.state,
            "county": row.county,
            "facility_id": row.facility_id,
            "facility_name": row.facility_name,
            "provider": row.provider,
            "in_state_rate": row.in_state_rate,
            "out_of_state_rate": row.out_of_state_rate,
            "facility_address": row.facility_address,
        }
        for row in rows
    ]
