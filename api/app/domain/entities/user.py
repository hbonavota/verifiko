from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.enums.user_plan import UserPlan
from app.domain.value_objects.user_id import UserId


@dataclass(slots=True)
class User:
    id: UserId
    email: str
    google_subject: str | None
    password_hash: str | None
    display_name: str
    avatar_url: str | None
    plan: UserPlan
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def create_google_user(
        *,
        email: str,
        google_subject: str,
        display_name: str,
        avatar_url: str | None,
        plan: UserPlan = UserPlan.FREE,
        user_id: UserId | None = None,
    ) -> "User":
        now = datetime.now(timezone.utc)
        return User(
            id=user_id or UserId.new(),
            email=email,
            google_subject=google_subject,
            password_hash=None,
            display_name=display_name,
            avatar_url=avatar_url,
            plan=plan,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def create_email_user(
        *,
        email: str,
        display_name: str,
        plan: UserPlan = UserPlan.FREE,
        user_id: UserId | None = None,
    ) -> "User":
        """A passwordless account, e.g. created on first magic-link sign-in."""
        now = datetime.now(timezone.utc)
        return User(
            id=user_id or UserId.new(),
            email=email,
            google_subject=None,
            password_hash=None,
            display_name=display_name,
            avatar_url=None,
            plan=plan,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def create_local_user(
        *,
        email: str,
        password_hash: str,
        display_name: str,
        plan: UserPlan = UserPlan.FREE,
        user_id: UserId | None = None,
    ) -> "User":
        now = datetime.now(timezone.utc)
        return User(
            id=user_id or UserId.new(),
            email=email,
            google_subject=None,
            password_hash=password_hash,
            display_name=display_name,
            avatar_url=None,
            plan=plan,
            created_at=now,
            updated_at=now,
        )

    def sync_google_profile(
        self,
        *,
        email: str,
        google_subject: str,
        display_name: str,
        avatar_url: str | None,
    ) -> None:
        self.email = email
        self.google_subject = google_subject
        self.display_name = display_name
        self.avatar_url = avatar_url
        self.updated_at = datetime.now(timezone.utc)

    def set_password_hash(self, password_hash: str) -> None:
        self.password_hash = password_hash
        self.updated_at = datetime.now(timezone.utc)

    def assign_plan(self, plan: UserPlan) -> None:
        self.plan = plan
        self.updated_at = datetime.now(timezone.utc)
