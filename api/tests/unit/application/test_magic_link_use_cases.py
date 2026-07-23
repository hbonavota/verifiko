import pytest

from app.application.ports.email_sender import EmailMessage, EmailSenderPort
from app.application.use_cases.authenticate_with_magic_link import (
    AuthenticateWithMagicLinkUseCase,
    InvalidMagicLinkError,
)
from app.application.use_cases.request_magic_link import RequestMagicLinkUseCase
from app.domain.entities.user import User
from app.domain.enums.user_plan import UserPlan
from app.domain.ports.user_repository import UserRepository
from app.domain.value_objects.user_id import UserId
from app.infrastructure.auth.magic_link_stores import InMemoryMagicLinkStore


class RecordingSender(EmailSenderPort):
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self._by_email: dict[str, User] = {}

    def save(self, user: User) -> User:
        self._by_email[user.email] = user
        return user

    def get_by_id(self, user_id: UserId) -> User | None:
        return next((u for u in self._by_email.values() if u.id == user_id), None)

    def get_by_google_subject(self, google_subject: str) -> User | None:
        return None

    def get_by_email(self, email: str) -> User | None:
        return self._by_email.get(email)


class FakeTokenService:
    def issue_access_token(self, user_id) -> str:
        return f"session-{user_id}"

    def resolve_user_id(self, token):
        raise NotImplementedError


def _token_from(sender: RecordingSender) -> str:
    link = sender.sent[-1].text.split("token=")[1].split()[0]
    return link


def _request_use_case(store, sender, token="fixed-token-123"):
    return RequestMagicLinkUseCase(
        magic_link_store=store,
        email_sender=sender,
        link_base_url="https://www.verifiko.es",
        ttl_seconds=900,
        token_factory=lambda: token,
    )


def test_request_stores_token_and_emails_link() -> None:
    store = InMemoryMagicLinkStore()
    sender = RecordingSender()

    _request_use_case(store, sender).execute("  User@Example.COM ")

    assert len(sender.sent) == 1
    message = sender.sent[0]
    assert message.to == "user@example.com"  # normalized
    assert "https://www.verifiko.es/auth/magic?token=fixed-token-123" in message.text


def test_consume_creates_passwordless_user_and_issues_session() -> None:
    store = InMemoryMagicLinkStore()
    sender = RecordingSender()
    repo = FakeUserRepository()
    _request_use_case(store, sender).execute("new@example.com")

    session = AuthenticateWithMagicLinkUseCase(store, repo, FakeTokenService()).execute(
        "fixed-token-123"
    )

    assert session.user.email == "new@example.com"
    assert session.token_type == "Bearer"
    assert session.access_token.startswith("session-")
    created = repo.get_by_email("new@example.com")
    assert created is not None
    assert created.password_hash is None  # passwordless
    assert created.plan is UserPlan.FREE


def test_consume_reuses_existing_user() -> None:
    store = InMemoryMagicLinkStore()
    sender = RecordingSender()
    repo = FakeUserRepository()
    existing = User.create_local_user(
        email="known@example.com", password_hash="hash", display_name="Known"
    )
    repo.save(existing)
    _request_use_case(store, sender).execute("known@example.com")

    session = AuthenticateWithMagicLinkUseCase(store, repo, FakeTokenService()).execute(
        "fixed-token-123"
    )

    assert session.user.id == str(existing.id)


def test_token_is_single_use() -> None:
    store = InMemoryMagicLinkStore()
    sender = RecordingSender()
    repo = FakeUserRepository()
    _request_use_case(store, sender).execute("new@example.com")
    consume = AuthenticateWithMagicLinkUseCase(store, repo, FakeTokenService())

    consume.execute("fixed-token-123")  # first use ok
    with pytest.raises(InvalidMagicLinkError):
        consume.execute("fixed-token-123")  # second use rejected


def test_unknown_token_is_rejected() -> None:
    consume = AuthenticateWithMagicLinkUseCase(
        InMemoryMagicLinkStore(), FakeUserRepository(), FakeTokenService()
    )
    with pytest.raises(InvalidMagicLinkError):
        consume.execute("never-issued")
