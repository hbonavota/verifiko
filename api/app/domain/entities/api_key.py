from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.value_objects.api_key_id import ApiKeyId
from app.domain.value_objects.user_id import UserId


@dataclass(slots=True)
class ApiKey:
    """A machine-to-machine credential owned by a user.

    The raw secret is never stored. Only a deterministic ``token_hash`` (for
    lookup) and a human-readable ``token_prefix`` (for identification in the UI)
    are persisted.
    """

    id: ApiKeyId
    user_id: UserId
    name: str
    token_prefix: str
    token_hash: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None

    @staticmethod
    def issue(
        *,
        user_id: UserId,
        name: str,
        token_prefix: str,
        token_hash: str,
        api_key_id: ApiKeyId | None = None,
        now: datetime | None = None,
    ) -> "ApiKey":
        issued_at = now or datetime.now(timezone.utc)
        return ApiKey(
            id=api_key_id or ApiKeyId.new(),
            user_id=user_id,
            name=name.strip(),
            token_prefix=token_prefix,
            token_hash=token_hash,
            created_at=issued_at,
            last_used_at=None,
            revoked_at=None,
        )

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self, now: datetime | None = None) -> None:
        if self.revoked_at is None:
            self.revoked_at = now or datetime.now(timezone.utc)

    def record_usage(self, now: datetime | None = None) -> None:
        self.last_used_at = now or datetime.now(timezone.utc)
