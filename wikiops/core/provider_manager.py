from typing import Dict, List
from importlib.metadata import entry_points

from wikiops.core.exceptions import ConfigurationError
from wikiops_sdk.contracts import DocumentProvider


class ProviderManager:
    """Loads provider factories and creates provider instances."""

    ENTRYPOINT_GROUP = "wikiops.providers"

    def __init__(self) -> None:
        self._factories: Dict[str, object] = {}
        self._loaded = False

    def load(self) -> None:
        """Loads provider factories from entry points."""
        if self._loaded:
            return

        for entry_point in entry_points(group=self.ENTRYPOINT_GROUP):
            try:
                factory_cls = entry_point.load()
                factory = factory_cls()
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load provider factory from entry point '{entry_point.name}': {e}"
                )

            provider_id = getattr(factory, "provider_id", entry_point.name)
            self._factories[provider_id] = factory

        self._loaded = True

    def create(self, provider_type: str, settings: Dict) -> DocumentProvider:
        self.load()
        factory = self._factories.get(provider_type)
        if not factory:
            raise ConfigurationError(
                f"No provider factory found for type '{provider_type}'"
            )
        try:
            return factory.create(settings)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create provider of type '{provider_type}': {e}"
            )

    def list_types(self) -> List[str]:
        """Returns a list of available provider types."""
        self.load()
        return sorted(self._factories.keys())
