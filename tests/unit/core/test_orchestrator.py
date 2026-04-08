from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import Field

from wikiops.core.config_loader import AppConfig, ProfileDefinition, ProviderDefinition
from wikiops.core.exceptions import ConfigurationError, ProviderCompatibilityError
from wikiops.core.orchestrator import DefaultDocumentationOrchestrator
from wikiops_sdk.contracts import PluginConfigModel, PluginInputModel, PluginManifest
from wikiops_sdk.domain import (
    ApplyResult,
    ChangeSet,
    Document,
    DocumentRef,
    OperationStatus,
    ProviderCapability,
    UpdateDocumentOperation,
)


class DemoPluginConfig(PluginConfigModel):
    greeting: str = Field(default="hello")


class DemoPluginInput(PluginInputModel):
    title: str


class RecordingPlugin:
    manifest = PluginManifest.for_current_api(
        plugin_id="demo.plugin",
        display_name="Demo Plugin",
        version="1.0.0",
        description="Plugin used for orchestrator tests.",
    )

    def __init__(self) -> None:
        self.received_ctx = None

    def get_config_model(self):
        return DemoPluginConfig

    def get_input_model(self):
        return DemoPluginInput

    def required_ref_aliases(self, plugin_config, input_data):
        assert plugin_config.greeting
        assert input_data.title
        return {"inventory"}

    def plan(self, ctx):
        self.received_ctx = ctx
        return ChangeSet(
            plugin_id=self.manifest.plugin_id,
            operations=[
                UpdateDocumentOperation(
                    ref=ctx.refs["inventory"],
                    new_content="# Planned\n",
                )
            ],
        )


class CapabilityHungryPlugin(RecordingPlugin):
    manifest = PluginManifest.for_current_api(
        plugin_id="hungry.plugin",
        display_name="Hungry Plugin",
        version="1.0.0",
        description="Plugin requiring update capability.",
        required_capabilities={ProviderCapability.UPDATE_DOCUMENT},
    )


class DemoProvider:
    provider_id = "demo-provider"

    def __init__(
        self,
        capabilities: set[ProviderCapability],
        document: Document,
        resolved_ref: DocumentRef | None = None,
    ) -> None:
        self._capabilities = capabilities
        self.document = document
        self.resolved_ref = resolved_ref
        self.resolve_calls: list[DocumentRef] = []
        self.validate_calls = 0

    def capabilities(self) -> set[ProviderCapability]:
        return self._capabilities

    def validate_settings(self) -> None:
        self.validate_calls += 1

    def resolve_ref(self, ref: DocumentRef, ctx=None) -> DocumentRef:
        self.resolve_calls.append(ref)
        return self.resolved_ref or ref

    def exists(self, ref: DocumentRef) -> bool:
        return True

    def get_document(self, ref: DocumentRef) -> Document:
        return self.document

    def build_link(self, ref: DocumentRef) -> str | None:
        return None

    def apply_changes(self, changeset: ChangeSet) -> ApplyResult:
        return ApplyResult(provider_name="default")


def _build_config(ref: DocumentRef, plugins: dict[str, dict[str, object]]) -> AppConfig:
    return AppConfig(
        providers={
            "default": ProviderDefinition(
                type="demo-provider",
                settings={"provider_name": "default"},
            )
        },
        profiles={
            "default": ProfileDefinition(
                provider="default",
                refs={"inventory": ref},
                plugins=plugins,
            )
        },
    )


def test_init_validates_python_runtime_compatibility(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"count": 0}

    monkeypatch.setattr(
        "wikiops.core.orchestrator.ensure_python_compatible",
        lambda: called.__setitem__("count", called["count"] + 1),
    )

    DefaultDocumentationOrchestrator()

    assert called["count"] == 1


def test_plan_raises_when_profile_is_missing() -> None:
    orchestrator = DefaultDocumentationOrchestrator()
    config = AppConfig()

    with pytest.raises(ConfigurationError, match="Profile 'missing' not found"):
        orchestrator._plan_internal(config, "missing", "demo.plugin", {"title": "Example"})


def test_plan_raises_when_provider_definition_is_missing() -> None:
    orchestrator = DefaultDocumentationOrchestrator()
    ref = DocumentRef(provider="default", kind="path", locator={"path": "/docs"})
    config = AppConfig(
        profiles={
            "default": ProfileDefinition(provider="default", refs={"inventory": ref})
        }
    )

    with pytest.raises(ConfigurationError, match="Provider 'default'.*does not exist"):
        orchestrator._plan_internal(config, "default", "demo.plugin", {"title": "Example"})


def test_plan_raises_when_provider_capabilities_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    doc_ref_factory,
    document_factory,
) -> None:
    ref = doc_ref_factory(provider="default", path="/docs")
    config = _build_config(ref, {"hungry.plugin": {}})
    provider = DemoProvider(set(), document_factory(ref=ref))
    plugin = CapabilityHungryPlugin()
    orchestrator = DefaultDocumentationOrchestrator()
    orchestrator.provider_manager = SimpleNamespace(create=lambda *_args: provider)
    orchestrator.plugin_manager = SimpleNamespace(get=lambda _plugin_id: plugin)

    with pytest.raises(ProviderCompatibilityError, match="Missing capabilities"):
        orchestrator._plan_internal(config, "default", "hungry.plugin", {"title": "Example"})


@pytest.mark.parametrize(
    ("plugins", "plugin_id", "expected_greeting"),
    [
        ({"demo.plugin": {"greeting": "from-manifest"}}, "entrypoint.plugin", "from-manifest"),
        ({"entrypoint.plugin": {"greeting": "from-entrypoint"}}, "entrypoint.plugin", "from-entrypoint"),
    ],
)
def test_plan_internal_builds_context_and_uses_plugin_config_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
    doc_ref_factory,
    document_factory,
    plugins: dict[str, dict[str, object]],
    plugin_id: str,
    expected_greeting: str,
) -> None:
    ref = doc_ref_factory(provider="default", path="/inventory")
    resolved_ref = doc_ref_factory(provider="default", path="/resolved")
    document = document_factory(ref=resolved_ref, title="Inventory", content="# Current\n")
    config = _build_config(ref, plugins)
    provider = DemoProvider(
        {ProviderCapability.READ_DOCUMENT},
        document,
        resolved_ref=resolved_ref,
    )
    plugin = RecordingPlugin()
    orchestrator = DefaultDocumentationOrchestrator()
    monkeypatch.setattr(
        "wikiops.core.orchestrator.uuid4",
        lambda: UUID("11111111-1111-1111-1111-111111111111"),
    )
    orchestrator.provider_manager = SimpleNamespace(create=lambda *_args: provider)
    orchestrator.plugin_manager = SimpleNamespace(get=lambda _plugin_id: plugin)
    orchestrator.reference_resolver = SimpleNamespace(
        resolve_alias=lambda profile, alias: profile.refs[alias]
    )
    orchestrator.document_loader = SimpleNamespace(
        load=lambda _provider, refs: {"inventory": document_factory(ref=refs["inventory"], title="Inventory", content="# Current\n")}
    )

    returned_config, ctx, change_set = orchestrator._plan_internal(
        config,
        "default",
        plugin_id,
        {"title": "Example"},
    )

    assert returned_config is config
    assert ctx.run_id == "11111111-1111-1111-1111-111111111111"
    assert ctx.profile_name == "default"
    assert ctx.provider_name == "default"
    assert ctx.refs == {"inventory": resolved_ref}
    assert ctx.plugin_config == {"greeting": expected_greeting}
    assert ctx.input_data == {"title": "Example"}
    assert ctx.runtime_vars == {
        "plugin_id": "demo.plugin",
        "provider_id": "demo-provider",
    }
    assert provider.resolve_calls == [ref]
    assert plugin.received_ctx == ctx
    assert change_set.plugin_id == "demo.plugin"
    assert len(change_set.operations) == 1


def test_plan_and_apply_raise_without_config_file() -> None:
    orchestrator = DefaultDocumentationOrchestrator()

    with pytest.raises(NotImplementedError):
        orchestrator.plan("default", "demo.plugin", {"title": "Example"})

    with pytest.raises(NotImplementedError):
        orchestrator.apply("default", "demo.plugin", {"title": "Example"})


def test_plan_from_file_loads_config_and_renders_diff(
    app_config_factory,
    changeset_factory,
    document_factory,
) -> None:
    orchestrator = DefaultDocumentationOrchestrator()
    config = app_config_factory()
    ctx = SimpleNamespace(documents={"inventory": document_factory()})
    change_set = changeset_factory()
    orchestrator.config_loader = SimpleNamespace(load=lambda _path: config)
    orchestrator._plan_internal = lambda *_args, **_kwargs: (config, ctx, change_set)
    orchestrator.diff_engine = SimpleNamespace(
        render=lambda documents, planned: f"diff:{len(documents)}:{planned.plugin_id}"
    )

    result = orchestrator.plan_from_file(
        "config.yaml",
        "default",
        "demo.plugin",
        {"title": "Example"},
    )

    assert result == (config, ctx, change_set, "diff:1:demo.plugin")


def test_apply_from_file_reuses_plan_and_applies_changes(
    app_config_factory,
    changeset_factory,
    apply_result_factory,
) -> None:
    orchestrator = DefaultDocumentationOrchestrator()
    config = app_config_factory()
    change_set = changeset_factory()
    apply_result = apply_result_factory(statuses=[OperationStatus.APPLIED])
    provider = object()
    orchestrator.plan_from_file = lambda **_kwargs: (config, object(), change_set, "diff")
    orchestrator.provider_manager = SimpleNamespace(create=lambda *_args: provider)
    orchestrator.apply_engine = SimpleNamespace(
        apply=lambda candidate, planned: apply_result
        if candidate is provider and planned is change_set
        else None
    )

    result = orchestrator.apply_from_file(
        "config.yaml",
        "default",
        "demo.plugin",
        {"title": "Example"},
    )

    assert result == (change_set, apply_result, "diff")
