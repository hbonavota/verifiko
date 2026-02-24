import json
import os
import re
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from urllib.parse import urlparse, urlunparse

import idna
import tldextract
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

app = FastAPI(title="Verifiko API", version="0.2.0")


# ---------------------------
# Modelos API
# ---------------------------
class UrlScanIn(BaseModel):
    url: str = Field(min_length=5, max_length=2048)


class ScanOut(BaseModel):
    id: str
    status: str
    score: Optional[int] = None
    verdict: Optional[str] = None
    created_at: datetime


# ---------------------------
# Utilidades
# ---------------------------
def normalize_url(raw: str) -> str:
    s = raw.strip()
    if not s:
        raise ValueError("URL vacía")

    # Si no hay esquema, asumimos https
    if "://" not in s:
        s = "https://" + s

    p = urlparse(s)
    if p.scheme not in ("http", "https"):
        raise ValueError("Esquema no soportado")

    # Host obligatorio
    if not p.netloc:
        raise ValueError("URL inválida (sin host)")

    # Normaliza host: lower + punycode
    host = p.hostname or ""
    host = host.strip().lower()
    try:
        host_ascii = idna.encode(host).decode("ascii")
    except Exception:
        raise ValueError("Host inválido")

    # reconstruir netloc (preservando puerto si existe)
    netloc = host_ascii
    if p.port:
        netloc = f"{host_ascii}:{p.port}"

    # Quita fragment (#...), normaliza path
    path = p.path or "/"

    return urlunparse((p.scheme, netloc, path, "", p.query or "", ""))


def verdict_from_score(score: int) -> str:
    if score >= 60:
        return "red"
    if score >= 20:
        return "yellow"
    return "green"

SUSPICIOUS_TLDS = {
    "zip", "mov", "top", "xyz", "icu", "click", "work", "support", "lol", "cam"
}

BRAND_HINTS = {
    "paypal", "google", "apple", "microsoft", "amazon", "meta", "facebook", "instagram",
    "whatsapp", "dhl", "correos", "bbva", "santander", "caixabank"
}

SHORTENER_HOSTS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rebrand.ly"
}

IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def compute_url_risk(normalized_url: str) -> Tuple[int, List[Tuple[str, str]]]:
    """
    Devuelve (score 0..100, signals[(name,value)])
    Score = riesgo de estafa/phishing (no 'veracidad').
    """
    signals: List[Tuple[str, str]] = []
    score = 0

    p = urlparse(normalized_url)
    host = (p.hostname or "").lower()

    # Señal: URL con IP directa
    if IPV4_RE.match(host):
        score += 35
        signals.append(("host_is_ip", "true"))

    # Señal: acortador
    if host in SHORTENER_HOSTS:
        score += 25
        signals.append(("url_shortener", host))

    # Señal: TLD sospechoso
    ext = tldextract.extract(host)  # subdomain, domain, suffix
    suffix = (ext.suffix or "").lower()
    if suffix in SUSPICIOUS_TLDS:
        score += 15
        signals.append(("suspicious_tld", suffix))

    # Señal: demasiados guiones
    hyphens = host.count("-")
    if hyphens >= 3:
        score += 10
        signals.append(("many_hyphens", str(hyphens)))

    # Señal: host muy largo
    if len(host) >= 35:
        score += 8
        signals.append(("long_hostname", str(len(host))))

    # Señal: username@host en URL (phishing clásico). Ojo: urlparse lo mete en netloc.
    if "@" in p.netloc:
        score += 30
        signals.append(("contains_at_in_netloc", "true"))

    # Señal: marcas en subdominio (ej: paypal.seguro-login.evil.com)
    sub = (ext.subdomain or "").lower()
    for b in BRAND_HINTS:
        if b in sub and not host.endswith(f"{b}.{suffix}") and not host.endswith(b):
            score += 12
            signals.append(("brand_in_subdomain", b))
            break

    # Señal: marca embebida en el dominio (ej: paypal-login-secure-update.xyz)
    domain = (ext.domain or "").lower()
    for b in BRAND_HINTS:
        if b in domain and domain != b:
            score += 18
            signals.append(("brand_in_domain", b))
            break

    # Señal: path con palabras típicas de phishing
    path = (p.path or "").lower()
    phishing_words = ["login", "verify", "account", "secure", "update", "invoice", "payment", "confirm"]
    hits = [w for w in phishing_words if w in path]
    if hits:
        score += min(12, 3 * len(hits))
        signals.append(("phishy_path_words", ",".join(hits[:6])))

    # Cap 0..100
    score = max(0, min(100, score))
    return score, signals

def build_report(verdict: str, score: int, signals: list[tuple[str, str]], normalized_url: str) -> tuple[str, list[str], list[str]]:
    """
    Genera un reporte explicable (sin LLM).
    - summary: 1-2 frases
    - recommendations: lista accionable
    - confidence_notes: caveats / limitaciones
    """
    signal_names = {n for (n, _) in signals}

    # Summary
    if verdict == "red":
        summary = f"Riesgo alto ({score}/100): esta URL muestra varios patrones típicos de phishing/estafa."
    elif verdict == "yellow":
        summary = f"Riesgo medio ({score}/100): hay señales sospechosas, conviene extremar precauciones."
    else:
        summary = f"Riesgo bajo ({score}/100): no vemos señales fuertes de phishing, pero ninguna verificación es infalible."

    # Recommendations
    recs: list[str] = []

    # Reglas orientadas a usuario final
    if "url_shortener" in signal_names:
        recs.append("No abras enlaces acortados sin expandirlos primero (pueden ocultar el destino real).")
    if "host_is_ip" in signal_names:
        recs.append("Evita URLs con IP directa: es un patrón frecuente en páginas de phishing.")
    if "brand_in_subdomain" in signal_names or "brand_in_domain" in signal_names:
        recs.append("Si parece una marca, entra por la web oficial escribiendo el dominio a mano (no desde enlaces).")
    if "phishy_path_words" in signal_names:
        recs.append("No introduzcas contraseñas/códigos si el enlace llegó por SMS/WhatsApp/correo inesperado.")
    if verdict in ("yellow", "red"):
        recs.append("Verifica por un canal alternativo: app oficial o teléfono del banco/servicio.")
        recs.append("Si ya has hecho clic, no descargues archivos y revisa que el navegador no haya guardado credenciales.")
    else:
        recs.append("Comprueba que el dominio y el candado HTTPS coinciden con el sitio oficial antes de iniciar sesión.")

    # Confidence notes (honestidad radical)
    notes: list[str] = [
        "Este resultado es un análisis heurístico: reduce riesgo, pero no garantiza que una URL sea segura o maliciosa.",
        "Los atacantes cambian tácticas con frecuencia; algunas estafas pueden no activar señales.",
    ]
    if verdict == "green":
        notes.append("Para máxima seguridad, confirma siempre la URL por la fuente oficial (marcador/app).")

    return summary, recs, notes

def save_signals(conn, scan_id: str, signals: List[Tuple[str, str]]) -> None:
    if not signals:
        return
    conn.execute(
        text(
            """
            insert into public.scan_signals (scan_id, name, value)
            values (:scan_id, :name, :value)
            """
        ),
        [{"scan_id": scan_id, "name": n, "value": v} for (n, v) in signals],
    )


# ---------------------------
# Endpoints
# ---------------------------
@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    return {"ok": True}


@app.post("/scan/url", response_model=ScanOut)
def create_url_scan(payload: UrlScanIn):
    scan_id = str(uuid.uuid4())
    now = datetime.utcnow()

    try:
        normalized = normalize_url(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Análisis rápido síncrono (MVP)
    score, signals = compute_url_risk(normalized)
    verdict = verdict_from_score(score)
    summary, recs, notes = build_report(verdict, score, signals, normalized)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                insert into public.scans (id, scan_type, input, normalized_input, status, score, verdict, created_at)
                values (:id, 'url', :input, :norm, 'done', :score, :verdict, :created_at)
                """
            ),
            {
                "id": scan_id,
                "input": payload.url,
                "norm": normalized,
                "score": score,
                "verdict": verdict,
                "created_at": now,
            },
        )
        save_signals(conn, scan_id, signals)
        conn.execute(
            text(
                """
                insert into public.scan_reports (scan_id, summary, recommendations, confidence_notes)
                values (:scan_id, :summary, :recs, :notes)
                """
            ),
            {
                "scan_id": scan_id,
                "summary": summary,
                "recs": json.dumps(recs),
                "notes": json.dumps(notes),
            },
        )

        # Señales "futuras" (IA) — dejamos placeholder para el pipeline
        # Ejemplo: conn.execute(... name='ai_content_risk', value='not_implemented')

    return ScanOut(
        id=scan_id,
        status="done",
        score=score,
        verdict=verdict,
        created_at=now,
    )


@app.get("/scan/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                select id, status, score, verdict, created_at
                from public.scans
                where id = :id
                """
            ),
            {"id": scan_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Scan no encontrado")

    return ScanOut(
        id=row["id"],
        status=row["status"],
        score=row["score"],
        verdict=row["verdict"],
        created_at=row["created_at"],
    )

@app.get("/scan/{scan_id}/signals")
def get_scan_signals(scan_id: str):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                select name, value, created_at
                from public.scan_signals
                where scan_id = :id
                order by id asc
                """
            ),
            {"id": scan_id},
        ).mappings().all()

    return {"scan_id": scan_id, "signals": rows}

@app.get("/scan/{scan_id}/report")
def get_scan_report(scan_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                select scan_id, summary, recommendations, confidence_notes, created_at
                from public.scan_reports
                where scan_id = :id
                """
            ),
            {"id": scan_id},
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    return {
        "scan_id": row["scan_id"],
        "summary": row["summary"],
        "recommendations": row["recommendations"],
        "confidence_notes": row["confidence_notes"],
        "created_at": row["created_at"],
    }
