import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.application.ports.reputation_lookup import (
    ReputationLookupError,
    ReputationLookupPort,
    ReputationMatch,
)


@dataclass(slots=True)
class UrlhausReputationClient(ReputationLookupPort):
    timeout_seconds: float = 2.0
    provider_name: str = "urlhaus.abuse.ch"
    endpoint: str = "https://urlhaus-api.abuse.ch/v1/host/"

    def lookup(self, hostname: str) -> ReputationMatch | None:
        body = urlencode({"host": hostname}).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Verifiko/1.0",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise ReputationLookupError(str(exc)) from exc

        if payload.get("query_status") != "ok":
            return None

        urls = payload.get("urls") or []
        if not urls:
            return None

        online_urls = [
            item for item in urls if str(item.get("url_status", "")).lower() == "online"
        ]
        reference_count = len(urls)
        confidence = 99.0 if online_urls else 96.0
        description = f"URLhaus returned {reference_count} malicious URL record(s) for the queried host."

        return ReputationMatch(
            queried_value=hostname,
            provider_name=self.provider_name,
            confidence=confidence,
            reference_count=reference_count,
            match_scope="host",
            description=description,
        )
