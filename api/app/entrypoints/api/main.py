from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.application.exceptions.application_exception import VerificationNotFoundError
from app.application.services.message_resolver import localize_known_error_message
from app.domain.exceptions.domain_exception import DomainException
from app.entrypoints.api.locale import select_response_locale
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

app.include_router(verifications_router, prefix="/api")


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
