from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.application.ports.redirect_resolver import (
    RedirectHop,
    RedirectResolution,
    RedirectResolutionError,
    RedirectResolverPort,
)
from app.infrastructure.external_services.outbound_target_guard import (
    UnsafeOutboundTargetError,
    assert_safe_outbound_url,
)


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(slots=True)
class HttpRedirectResolver(RedirectResolverPort):
    timeout_seconds: float = 3.0
    max_hops: int = 5
    user_agent: str = "Verifiko/1.0"
    provider_name: str = "http-redirect-resolver"

    def resolve(self, url: str) -> RedirectResolution:
        opener = build_opener(_NoRedirectHandler())
        current_url = url
        hops: list[RedirectHop] = []

        try:
            assert_safe_outbound_url(current_url)
        except UnsafeOutboundTargetError as exc:
            raise RedirectResolutionError(str(exc)) from exc

        for _ in range(self.max_hops):
            request = Request(current_url, headers={"User-Agent": self.user_agent})
            try:
                with opener.open(request, timeout=self.timeout_seconds) as response:
                    return RedirectResolution(
                        final_url=response.geturl(),
                        hops=tuple(hops),
                        provider_name=self.provider_name,
                    )
            except HTTPError as exc:
                if exc.code not in {301, 302, 303, 307, 308}:
                    raise RedirectResolutionError(str(exc)) from exc

                location = exc.headers.get("Location")
                if not location:
                    raise RedirectResolutionError("Redirect response omitted a Location header.")

                next_url = urljoin(current_url, location)
                try:
                    assert_safe_outbound_url(next_url)
                except UnsafeOutboundTargetError as guard_exc:
                    raise RedirectResolutionError(str(guard_exc)) from guard_exc

                hops.append(
                    RedirectHop(
                        status_code=exc.code,
                        source_url=current_url,
                        target_url=next_url,
                    )
                )
                current_url = next_url
            except (URLError, TimeoutError, OSError) as exc:
                raise RedirectResolutionError(str(exc)) from exc

        raise RedirectResolutionError("Redirect chain exceeded the configured hop limit.")
