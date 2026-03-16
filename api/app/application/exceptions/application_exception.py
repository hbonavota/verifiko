class ApplicationException(Exception):
    """Base application exception."""


class VerificationNotFoundError(ApplicationException):
    """Raised when a verification cannot be found."""
