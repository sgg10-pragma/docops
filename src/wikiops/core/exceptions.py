class AzdWikiError(Exception):
    """Base error for the project."""


class ConfigurationError(AzdWikiError):
    """Raised when configuration is invalid."""


class ProviderCompatibilityError(AzdWikiError):
    """Raised when a provider cannot satisfy a plugin."""


class ReferenceResolutionError(AzdWikiError):
    """Raised when a required reference cannot be resolved."""
