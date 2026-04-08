from uuid import uuid4
from typing import Dict, List, Tuple, Optional

from wikiops_sdk.domain import ApplyResult, ExecutionContext

from wikiops.core.diff_engine import DiffEngine
from wikiops.core.apply_engine import ApplyEngine
from wikiops.core.plugin_manager import PluginManager
from wikiops.core.document_loader import DocumentLoader
from wikiops.core.provider_manager import ProviderManager
from wikiops.core.reference_resolver import ReferenceResolver
from wikiops.core.config_loader import AppConfig, ConfigLoader
from wikiops.core.exceptions import ConfigurationError, ProviderCompatibilityError

from wikiops.contracts.orchestrator import PlanningResult


class DefaultDocumentationOrchestrator:
    """Default implementation of the orchestration flow."""

    def __init__(self) -> None:
        self.config_loader = ConfigLoader()
        self.plugin_manager = PluginManager()
        self.provider_manager = ProviderManager()
        self.reference_resolver = ReferenceResolver()
        self.document_loader = DocumentLoader()
        self.diff_engine = DiffEngine()
        self.apply_engine = ApplyEngine()

    def _plan_internal(
        self,
        config: AppConfig,
        profile_name: str,
        plugin_id: str,
        raw_input: Dict,
        dry_run: bool = True,
    ) -> Tuple[AppConfig, ExecutionContext, PlanningResult]:
        profile = config.profiles.get(profile_name)
        if not profile:
            raise ConfigurationError(
                f"Profile '{profile_name}' not found in configuration."
            )

        provider_definition = config.providers.get(profile.provider)
        if not provider_definition:
            raise ConfigurationError(
                f"Provider '{profile.provider}' referenced by profile '{profile_name}' does not exist."
            )

        # Validate provider capabilities against plugin requirements
        provider = self.provider_manager.create(
            provider_definition.type, provider_definition.settings
        )
        provider.validate_settings()

        plugin = self.plugin_manager.get(plugin_id)

        missing_capabilities = (
            plugin.manifest.required_capabilities - provider.capabilities()
        )
        if missing_capabilities:
            missing = ", ".join(
                sorted(capability.value for capability in missing_capabilities)
            )
            raise ProviderCompatibilityError(
                f"Provider '{provider.provider_id}' does not satisfy plugin '{plugin.manifest.plugin_id}'. "
                f"Missing capabilities: {missing}."
            )

        # Determine plugin config for the profile, falling back to empty dict if not defined
        profile_plugin_config = (
            profile.plugins.get(plugin.manifest.plugin_id)
            or profile.plugins.get(plugin_id)
            or {}
        )
        plugin_config_model = plugin.get_config_model().model_validate(
            profile_plugin_config
        )
        input_model = plugin.get_input_model().model_validate(raw_input)

        # Resolve references required by the plugin
        required_aliases = plugin.required_ref_aliases(plugin_config_model, input_model)
        resolved_refs = {
            alias: provider.resolve_ref(
                self.reference_resolver.resolve_alias(profile, alias)
            )
            for alias in required_aliases
        }

        # Load documents based on resolved references
        documents = self.document_loader.load(provider, resolved_refs)

        ctx = ExecutionContext(
            run_id=str(uuid4()),
            profile_name=profile_name,
            provider_name=profile.provider,
            dry_run=dry_run,
            refs=resolved_refs,
            documents=documents,
            plugin_config=plugin_config_model.model_dump(),
            input_data=input_model.model_dump(),
            runtime_vars={
                "plugin_id": plugin.manifest.plugin_id,
                "provider_id": provider.provider_id,
            },
        )

        change_set = plugin.plan(ctx)

        return config, ctx, PlanningResult.model_validate(change_set.model_dump())

    def plan(
        self, profile_name: str, plugin_id: str, raw_input: Dict, dry_run: bool = True
    ) -> PlanningResult:
        raise NotImplementedError(
            "Planning without config file is not supported. Use plan_from_file instead."
        )

    def plan_from_file(
        self,
        config_path: str,
        profile_name: str,
        plugin_id: str,
        raw_input: Dict,
        dry_run: bool = True,
    ) -> Tuple[AppConfig, ExecutionContext, PlanningResult, str]:
        config = self.config_loader.load(config_path)
        plan = self._plan_internal(
            config, profile_name, plugin_id, raw_input, dry_run=dry_run
        )
        diff = self.diff_engine.render(plan[1].documents, plan[2])
        return config, plan[1], plan[2], diff

    def apply(self, profile_name: str, plugin_id: str, raw_input: Dict) -> ApplyResult:
        raise NotImplementedError(
            "Apply without config file is not supported. Use apply_from_file instead."
        )

    def apply_from_file(
        self,
        config_path: str,
        profile_name: str,
        plugin_id: str,
        raw_input: Dict,
    ) -> Tuple[PlanningResult, ApplyResult, str]:
        config, ctx, change_set, diff = self.plan_from_file(
            config_path=config_path,
            profile_name=profile_name,
            plugin_id=plugin_id,
            raw_input=raw_input,
            dry_run=False,
        )

        profile = config.profiles[profile_name]

        provider_definition = config.providers[profile.provider]
        provider = self.provider_manager.create(
            provider_definition.type, provider_definition.settings
        )

        apply_result = self.apply_engine.apply(provider, change_set)

        return change_set, apply_result, diff
