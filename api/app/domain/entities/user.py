from dataclasses import dataclass
from datetime import datetime, timezone

from app.domain.enums.user_plan import UserPlan
from app.domain.value_objects.user_id import UserId


@dataclass(slots=True)
class User:
    id: UserId
    email: str
    google_subject: str
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
            display_name=display_name,
            avatar_url=avatar_url,
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

    def assign_plan(self, plan: UserPlan) -> None:
        self.plan = plan
        self.updated_at = datetime.now(timezone.utc)
