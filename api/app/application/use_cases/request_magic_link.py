from dataclasses import dataclass, field
from typing import Callable

from app.application.ports.email_sender import EmailMessage, EmailSenderPort
from app.application.ports.magic_link_store import MagicLinkStorePort
from app.application.services.email_normalizer import normalize_email
from app.application.services.magic_link_token import (
    generate_magic_link_token,
    hash_magic_link_token,
)


@dataclass(slots=True)
class RequestMagicLinkUseCase:
    """Issues a single-use magic link and emails it.

    Always succeeds silently regardless of whether the email already has an
    account: the link both signs in existing users and creates passwordless
    accounts on first use, so there is no user-enumeration signal.
    """

    magic_link_store: MagicLinkStorePort
    email_sender: EmailSenderPort
    link_base_url: str
    ttl_seconds: int
    token_factory: Callable[[], str] = field(default=generate_magic_link_token)

    def execute(self, email: str) -> None:
        normalized_email = normalize_email(email)
        token = self.token_factory()
        self.magic_link_store.save(
            hash_magic_link_token(token), normalized_email, self.ttl_seconds
        )
        link = f"{self.link_base_url}/auth/magic?token={token}"
        self.email_sender.send(self._build_message(normalized_email, link))

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
