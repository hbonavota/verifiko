from dataclasses import dataclass

from app.domain.entities.user import User
from app.domain.enums.user_plan import UserPlan


@dataclass(slots=True)
class UserQuotaPolicy:
    free_daily_limit: int
    pro_daily_limit: int

    def daily_limit_for(self, user: User) -> int:
        return self.daily_limit_for_plan(user.plan)

    def daily_limit_for_plan(self, plan: UserPlan) -> int:
        if plan is UserPlan.PRO:
            return self.pro_daily_limit
        return self.free_daily_limit
