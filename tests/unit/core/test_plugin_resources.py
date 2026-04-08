from __future__ import annotations

import pytest

from wikiops.core.plugin_resources import PackagePluginResourceProvider


def test_from_entry_point_reads_packaged_resources(entry_point_factory) -> None:
    entry_point = entry_point_factory("demo-plugin", object)

    provider = PackagePluginResourceProvider.from_entry_point(entry_point)

    assert provider.read_text("templates/example.md") == "Hello from plugin resources.\n"


@pytest.mark.parametrize("value", ["", ".", "/absolute/path", "../escape"])
def test_normalize_path_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        PackagePluginResourceProvider._normalize_path(value)


def test_has_returns_false_for_invalid_and_missing_paths() -> None:
    provider = PackagePluginResourceProvider("tests.fixtures.demo_plugin")

    assert provider.has("../escape") is False
    assert provider.has("missing.txt") is False


def test_read_text_rejects_missing_files() -> None:
    provider = PackagePluginResourceProvider("tests.fixtures.demo_plugin")

    with pytest.raises(FileNotFoundError, match="Plugin resource 'missing.txt'"):
        provider.read_text("missing.txt")


def test_list_supports_prefix_filtering() -> None:
    provider = PackagePluginResourceProvider("tests.fixtures.demo_plugin")

    assert list(provider.list("templates")) == ["templates/example.md"]
    assert list(provider.list("resources")) == ["resources/example.txt"]
