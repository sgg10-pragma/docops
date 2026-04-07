from typing import Protocol, Type, runtime_checkable, Set

from pydantic import BaseModel, Field

from wikiops.domain.context import ExecutionContext
from wikiops.domain.models import ChangeSet, ProviderCapability
from wikiops.contracts.resources import PlugingResourceProvider


class PluginManifest(BaseModel):
    """Metadata that describes a documentation plugin."""

    plugin_id: str = Field(..., description="Unique identifier for the plugin.")
    display_name: str = Field(..., description="Human-readable name for the plugin.")
    version: str = Field(..., description="Version of the plugin.")
    plugin_api_version: str = Field(
        default="1.0.0",
        description="Version of the plugin API that this plugin implements.",
    )
    description: str = Field(
        ..., description="Brief description of the plugin's functionality."
    )
    required_capabilities: Set[ProviderCapability] = Field(
        default_factory=set,
        description="List of provider capabilities that this plugin requires to function.",
    )


class PluginConfigModel(BaseModel):
    """Base class for plugin configuration."""


class PluginInputModel(BaseModel):
    """Base class for plugin execution input."""


@runtime_checkable
class DocumentationPlugin(Protocol):
    """Protocol implemented by documentation plugins."""

    manifest: PluginManifest
    resources: PlugingResourceProvider

    def get_config_model(self) -> Type[PluginConfigModel]: ...

    def get_input_model(self) -> Type[PluginInputModel]: ...

    def required_ref_aliases(
        self,
        plugin_config: PluginConfigModel,
        input_data: PluginInputModel,
    ) -> Set[str]: ...

    def plan(self, ctx: ExecutionContext) -> ChangeSet: ...
