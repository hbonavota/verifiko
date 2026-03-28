from dataclasses import dataclass
from urllib.parse import urljoin

from app.application.ports.redirect_resolver import (
    RedirectHop,
    RedirectResolution,
    RedirectResolutionError,
    RedirectResolverPort,
)
from app.infrastructure.external_services.outbound_target_guard import (
    UnsafeOutboundTargetError,
    resolve_safe_outbound_url,
)
from app.infrastructure.external_services.pinned_http_client import send_pinned_get_request


@dataclass(slots=True)
class HttpRedirectResolver(RedirectResolverPort):
    timeout_seconds: float = 3.0
    max_hops: int = 5
    user_agent: str = "Verifiko/1.0"
    provider_name: str = "http-redirect-resolver"

    def resolve(self, url: str) -> RedirectResolution:
        current_url = url
        hops: list[RedirectHop] = []

        try:
            for _ in range(self.max_hops):
                response = send_pinned_get_request(
                    current_url,
                    headers={"User-Agent": self.user_agent},
                    timeout_seconds=self.timeout_seconds,
                    read_body=False,
                )
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location:
                        raise RedirectResolutionError(
                            "Redirect response omitted a Location header."
                        )

                    next_url = urljoin(current_url, location)
                    try:
                        resolve_safe_outbound_url(next_url)
                    except UnsafeOutboundTargetError as guard_exc:
                        raise RedirectResolutionError(str(guard_exc)) from guard_exc

                    hops.append(
                        RedirectHop(
                            status_code=response.status_code,
                            source_url=current_url,
                            target_url=next_url,
                        )
                    )
                    current_url = next_url
                    continue
                if response.status_code >= 400:
                    raise RedirectResolutionError(f"HTTP Error {response.status_code}")

                return RedirectResolution(
                    final_url=current_url,
                    hops=tuple(hops),
                    provider_name=self.provider_name,
                )
        except UnsafeOutboundTargetError as exc:
            raise RedirectResolutionError(str(exc)) from exc
        except (TimeoutError, OSError) as exc:
            raise RedirectResolutionError(str(exc)) from exc

        raise RedirectResolutionError("Redirect chain exceeded the configured hop limit.")
