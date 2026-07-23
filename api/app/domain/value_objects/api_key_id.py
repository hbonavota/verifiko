from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class ApiKeyId:
    value: UUID

    @staticmethod
    def new() -> "ApiKeyId":
        return ApiKeyId(value=uuid4())

    @staticmethod
    def from_string(raw: str) -> "ApiKeyId":
        return ApiKeyId(value=UUID(raw))

    def __str__(self) -> str:
        return str(self.value)
