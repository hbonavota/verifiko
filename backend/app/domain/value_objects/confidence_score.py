from dataclasses import dataclass

from app.domain.exceptions.domain_exception import DomainException


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    value: float

    def __post_init__(self) -> None:
        if self.value < 0 or self.value > 100:
            raise DomainException("Confidence score must be between 0 and 100.")

    @property
    def as_ratio(self) -> float:
        return self.value / 100

    def rounded(self, digits: int = 2) -> float:
        return round(self.value, digits)
