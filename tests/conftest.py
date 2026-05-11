from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import pytest
from typer.testing import CliRunner

from docops.core.config_loader import AppConfig, ProfileDefinition, ProviderDefinition
from docops_sdk.domain import (
    ApplyResult,
    AppliedOperationResult,
    ChangeSet,
    Document,
    DocumentRef,
    DocumentVersion,
    OperationStatus,
    RefKind,
)


@dataclass
class FakeEntryPoint:
    name: str
    target: Any
    module: str = "tests.fixtures.demo_plugin"

    def load(self) -> Any:
        return self.target


@pytest.fixture
def entry_point_factory() -> Callable[..., FakeEntryPoint]:
    def _make(
        name: str,
        target: Any,
        module: str = "tests.fixtures.demo_plugin",
    ) -> FakeEntryPoint:
        return FakeEntryPoint(name=name, target=target, module=module)

    return _make


@pytest.fixture
def doc_ref_factory() -> Callable[..., DocumentRef]:
    def _make(
        *,
        provider: str = "demo-provider",
        path: str = "/docs/example",
        kind: RefKind = RefKind.PATH,
        **extra: Any,
    ) -> DocumentRef:
        return DocumentRef(provider=provider, kind=kind, locator={"path": path}, **extra)

    return _make


@pytest.fixture
def document_factory(
    doc_ref_factory: Callable[..., DocumentRef],
) -> Callable[..., Document]:
    def _make(
        *,
        ref: DocumentRef | None = None,
        title: str = "Example",
        content: str = "# Example\n",
        version: DocumentVersion | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        return Document(
            ref=ref or doc_ref_factory(),
            title=title,
            content=content,
            version=version,
            metadata=metadata or {},
        )

    return _make


@pytest.fixture
def changeset_factory() -> Callable[..., ChangeSet]:
    def _make(
        *,
        plugin_id: str = "demo.plugin",
        operations: list[Any] | None = None,
        warnings: list[Any] | None = None,
        notes: list[Any] | None = None,
    ) -> ChangeSet:
        return ChangeSet(
            plugin_id=plugin_id,
            operations=operations or [],
            warnings=warnings or [],
            notes=notes or [],
        )

    return _make


@pytest.fixture
def apply_result_factory() -> Callable[..., ApplyResult]:
    def _make(
        *,
        provider_name: str = "demo-provider",
        statuses: list[OperationStatus] | None = None,
    ) -> ApplyResult:
        results = [
            AppliedOperationResult(operation_id=f"op-{index}", status=status)
            for index, status in enumerate(statuses or [], start=1)
        ]
        return ApplyResult(provider_name=provider_name, results=results)

    return _make


@pytest.fixture
def app_config_factory() -> Callable[..., AppConfig]:
    def _make(
        *,
        provider_name: str = "default",
        provider_type: str = "demo-provider",
        provider_settings: dict[str, Any] | None = None,
        profile_name: str = "default",
        refs: dict[str, DocumentRef] | None = None,
        plugins: dict[str, dict[str, Any]] | None = None,
    ) -> AppConfig:
        return AppConfig(
            providers={
                provider_name: ProviderDefinition(
                    type=provider_type,
                    settings=provider_settings or {"provider_name": provider_name},
                )
            },
            profiles={
                profile_name: ProfileDefinition(
                    provider=provider_name,
                    refs=refs or {},
                    plugins=plugins or {},
                )
            },
        )

    return _make


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()
