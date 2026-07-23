from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeneratedApiKey:
    """The output of minting a new API key.

    ``plaintext`` is the secret shown to the caller exactly once. Only
    ``token_hash`` and ``token_prefix`` are ever persisted.
    """

    plaintext: str
    token_prefix: str
    token_hash: str


class ApiKeyTokenServicePort(ABC):
    @abstractmethod
    def generate(self) -> GeneratedApiKey:
        raise NotImplementedError

    @abstractmethod
    def hash(self, plaintext: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def looks_like_api_key(self, candidate: str) -> bool:
        raise NotImplementedError
