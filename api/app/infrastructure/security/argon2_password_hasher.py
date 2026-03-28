from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.application.ports.password_hasher import PasswordHasherPort


class Argon2PasswordHasher(PasswordHasherPort):
    def __init__(self) -> None:
        self._password_hasher = PasswordHasher()

    def hash_password(self, password: str) -> str:
        return self._password_hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return bool(self._password_hasher.verify(password_hash, password))
        except (InvalidHashError, VerificationError):
            return False
