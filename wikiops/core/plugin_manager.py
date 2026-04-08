from typing import Dict, List
from importlib.metadata import entry_points

from wikiops.core.exceptions import ConfigurationError
from wikiops_sdk.contracts import DocumentationPlugin


class PluginManager:
    """Loads plugin factories and creates plugin instances."""

    ENTRYPOINT_GROUP = "wikiops.plugins"

    def __init__(self) -> None:
        self._plugins: Dict[str, DocumentationPlugin] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        for entry_point in entry_points(group=self.ENTRYPOINT_GROUP):
            try:
                plugin_cls = entry_point.load()
                plugin: DocumentationPlugin = plugin_cls()
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load plugin from entry point '{entry_point.name}': {e}"
                )

            plugin_id = plugin.manifest.plugin_id
            self._plugins[plugin_id] = plugin

        self._loaded = True

    def get(self, plugin_id: str) -> DocumentationPlugin:
        self.load()
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            raise ConfigurationError(f"No plugin found with ID '{plugin_id}'")
        return plugin

    def list(self) -> List[DocumentationPlugin]:
        """Returns a list of available plugin IDs."""
        self.load()
        unique: dict[str, DocumentationPlugin] = {}
        for plugin in self._plugins.values():
            unique[plugin.manifest.plugin_id] = plugin
        return sorted(unique.values(), key=lambda item: item.manifest.plugin_id)
