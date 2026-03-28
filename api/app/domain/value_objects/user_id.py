from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class UserId:
    value: UUID

    @staticmethod
    def new() -> "UserId":
        return UserId(value=uuid4())

    @staticmethod
    def from_string(raw: str) -> "UserId":
        return UserId(value=UUID(raw))

    def __str__(self) -> str:
        return str(self.value)
