from fastapi import Depends, FastAPI, HTTPException

from api.core.db import get_db
from api.models.schemas import ScanOut, UrlScanIn
from api.repositories.scans_repo import (
    get_report_by_scan_id,
    get_scan_by_id,
    get_signals_by_scan_id,
    insert_report,
    insert_scan,
    insert_signals,
)
from api.services.report_builder import build_report
from api.services.risk_engine import (
    ENGINE_VERSION,
    RULESET_VERSION,
    compute_url_risk,
    verdict_from_score,
)
from api.services.url_normalizer import normalize_url

app = FastAPI(title="Verifiko API", version="0.3.1")


@app.get("/health")
def health(db=Depends(get_db)):
    """Health check"""
    return {"status": "ok"}


@app.post("/scan/url", response_model=ScanOut)
def scan_url(request: UrlScanIn, db=Depends(get_db)):
    """Escanea una URL"""
    try:
        # la función de normalización ahora devuelve (url, metadata)
        normalized_url, metadata = normalize_url(request.url)

        # puede devolver 2 o 3 elementos, el segundo
        # valor siempre son los nombres de las señales raw/derive.
        result = compute_url_risk(normalized_url, metadata)
        if isinstance(result, tuple):
            if len(result) == 3:
                score, raw_flags, derived_signals = result
                signal_names = raw_flags + derived_signals
            elif len(result) == 2:
                score, signal_names = result
                raw_flags = []
                derived_signals = []
            else:
                raise ValueError(
                    "compute_url_risk retornó tupla de longitud inesperada"
                )
        else:
            raise ValueError("compute_url_risk retornó tipo inesperado")

        # convertir al formato que espera el repositorio
        signals_for_db = [(name, "true") for name in signal_names]
        signals_for_report = [{"name": name, "value": "true"} for name in signal_names]

        verdict = verdict_from_score(score)

        scan = insert_scan(db, request.url, normalized_url, score, verdict)
        insert_signals(db, scan.id, signals_for_db)

        report_data = build_report(
            signals_for_report,
            score,
            verdict,
            raw_flags=raw_flags,
            derived_signals=derived_signals,
        )
        insert_report(
            db,
            scan.id,
            report_data["summary"],
            report_data["recommendations"],
            report_data.get("confidence_notes", ""),
        )

        # pydantic ScanOut acepta sólo str; forzamos conversión aquí
        created_at = scan.created_at
        # usar str() directamente para evitar dependencias externas
        created_at = (
            created_at.isoformat()
            if hasattr(created_at, "isoformat")
            else str(created_at)
        )

        return ScanOut(
            id=str(scan.id),
            status="completed",
            score=scan.score,
            verdict=scan.verdict,
            created_at=created_at,
            engine_version=ENGINE_VERSION,
            ruleset_version=RULESET_VERSION,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/scan/{scan_id}")
def get_scan(scan_id: int, db=Depends(get_db)):
    """Obtiene resultado del escaneo"""
    scan = get_scan_by_id(db, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return {
        "id": scan.id,
        "input_url": scan.input_url,
        "normalized_url": scan.normalized_url,
        "score": scan.score,
        "verdict": scan.verdict,
        "created_at": scan.created_at,
        "engine_version": ENGINE_VERSION,
        "ruleset_version": RULESET_VERSION,
    }


@app.get("/scan/{scan_id}/signals")
def get_signals(scan_id: int, db=Depends(get_db)):
    """Obtiene señales del escaneo"""
    signals = get_signals_by_scan_id(db, scan_id)
    return {
        "scan_id": scan_id,
        "signals": [{"name": s.name, "value": s.value} for s in signals],
    }


@app.get("/scan/{scan_id}/report")
def get_report(scan_id: int, db=Depends(get_db)):
    """Obtiene reporte completo"""
    report = get_report_by_scan_id(db, scan_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "scan_id": scan_id,
        "summary": report.summary,
        "recommendations": report.recommendations,
        "confidence_notes": report.confidence_notes,
    }
