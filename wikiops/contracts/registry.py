from typing import Protocol, runtime_checkable

from wikiops_sdk.contracts import DocumentationPlugin, DocumentProvider


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
