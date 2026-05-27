"""Custom domain exceptions for business logic violations.

These exceptions are raised by the service layer to indicate domain-specific
errors that should be caught and translated to HTTP responses by controllers.
"""


class ArchivedEntityError(Exception):
    """Raised when attempting to modify an archived entity.

    Archived entities (with archived_at set) are read-only and cannot be edited.
    """

    pass
