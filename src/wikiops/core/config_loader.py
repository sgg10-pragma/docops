from pathlib import Path
from typing import Any, Dict, Union

import yaml
from pydantic import BaseModel, Field

from wikiops.core.exceptions import ConfigurationError
from wikiops_sdk.domain import DocumentRef


class ProviderDefinition(BaseModel):
    """Provider configuration entry from the YAML file."""

    type: str
    settings: Dict[str, Any] = Field(default_factory=dict)


class ProfileDefinition(BaseModel):
    """Execution profile entry from the YAML file."""

    provider: str
    refs: Dict[str, DocumentRef] = Field(default_factory=dict)
    plugins: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class AppConfig(BaseModel):
    """Top-level application configuration."""

    providers: Dict[str, ProviderDefinition] = Field(default_factory=dict)
    profiles: Dict[str, ProfileDefinition] = Field(default_factory=dict)


class ConfigLoader:
    """Loads and validates YAML application configuration."""

    def _prepare_providers(
        self, raw_providers: Dict[str, Any]
    ) -> Dict[str, ProviderDefinition]:
        """Validates and transforms raw provider definitions into structured ProviderDefinition instances."""
        providers = {}

        for name, provider in raw_providers.items():
            provider_type = provider.get("type")

            if not provider_type:
                raise ConfigurationError(f"Provider '{name}' is missing 'type' field.")

            settings = {k: v for k, v in provider.items() if k != "type"}
            settings.setdefault("provider_name", name)

            providers[name] = ProviderDefinition(type=provider_type, settings=settings)

        return providers

    def _prepare_profiles(
        self, raw_profiles: Dict[str, Any]
    ) -> Dict[str, ProfileDefinition]:
        """Validates and transforms raw profile definitions into structured ProfileDefinition instances."""
        profiles = {}

        for name, profile in raw_profiles.items():
            provider_name = profile.get("provider")

            if not provider_name:
                raise ConfigurationError(
                    f"Profile '{name}' is missing 'provider' field."
                )

            refs_raw = profile.get("refs", {})
            plugins_raw = profile.get("plugins", {})

            refs = {
                alias: DocumentRef.model_validate(ref_raw)
                for alias, ref_raw in refs_raw.items()
            }
            profiles[name] = ProfileDefinition(
                provider=provider_name, refs=refs, plugins=plugins_raw
            )

        return profiles

    def load(self, path: Union[str, Path]) -> AppConfig:
        config_path = Path(path)

        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        if not config_path.is_file():
            raise ConfigurationError(f"Configuration path is not a file: {config_path}")

        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        providers_section = raw.get("providers", {})
        profiles_section = raw.get("profiles", {})

        providers = self._prepare_providers(providers_section)
        profiles = self._prepare_profiles(profiles_section)

        return AppConfig(providers=providers, profiles=profiles)
