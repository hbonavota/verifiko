from __future__ import annotations

from sqlalchemy.orm import Session

from api.core.db import Report, Scan, Signal


def insert_scan(
    db: Session, input_url: str, normalized_url: str, score: int, verdict: str
) -> Scan:
    """Inserta escaneo en BD."""
    scan = Scan(
        input_url=input_url,
        normalized_url=normalized_url,
        score=score,
        verdict=verdict,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def insert_signals(db: Session, scan_id: int, signals: list[tuple[str, str]]) -> None:
    """Inserta señales detectadas."""
    if not signals:
        return
    for name, value in signals:
        signal = Signal(scan_id=scan_id, name=name, value=value)
        db.add(signal)
    db.commit()


def insert_report(
    db: Session,
    scan_id: int,
    summary: str,
    recommendations: str,
    confidence_notes: str,
) -> Report:
    """
    Inserta reporte.

    Acepta todos los parámetros como strings (compatibilidad total).
    """
    report = Report(
        scan_id=scan_id,
        summary=summary,
        recommendations=recommendations,
        confidence_notes=confidence_notes,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_scan_by_id(db: Session, scan_id: int) -> Scan | None:
    """Obtiene escaneo por ID."""
    return db.query(Scan).filter(Scan.id == scan_id).first()


def get_signals_by_scan_id(db: Session, scan_id: int) -> list[Signal]:
    """Obtiene señales de un escaneo."""
    return db.query(Signal).filter(Signal.scan_id == scan_id).all()


def get_report_by_scan_id(db: Session, scan_id: int) -> Report | None:
    """Obtiene reporte de un escaneo."""
    return db.query(Report).filter(Report.scan_id == scan_id).first()
