from inspect import Parameter, signature
from typing import Any, Dict, List
from importlib.metadata import entry_points

from docops.core.exceptions import ConfigurationError
from docops.core.plugin_resources import PackagePluginResourceProvider
from wikiops_sdk import PLUGIN_ENTRYPOINT_GROUP, ensure_plugin_api_compatible
from wikiops_sdk.compat import CompatibilityError
from wikiops_sdk.contracts import DocumentationPlugin


class PluginManager:
    """Loads plugin instances from host entry points."""

    ENTRYPOINT_GROUP = PLUGIN_ENTRYPOINT_GROUP

    def __init__(self) -> None:
        self._plugins: Dict[str, DocumentationPlugin] = {}
        self._loaded = False

    @staticmethod
    def _instantiate_plugin(
        plugin_cls: type[Any], resources: PackagePluginResourceProvider
    ) -> DocumentationPlugin:
        constructor = signature(plugin_cls)
        parameters = list(constructor.parameters.values())
        has_named_resources = "resources" in constructor.parameters
        has_var_keyword = any(
            parameter.kind is Parameter.VAR_KEYWORD for parameter in parameters
        )
        has_var_positional = any(
            parameter.kind is Parameter.VAR_POSITIONAL for parameter in parameters
        )

        if has_named_resources or has_var_keyword:
            return plugin_cls(resources=resources)
        if has_var_positional:
            return plugin_cls(resources)

        required_parameters = [
            parameter
            for parameter in parameters
            if parameter.default is Parameter.empty
            and parameter.kind
            in (
                Parameter.POSITIONAL_ONLY,
                Parameter.POSITIONAL_OR_KEYWORD,
                Parameter.KEYWORD_ONLY,
            )
        ]

        if not required_parameters:
            return plugin_cls()
        if len(required_parameters) == 1:
            parameter = required_parameters[0]
            if parameter.kind in (
                Parameter.POSITIONAL_ONLY,
                Parameter.POSITIONAL_OR_KEYWORD,
            ):
                return plugin_cls(resources)
            return plugin_cls(resources=resources)

        raise ConfigurationError(
            "Plugin constructors must be zero-argument or accept a single resource provider."
        )

    @staticmethod
    def _attach_resources_if_needed(
        plugin: Any, resources: PackagePluginResourceProvider
    ) -> None:
        try:
            existing_resources = getattr(plugin, "resources")
        except AttributeError:
            existing_resources = None
        except Exception as e:
            raise ConfigurationError(
                f"Failed to inspect plugin resources attribute: {e}"
            )

        if existing_resources is not None:
            return

        try:
            setattr(plugin, "resources", resources)
        except Exception as e:
            raise ConfigurationError(
                "Plugin constructors must accept a resource provider or expose a writable 'resources' attribute."
            ) from e

    def load(self) -> None:
        if self._loaded:
            return

        for entry_point in entry_points(group=self.ENTRYPOINT_GROUP):
            try:
                plugin_cls = entry_point.load()
            except CompatibilityError:
                raise
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load plugin from entry point '{entry_point.name}': {e}"
                )

            try:
                resources = PackagePluginResourceProvider.from_entry_point(entry_point)
                plugin = self._instantiate_plugin(plugin_cls, resources)
                self._attach_resources_if_needed(plugin, resources)
            except CompatibilityError:
                raise
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to instantiate plugin from entry point '{entry_point.name}': {e}"
                )

            if not isinstance(plugin, DocumentationPlugin):
                raise ConfigurationError(
                    f"Plugin entry point '{entry_point.name}' does not implement DocumentationPlugin."
                )

            ensure_plugin_api_compatible(plugin.manifest.plugin_api_version)

            plugin_id = plugin.manifest.plugin_id
            if plugin_id in self._plugins:
                raise ConfigurationError(
                    f"Duplicate plugin ID '{plugin_id}' found while loading entry point '{entry_point.name}'."
                )
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
