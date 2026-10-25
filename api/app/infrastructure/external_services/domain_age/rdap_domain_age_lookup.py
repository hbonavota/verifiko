import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from app.application.ports.domain_age_lookup import (
    DomainAgeLookupPort,
    DomainRegistrationInfo,
    DomainRegistrationLookupError,
)


@dataclass(slots=True)
class RdapDomainAgeLookup(DomainAgeLookupPort):
    timeout_seconds: float = 2.0
    provider_name: str = "rdap.org"
    base_url: str = "https://rdap.org/domain/"

    def lookup(self, domain: str) -> DomainRegistrationInfo | None:
        try:
            with urlopen(
                f"{self.base_url}{domain}", timeout=self.timeout_seconds
            ) as response:
                payload = json.load(response)
        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise DomainRegistrationLookupError(str(exc)) from exc

        registered_at = _extract_registration_date(payload)
        if registered_at is None:
            return None

        return DomainRegistrationInfo(
            registered_at=registered_at,
            provider_name=self.provider_name,
        )


def _extract_registration_date(payload: dict) -> datetime | None:
    events = payload.get("events", [])
    candidates: list[datetime] = []

    for event in events:
        action = str(event.get("eventAction", "")).lower()
        if action not in {"registration", "registered"}:
            continue

        event_date = event.get("eventDate")
        parsed = _parse_rdap_datetime(event_date)
        if parsed is not None:
            candidates.append(parsed)

    if not candidates:
        return None

    return min(candidates)


def _parse_rdap_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    candidate = value.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)
