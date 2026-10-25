"""Machine-to-machine worker endpoint invoked by Upstash QStash.

When ``scan_dispatch_mode`` is ``"qstash"``, the submit path publishes the job to
QStash instead of running it on a background thread. QStash then calls this
endpoint as its own HTTP request, so the 10-30s detonation runs in a fresh
serverless invocation with its own time budget — never on a frozen instance.

Trust is established by the ``Upstash-Signature`` header (a JWT over the request
body), not by user auth: this route deliberately does not depend on
``get_current_user``. An unsigned or tampered request is rejected with 401.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from starlette.concurrency import run_in_threadpool

from app.application.services.verification_scan_processor import (
    VerificationScanProcessor,
)
from app.entrypoints.api.dependencies.container import (
    get_qstash_signature_verifier,
    get_verification_scan_processor,
)
from app.infrastructure.security.qstash_signature_verifier import (
    QStashSignatureError,
    QStashSignatureVerifier,
)

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("/process", include_in_schema=False)
async def process_scan(
    request: Request,
    upstash_signature: str | None = Header(default=None, alias="Upstash-Signature"),
    verifier: QStashSignatureVerifier = Depends(get_qstash_signature_verifier),
    processor: VerificationScanProcessor = Depends(get_verification_scan_processor),
) -> dict[str, str]:
    # Verify against the *exact* bytes QStash signed; re-parsing then
    # re-serializing would change them and break the body-hash check.
    raw_body = await request.body()
    try:
        verifier.verify(signature=upstash_signature or "", body=raw_body)
    except QStashSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid QStash signature.",
        ) from exc

    try:
        job_id = json.loads(raw_body)["job_id"]
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid worker payload.",
        ) from exc
    if not isinstance(job_id, str) or not job_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid worker payload.",
        )

    # The processor is blocking (it runs the whole pipeline, including the
    # detonation) and handles its own failures, marking the job FAILED rather
    # than raising. Run it off the event loop so we don't stall other requests.
    await run_in_threadpool(processor.process, job_id)
    return {"status": "processed", "job_id": job_id}
