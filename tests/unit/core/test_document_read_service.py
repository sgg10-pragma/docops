from __future__ import annotations

from types import SimpleNamespace

import pytest

from docops.core.document_reader import DocumentReader
from docops.core.exceptions import ConfigurationError, ProviderCompatibilityError
from docops_sdk.domain import ProviderCapability, RefKind


class DemoProvider:
    provider_id = "demo-provider"

    def __init__(
        self,
        capabilities: set[ProviderCapability],
        document,
        *,
        resolved_ref=None,
        link: str | None = None,
    ) -> None:
        self._capabilities = capabilities
        self.document = document
        self.resolved_ref = resolved_ref or document.ref
        self.link = link
        self.resolve_calls = []
        self.get_calls = []
        self.build_link_calls = []

    def capabilities(self) -> set[ProviderCapability]:
        return self._capabilities

    def resolve_ref(self, ref, ctx=None):
        self.resolve_calls.append(ref)
        return self.resolved_ref

    def get_document(self, ref):
        self.get_calls.append(ref)
        return self.document

    def build_link(self, ref):
        self.build_link_calls.append(ref)
        return self.link


def _make_reader(monkeypatch: pytest.MonkeyPatch) -> DocumentReader:
    monkeypatch.setattr("docops.core.document_reader.ensure_python_compatible", lambda: None)
    return DocumentReader()


def test_init_validates_python_runtime_compatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = {"count": 0}

    monkeypatch.setattr(
        "docops.core.document_reader.ensure_python_compatible",
        lambda: called.__setitem__("count", called["count"] + 1),
    )

    DocumentReader()

    assert called["count"] == 1


def test_get_from_file_reads_document_by_alias(
    monkeypatch: pytest.MonkeyPatch,
    app_config_factory,
    doc_ref_factory,
    document_factory,
) -> None:
    ref = doc_ref_factory(provider="default", path="/inventory")
    resolved_ref = doc_ref_factory(provider="default", path="/resolved")
    document = document_factory(ref=resolved_ref, title="Inventory", content="# Current\n")
    config = app_config_factory(refs={"inventory": ref})
    provider = DemoProvider(
        {ProviderCapability.READ_DOCUMENT, ProviderCapability.BUILD_LINK},
        document,
        resolved_ref=resolved_ref,
        link="https://example.test/docs/inventory",
    )
    reader = _make_reader(monkeypatch)
    reader.config_loader = SimpleNamespace(load=lambda _path: config)
    reader.provider_manager = SimpleNamespace(create=lambda *_args: provider)

    result = reader.get_from_file("config.yaml", "default", alias="inventory")

    assert result.profile_name == "default"
    assert result.provider_name == "default"
    assert result.selector_kind == "alias"
    assert result.selector_value == "inventory"
    assert result.document == document
    assert result.link == "https://example.test/docs/inventory"
    assert provider.resolve_calls == [ref]
    assert provider.get_calls == [resolved_ref]
    assert provider.build_link_calls == [document.ref]


def test_get_from_file_reads_document_by_path(
    monkeypatch: pytest.MonkeyPatch,
    app_config_factory,
    doc_ref_factory,
    document_factory,
) -> None:
    resolved_ref = doc_ref_factory(provider="default", path="/resolved")
    document = document_factory(ref=resolved_ref, title="Page", content="# Page\n")
    config = app_config_factory(refs={})
    provider = DemoProvider(
        {ProviderCapability.READ_DOCUMENT, ProviderCapability.RESOLVE_BY_PATH},
        document,
        resolved_ref=resolved_ref,
    )
    reader = _make_reader(monkeypatch)
    reader.config_loader = SimpleNamespace(load=lambda _path: config)
    reader.provider_manager = SimpleNamespace(create=lambda *_args: provider)

    result = reader.get_from_file("config.yaml", "default", path="/Docs/Page")

    requested_ref = provider.resolve_calls[0]
    assert requested_ref.provider == "default"
    assert requested_ref.kind == RefKind.PATH
    assert requested_ref.locator == {"path": "/Docs/Page"}
    assert result.selector_kind == "path"
    assert result.selector_value == "/Docs/Page"
    assert result.link is None
    assert provider.build_link_calls == []


@pytest.mark.parametrize(
    ("alias", "path"),
    [
        (None, None),
        ("inventory", "/Docs/Page"),
    ],
)
def test_get_from_file_requires_exactly_one_selector(
    monkeypatch: pytest.MonkeyPatch,
    app_config_factory,
    document_factory,
    alias: str | None,
    path: str | None,
) -> None:
    config = app_config_factory(refs={})
    provider = DemoProvider({ProviderCapability.READ_DOCUMENT}, document_factory())
    reader = _make_reader(monkeypatch)
    reader.config_loader = SimpleNamespace(load=lambda _path: config)
    reader.provider_manager = SimpleNamespace(create=lambda *_args: provider)

    with pytest.raises(ConfigurationError, match="Exactly one of 'alias' or 'path'"):
        reader.get_from_file("config.yaml", "default", alias=alias, path=path)


def test_get_from_file_requires_read_document_capability(
    monkeypatch: pytest.MonkeyPatch,
    app_config_factory,
    doc_ref_factory,
    document_factory,
) -> None:
    config = app_config_factory(refs={"inventory": doc_ref_factory(provider="default")})
    provider = DemoProvider(set(), document_factory())
    reader = _make_reader(monkeypatch)
    reader.config_loader = SimpleNamespace(load=lambda _path: config)
    reader.provider_manager = SimpleNamespace(create=lambda *_args: provider)

    with pytest.raises(ProviderCompatibilityError, match="does not support document reads"):
        reader.get_from_file("config.yaml", "default", alias="inventory")


def test_get_from_file_requires_path_capability_for_path_selector(
    monkeypatch: pytest.MonkeyPatch,
    app_config_factory,
    document_factory,
) -> None:
    config = app_config_factory(refs={})
    provider = DemoProvider({ProviderCapability.READ_DOCUMENT}, document_factory())
    reader = _make_reader(monkeypatch)
    reader.config_loader = SimpleNamespace(load=lambda _path: config)
    reader.provider_manager = SimpleNamespace(create=lambda *_args: provider)

    with pytest.raises(ProviderCompatibilityError, match="path-based document reads"):
        reader.get_from_file("config.yaml", "default", path="/Docs/Page")
