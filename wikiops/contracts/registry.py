from typing import Protocol, runtime_checkable

from wikiops.contracts.provider import DocumentProvider
from wikiops.contracts.plugin import DocumentationPlugin


@runtime_checkable
class ProviderRegistry(Protocol):
    """Factory for provider instances."""

    provider_id: str

    def create(self, settings: dict) -> DocumentProvider: ...


@runtime_checkable
class PluginFactory(Protocol):
    """Factory for plugin instances."""

    plugin_id: str

    def create(self) -> DocumentationPlugin: ...
