from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.application.exceptions.application_exception import VerificationNotFoundError
from app.application.services.message_resolver import localize_known_error_message
from app.domain.exceptions.domain_exception import DomainException
from app.entrypoints.api.locale import select_response_locale
from app.entrypoints.api.routes.api_keys import router as api_keys_router
from app.entrypoints.api.routes.auth import router as auth_router
from app.entrypoints.api.routes.internal_scan_worker import router as internal_scan_worker_router
from app.entrypoints.api.routes.me import router as me_router
from app.entrypoints.api.routes.scans import router as scans_router
from app.entrypoints.api.routes.verifications import router as verifications_router
from app.infrastructure.config.settings import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.app_debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_origin_regex=settings.cors_allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_API_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
_API_CSP_VALUE = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in _API_SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)

    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type.lower():
        response.headers.setdefault("Content-Security-Policy", _API_CSP_VALUE)
    return response


_API_ROUTERS = (
    auth_router,
    me_router,
    api_keys_router,
    scans_router,
    verifications_router,
    # Internal QStash worker callback. Hidden from the OpenAPI schema (the route
    # itself sets include_in_schema=False); authenticated by Upstash-Signature,
    # not user auth.
    internal_scan_worker_router,
)

# Canonical, versioned surface. This is the documented contract and the source
# of truth for generated SDKs and OpenAPI operation IDs.
for _router in _API_ROUTERS:
    app.include_router(_router, prefix="/api/v1")

# Legacy unversioned surface, preserved for backwards compatibility with the
# existing web client. Hidden from the OpenAPI schema so the documented contract
# has a single, unambiguous set of operation IDs under /api/v1.
for _router in _API_ROUTERS:
    app.include_router(_router, prefix="/api", include_in_schema=False)


@app.exception_handler(DomainException)
def handle_domain_exception(request: Request, exc: DomainException) -> JSONResponse:
    locale = select_response_locale(request.headers.get("Accept-Language"))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": localize_known_error_message(str(exc), language=locale)},
    )


@app.exception_handler(VerificationNotFoundError)
def handle_verification_not_found(request: Request, exc: VerificationNotFoundError) -> JSONResponse:
    locale = select_response_locale(request.headers.get("Accept-Language"))
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": localize_known_error_message(str(exc), language=locale)},
    )


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
