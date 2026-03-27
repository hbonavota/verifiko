from app.application.services.verification_text_localizer import SupportedLocale


def select_response_locale(accept_language: str | None) -> SupportedLocale:
    if not accept_language:
        return "en"

    for entry in accept_language.split(","):
        language = entry.split(";", 1)[0].strip().lower()
        if language.startswith("es"):
            return "es"
        if language.startswith("en"):
            return "en"

    return "en"
