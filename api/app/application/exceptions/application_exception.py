class ApplicationException(Exception):
    """Base application exception."""


class VerificationNotFoundError(ApplicationException):
    """Raised when a verification cannot be found."""


class ApiKeyNotFoundError(ApplicationException):
    """Raised when an API key cannot be found for the requesting owner."""


class VerificationScanNotFoundError(ApplicationException):
    """Raised when an async verification scan cannot be found for the owner."""
