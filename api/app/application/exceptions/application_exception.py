class ApplicationException(Exception):
    """Base application exception."""


class VerificationNotFoundError(ApplicationException):
    """Raised when a verification cannot be found."""


class ApiKeyNotFoundError(ApplicationException):
    """Raised when an API key cannot be found for the requesting owner."""
