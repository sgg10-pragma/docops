from __future__ import annotations

import pytest

from docops.core.config_loader import ConfigLoader
from docops.core.exceptions import ConfigurationError
from wikiops_sdk.domain import RefKind


def test_load_rejects_missing_file(tmp_path) -> None:
    loader = ConfigLoader()

    with pytest.raises(ConfigurationError, match="Configuration file not found"):
        loader.load(tmp_path / "missing.yaml")


def test_load_rejects_directory_path(tmp_path) -> None:
    loader = ConfigLoader()

    with pytest.raises(ConfigurationError, match="Configuration path is not a file"):
        loader.load(tmp_path)


def test_load_accepts_empty_yaml(tmp_path) -> None:
    loader = ConfigLoader()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("", encoding="utf-8")

    config = loader.load(config_path)

    assert config.providers == {}
    assert config.profiles == {}


def test_load_injects_provider_name_and_parses_refs(tmp_path) -> None:
    loader = ConfigLoader()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
providers:
  default:
    type: azure_devops_wiki
    organization: acme
profiles:
  demo:
    provider: default
    refs:
      inventory:
        provider: default
        kind: path
        locator:
          path: /inventory
    plugins:
      demo.plugin:
        greeting: hola
""".strip(),
        encoding="utf-8",
    )

    config = loader.load(config_path)

    assert config.providers["default"].type == "azure_devops_wiki"
    assert config.providers["default"].settings["provider_name"] == "default"
    assert config.providers["default"].settings["organization"] == "acme"
    assert config.profiles["demo"].provider == "default"
    assert config.profiles["demo"].refs["inventory"].kind == RefKind.PATH
    assert config.profiles["demo"].plugins["demo.plugin"] == {"greeting": "hola"}


def test_load_rejects_provider_without_type(tmp_path) -> None:
    loader = ConfigLoader()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
providers:
  default:
    organization: acme
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="Provider 'default' is missing 'type' field"):
        loader.load(config_path)


def test_load_rejects_profile_without_provider(tmp_path) -> None:
    loader = ConfigLoader()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
profiles:
  demo:
    refs: {}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="Profile 'demo' is missing 'provider' field"):
        loader.load(config_path)
