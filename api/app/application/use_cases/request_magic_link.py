import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from typing import Callable

from app.application.ports.email_sender import EmailMessage, EmailSenderPort
from app.application.ports.magic_link_store import MagicLinkStorePort
from app.application.services.email_normalizer import normalize_email
from app.application.services.magic_link_token import (
    generate_magic_link_token,
    hash_magic_link_token,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RequestMagicLinkUseCase:
    """Issues a single-use magic link and emails it.

    Always succeeds silently regardless of whether the email already has an
    account: the link both signs in existing users and creates passwordless
    accounts on first use, so there is no user-enumeration signal.

    Email delivery is best-effort and time-bounded: the token is stored first,
    then the email is sent with a hard timeout. A slow, hanging, or failing
    provider is logged and never turned into a 5xx or a request that outlives
    the serverless function budget.
    """

    magic_link_store: MagicLinkStorePort
    email_sender: EmailSenderPort
    link_base_url: str
    ttl_seconds: int
    token_factory: Callable[[], str] = field(default=generate_magic_link_token)
    send_timeout_seconds: float = 8.0

    def execute(self, email: str) -> None:
        normalized_email = normalize_email(email)
        token = self.token_factory()
        self.magic_link_store.save(
            hash_magic_link_token(token), normalized_email, self.ttl_seconds
        )
        link = f"{self.link_base_url}/auth/magic?token={token}"
        self._deliver(normalized_email, link)

    def _deliver(self, email: str, link: str) -> None:
        message = self._build_message(email, link)
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.email_sender.send, message)
        try:
            future.result(timeout=self.send_timeout_seconds)
        except FuturesTimeoutError:
            logger.warning("Magic-link email delivery timed out for %s", email)
        except Exception:
            logger.warning("Magic-link email delivery failed for %s", email, exc_info=True)
        finally:
            # Never block the request on a hanging send; abandon the worker.
            executor.shutdown(wait=False, cancel_futures=True)

    def _build_message(self, email: str, link: str) -> EmailMessage:
        minutes = max(1, self.ttl_seconds // 60)
        subject = "Your Verifiko sign-in link"
        text = (
            "Sign in to Verifiko using the link below. "
            f"It expires in {minutes} minutes and can be used once.\n\n{link}\n\n"
            "If you didn't request this, you can ignore this email."
        )
        html = (
            "<p>Sign in to Verifiko using the button below. "
            f"It expires in {minutes} minutes and can be used once.</p>"
            f'<p><a href="{link}">Sign in to Verifiko</a></p>'
            f"<p>Or paste this link: {link}</p>"
            "<p>If you didn't request this, you can ignore this email.</p>"
        )
        return EmailMessage(to=email, subject=subject, html=html, text=text)
