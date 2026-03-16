from abc import ABC, abstractmethod
from datetime import datetime


class TimeProvider(ABC):
    @abstractmethod
    def now(self) -> datetime:
        raise NotImplementedError
