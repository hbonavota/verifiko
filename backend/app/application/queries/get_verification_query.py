from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetVerificationQuery:
    verification_id: str
