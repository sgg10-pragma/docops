from __future__ import annotations

from typing import Any

import pytest

from wikiops.core.exceptions import ConfigurationError
from wikiops.core.plugin_manager import PluginManager
from wikiops.core.plugin_resources import PackagePluginResourceProvider
from wikiops_sdk.compat import PluginAPIIncompatibleError
from wikiops_sdk.contracts import PluginConfigModel, PluginInputModel, PluginManifest
from wikiops_sdk.domain import ChangeSet


def _patch_entry_points(monkeypatch: pytest.MonkeyPatch, entry_points: list[Any]) -> None:
    monkeypatch.setattr(
        "wikiops.core.plugin_manager.entry_points",
        lambda **_: entry_points,
    )


class ResourceAwarePlugin:
    manifest = PluginManifest.for_current_api(
        plugin_id="demo.plugin",
        display_name="Demo Plugin",
        version="1.0.0",
        description="Demo plugin for tests.",
    )

    def __init__(self, resources) -> None:
        self.resources = resources

    def get_config_model(self):
        return PluginConfigModel

    def get_input_model(self):
        return PluginInputModel

    def required_ref_aliases(self, plugin_config, input_data):
        return set()

    def plan(self, ctx):
        return ChangeSet(plugin_id=self.manifest.plugin_id)


class AnotherPlugin(ResourceAwarePlugin):
    manifest = PluginManifest.for_current_api(
        plugin_id="another.plugin",
        display_name="Another Plugin",
        version="1.0.0",
        description="Another plugin for sorting tests.",
    )


class DuplicatePlugin(ResourceAwarePlugin):
    manifest = PluginManifest.for_current_api(
        plugin_id="demo.plugin",
        display_name="Duplicate Plugin",
        version="1.0.0",
        description="Duplicate plugin for tests.",
    )


class IncompatiblePlugin(ResourceAwarePlugin):
    manifest = PluginManifest(
        plugin_id="demo.incompatible",
        display_name="Incompatible Plugin",
        version="1.0.0",
        plugin_api_version="2.0.0",
        description="Incompatible plugin for tests.",
    )


class ZeroArgPlugin(ResourceAwarePlugin):
    manifest = PluginManifest.for_current_api(
        plugin_id="demo.zeroarg",
        display_name="Zero Arg Plugin",
        version="1.0.0",
        description="Zero-arg plugin for tests.",
    )

    def __init__(self) -> None:
        self.resources = None


class SelfManagedResourceProvider:
    def has(self, relative_path: str) -> bool:
        return relative_path == "custom.txt"

    def read_text(self, relative_path: str, encoding: str = "utf-8") -> str:
        if relative_path != "custom.txt":
            raise FileNotFoundError(relative_path)
        return "custom resource"

    def list(self, prefix: str = "") -> list[str]:
        values = ["custom.txt"]
        return [value for value in values if value.startswith(prefix)]


class SelfManagedPlugin(ResourceAwarePlugin):
    manifest = PluginManifest.for_current_api(
        plugin_id="demo.selfmanaged",
        display_name="Self Managed Plugin",
        version="1.0.0",
        description="Plugin with its own resource provider.",
    )

    resources = SelfManagedResourceProvider()

    def __init__(self) -> None:
        pass


class ReadOnlyResourcesPlugin(ResourceAwarePlugin):
    manifest = PluginManifest.for_current_api(
        plugin_id="demo.readonly",
        display_name="Read Only Resources Plugin",
        version="1.0.0",
        description="Plugin with a non-writable resources attribute.",
    )

    @property
    def resources(self):
        return None

    def __init__(self) -> None:
        pass


class BrokenPlugin:
    manifest = PluginManifest.for_current_api(
        plugin_id="demo.broken",
        display_name="Broken Plugin",
        version="1.0.0",
        description="Missing required behavior.",
    )


class VarArgsPlugin(ResourceAwarePlugin):
    def __init__(self, *args) -> None:
        self.resources = args[0]


class VarKwPlugin(ResourceAwarePlugin):
    def __init__(self, **kwargs) -> None:
        self.resources = kwargs["resources"]


class PositionalPlugin(ResourceAwarePlugin):
    def __init__(self, payload) -> None:
        self.resources = payload


class InvalidConstructorPlugin(ResourceAwarePlugin):
    def __init__(self, first, second) -> None:
        self.resources = (first, second)


class BrokenEntryPoint:
    name = "broken-entrypoint"
    module = "tests.fixtures.demo_plugin"

    def load(self):
        raise RuntimeError("boom")


@pytest.mark.parametrize(
    ("plugin_cls", "expected_resource_attr"),
    [
        (ResourceAwarePlugin, "resources"),
        (VarArgsPlugin, "resources"),
        (VarKwPlugin, "resources"),
        (PositionalPlugin, "resources"),
    ],
)
def test_instantiate_plugin_accepts_supported_constructor_shapes(
    plugin_cls: type[Any],
    expected_resource_attr: str,
) -> None:
    resources = PackagePluginResourceProvider("tests.fixtures.demo_plugin")

    plugin = PluginManager._instantiate_plugin(plugin_cls, resources)

    assert getattr(plugin, expected_resource_attr) is resources


def test_instantiate_plugin_rejects_multiple_required_arguments() -> None:
    resources = PackagePluginResourceProvider("tests.fixtures.demo_plugin")

    with pytest.raises(ConfigurationError):
        PluginManager._instantiate_plugin(InvalidConstructorPlugin, resources)


def test_load_injects_plugin_resources(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    manager = PluginManager()
    entry_point = entry_point_factory("demo-plugin", ResourceAwarePlugin)
    _patch_entry_points(monkeypatch, [entry_point])

    manager.load()

    plugin = manager.get("demo.plugin")
    assert plugin.resources.has("templates/example.md")
    assert plugin.resources.read_text("templates/example.md") == "Hello from plugin resources.\n"
    assert "templates/example.md" in list(plugin.resources.list("templates"))
    assert plugin.resources.read_text("resources/example.txt") == "Hello from nested resources.\n"


def test_load_supports_zero_arg_plugins_via_post_attachment(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    manager = PluginManager()
    entry_point = entry_point_factory("zero-arg-plugin", ZeroArgPlugin)
    _patch_entry_points(monkeypatch, [entry_point])

    manager.load()

    plugin = manager.get("demo.zeroarg")
    assert plugin.resources.has("templates/example.md")


def test_load_preserves_plugin_owned_resources(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    manager = PluginManager()
    entry_point = entry_point_factory("self-managed-plugin", SelfManagedPlugin)
    _patch_entry_points(monkeypatch, [entry_point])

    manager.load()

    plugin = manager.get("demo.selfmanaged")
    assert isinstance(plugin.resources, SelfManagedResourceProvider)
    assert plugin.resources.read_text("custom.txt") == "custom resource"


def test_load_rejects_non_writable_resources_attribute(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    manager = PluginManager()
    entry_point = entry_point_factory("readonly-plugin", ReadOnlyResourcesPlugin)
    _patch_entry_points(monkeypatch, [entry_point])

    with pytest.raises(ConfigurationError, match="Failed to instantiate plugin"):
        manager.load()


def test_load_rejects_duplicate_plugin_ids(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    manager = PluginManager()
    entry_points = [
        entry_point_factory("demo-plugin", ResourceAwarePlugin),
        entry_point_factory("duplicate-plugin", DuplicatePlugin),
    ]
    _patch_entry_points(monkeypatch, entry_points)

    with pytest.raises(ConfigurationError, match="Duplicate plugin ID"):
        manager.load()


def test_load_rejects_incompatible_plugins(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    manager = PluginManager()
    entry_point = entry_point_factory("incompatible-plugin", IncompatiblePlugin)
    _patch_entry_points(monkeypatch, [entry_point])

    with pytest.raises(PluginAPIIncompatibleError):
        manager.load()


def test_load_wraps_entry_point_load_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = PluginManager()
    _patch_entry_points(monkeypatch, [BrokenEntryPoint()])

    with pytest.raises(ConfigurationError, match="Failed to load plugin"):
        manager.load()


def test_load_rejects_plugins_without_contract(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    manager = PluginManager()
    entry_point = entry_point_factory("broken-plugin", BrokenPlugin)
    _patch_entry_points(monkeypatch, [entry_point])

    with pytest.raises(ConfigurationError, match="does not implement DocumentationPlugin"):
        manager.load()


def test_get_raises_for_missing_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = PluginManager()
    _patch_entry_points(monkeypatch, [])

    with pytest.raises(ConfigurationError, match="No plugin found"):
        manager.get("missing.plugin")


def test_list_returns_sorted_plugins(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    manager = PluginManager()
    entry_points = [
        entry_point_factory("second-plugin", ResourceAwarePlugin),
        entry_point_factory("first-plugin", AnotherPlugin),
    ]
    _patch_entry_points(monkeypatch, entry_points)

    plugins = manager.list()

    assert [plugin.manifest.plugin_id for plugin in plugins] == [
        "another.plugin",
        "demo.plugin",
    ]


def test_load_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    entry_point_factory,
) -> None:
    calls = {"count": 0}

    def _entry_points(**_kwargs):
        calls["count"] += 1
        return [entry_point_factory("demo-plugin", ResourceAwarePlugin)]

    monkeypatch.setattr("wikiops.core.plugin_manager.entry_points", _entry_points)
    manager = PluginManager()

    manager.load()
    manager.load()

    assert calls["count"] == 1
