from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetOwnedVerificationQuery:
    verification_id: str
    owner_user_id: str
