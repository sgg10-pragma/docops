from __future__ import annotations

import mimetypes
from pathlib import Path

from pydantic import BaseModel, Field

from docops.core.exceptions import ConfigurationError
from wikiops_sdk.contracts import PluginResourceProvider
from wikiops_sdk.domain import (
    AssetPathBase,
    AssetPolicy,
    ExecutionContext,
    LocalFileAssetSource,
    PluginResourceAssetSource,
    PutAssetOperation,
)


class ResolvedAssetUpload(BaseModel):
    """Host-local resolved asset payload ready for provider upload."""

    operation: PutAssetOperation = Field(..., description="Prepared asset operation.")
    content: bytes = Field(..., description="Resolved asset bytes.")


class AssetSourceResolver:
    """Resolves asset sources declared in planned operations."""

    def resolve(
        self,
        operation: PutAssetOperation,
        ctx: ExecutionContext,
        resources: PluginResourceProvider,
    ) -> ResolvedAssetUpload:
        if isinstance(operation.source, PluginResourceAssetSource):
            content = resources.read_bytes(operation.source.relative_path)
            source_name = Path(operation.source.relative_path).name
        elif isinstance(operation.source, LocalFileAssetSource):
            candidate = self._resolve_local_file(operation.source, ctx)
            content = candidate.read_bytes()
            source_name = candidate.name
        else:  # pragma: no cover - protected by SDK discriminated union
            raise ConfigurationError(
                f"Unsupported asset source type: {type(operation.source).__name__}"
            )

        if not source_name:
            raise ConfigurationError(
                f"Asset '{operation.asset_key}' must resolve to a file name."
            )

        prepared_operation = operation.model_copy(
            update={
                "name": operation.name or source_name,
                "media_type": operation.media_type
                or mimetypes.guess_type(operation.name or source_name)[0]
                or "application/octet-stream",
            }
        )
        return ResolvedAssetUpload(operation=prepared_operation, content=content)

    def policy_from_context(self, ctx: ExecutionContext) -> AssetPolicy:
        policy_data = ctx.plugin_config.get("asset_policy") or {}
        return AssetPolicy.model_validate(policy_data)

    def _resolve_local_file(
        self, source: LocalFileAssetSource, ctx: ExecutionContext
    ) -> Path:
        candidate = Path(source.path)
        if not candidate.is_absolute():
            base_dir = self._base_dir_for_source(source, ctx)
            candidate = (base_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()

        if not candidate.is_file():
            raise ConfigurationError(
                f"Local asset source '{source.path}' does not exist or is not a file."
            )

        policy = self.policy_from_context(ctx)
        if policy.deactivate_allowed_asset_roots:
            return candidate

        config_dir = self._runtime_dir(ctx, "config_dir")
        allowed_roots = [
            ((config_dir / Path(root)).resolve() if not Path(root).is_absolute() else Path(root).resolve())
            for root in policy.allowed_asset_roots
        ]
        if not allowed_roots:
            raise ConfigurationError(
                "Local asset sources require 'asset_policy.allowed_asset_roots' unless 'deactivate_allowed_asset_roots' is true."
            )

        if not any(candidate.is_relative_to(root) for root in allowed_roots):
            allowed = ", ".join(str(root) for root in allowed_roots)
            raise ConfigurationError(
                f"Local asset '{candidate}' is outside the configured allowed_asset_roots: {allowed}."
            )

        return candidate

    def _base_dir_for_source(
        self, source: LocalFileAssetSource, ctx: ExecutionContext
    ) -> Path:
        if source.relative_to is AssetPathBase.CONFIG_DIR:
            return self._runtime_dir(ctx, "config_dir")
        if source.relative_to is AssetPathBase.INPUT_DIR:
            return self._runtime_dir(ctx, "input_dir")
        raise ConfigurationError(
            "Relative local asset paths must declare whether they are relative to the config_dir or input_dir."
        )

    @staticmethod
    def _runtime_dir(ctx: ExecutionContext, key: str) -> Path:
        value = ctx.runtime_vars.get(key)
        if not value:
            raise ConfigurationError(
                f"Runtime variable '{key}' is required to resolve local asset paths."
            )
        return Path(str(value)).resolve()
