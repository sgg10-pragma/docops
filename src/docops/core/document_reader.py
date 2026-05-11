from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from docops.core.config_loader import ConfigLoader, ProfileDefinition
from docops.core.exceptions import ConfigurationError, ProviderCompatibilityError
from docops.core.provider_manager import ProviderManager
from docops.core.reference_resolver import ReferenceResolver
from docops_sdk import ensure_python_compatible
from docops_sdk.domain import Document, DocumentRef, ProviderCapability, RefKind


class DocumentReadResult(BaseModel):
    """Structured result returned by host read-only document inspection."""

    profile_name: str = Field(..., description="Profile used for the read operation.")
    provider_name: str = Field(..., description="Configured provider used for the read.")
    selector_kind: Literal["alias", "path"] = Field(
        ..., description="Kind of selector used to identify the document."
    )
    selector_value: str = Field(
        ..., description="Alias or path provided by the caller."
    )
    link: str | None = Field(
        default=None,
        description="Best-effort user-facing link for the resolved document.",
    )
    document: Document = Field(..., description="Fetched document payload.")


class DocumentReader:
    """Reads a single document through the configured provider."""

    def __init__(self) -> None:
        ensure_python_compatible()
        self.config_loader = ConfigLoader()
        self.provider_manager = ProviderManager()
        self.reference_resolver = ReferenceResolver()

    def get_from_file(
        self,
        config_path: str,
        profile_name: str,
        *,
        alias: str | None = None,
        path: str | None = None,
    ) -> DocumentReadResult:
        config = self.config_loader.load(config_path)
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

        provider = self.provider_manager.create(
            provider_definition.type, provider_definition.settings
        )
        capabilities = provider.capabilities()
        if ProviderCapability.READ_DOCUMENT not in capabilities:
            raise ProviderCompatibilityError(
                f"Provider '{provider.provider_id}' does not support document reads."
            )

        ref, selector_kind, selector_value = self._select_ref(
            profile,
            capabilities,
            alias=alias,
            path=path,
        )
        resolved_ref = provider.resolve_ref(ref)
        document = provider.get_document(resolved_ref)
        link = None
        if ProviderCapability.BUILD_LINK in capabilities:
            link = provider.build_link(document.ref)

        return DocumentReadResult(
            profile_name=profile_name,
            provider_name=profile.provider,
            selector_kind=selector_kind,
            selector_value=selector_value,
            link=link,
            document=document,
        )

    def _select_ref(
        self,
        profile: ProfileDefinition,
        capabilities: set[ProviderCapability],
        *,
        alias: str | None,
        path: str | None,
    ) -> tuple[DocumentRef, Literal["alias", "path"], str]:
        if (alias is None) == (path is None):
            raise ConfigurationError(
                "Exactly one of 'alias' or 'path' must be provided."
            )

        if alias is not None:
            return self.reference_resolver.resolve_alias(profile, alias), "alias", alias

        if ProviderCapability.RESOLVE_BY_PATH not in capabilities:
            raise ProviderCompatibilityError(
                "The selected provider does not support path-based document reads."
            )

        return (
            DocumentRef(
                provider=profile.provider,
                kind=RefKind.PATH,
                locator={"path": path},
            ),
            "path",
            path,
        )
