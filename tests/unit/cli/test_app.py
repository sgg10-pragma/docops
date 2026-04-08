from __future__ import annotations

from types import SimpleNamespace

from wikiops.cli import app as cli_app
from wikiops_sdk.domain import ApplyResult, AppliedOperationResult, OperationStatus


def test_load_yaml_reads_valid_and_empty_documents(tmp_path) -> None:
    populated = tmp_path / "input.yaml"
    populated.write_text("title: Example\ncount: 2\n", encoding="utf-8")
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")

    assert cli_app._load_yaml(populated) == {"title": "Example", "count": 2}
    assert cli_app._load_yaml(empty) == {}


def test_plugins_command_lists_discovered_plugins(cli_runner, monkeypatch) -> None:
    plugin = SimpleNamespace(
        manifest=SimpleNamespace(
            plugin_id="demo.plugin",
            display_name="Demo Plugin",
            version="1.0.0",
        )
    )

    class FakeOrchestrator:
        def __init__(self) -> None:
            self.plugin_manager = SimpleNamespace(list=lambda: [plugin])

    monkeypatch.setattr(cli_app, "DefaultDocumentationOrchestrator", FakeOrchestrator)

    result = cli_runner.invoke(cli_app.app, ["plugins"])

    assert result.exit_code == 0
    assert "demo.plugin :: Demo Plugin (1.0.0)" in result.stdout


def test_providers_command_lists_discovered_provider_types(
    cli_runner,
    monkeypatch,
) -> None:
    class FakeOrchestrator:
        def __init__(self) -> None:
            self.provider_manager = SimpleNamespace(list_types=lambda: ["alpha", "omega"])

    monkeypatch.setattr(cli_app, "DefaultDocumentationOrchestrator", FakeOrchestrator)

    result = cli_runner.invoke(cli_app.app, ["providers"])

    assert result.exit_code == 0
    assert "- alpha" in result.stdout
    assert "- omega" in result.stdout


def test_run_command_prints_plan_output(
    cli_runner,
    monkeypatch,
    tmp_path,
    changeset_factory,
) -> None:
    input_path = tmp_path / "input.yaml"
    input_path.write_text("title: Example\n", encoding="utf-8")
    change_set = changeset_factory()

    class FakeOrchestrator:
        def plan_from_file(self, config, profile, plugin, raw_input, dry_run=True):
            assert config == "config.yaml"
            assert profile == "default"
            assert plugin == "demo.plugin"
            assert raw_input == {"title": "Example"}
            assert dry_run is True
            return object(), object(), change_set, "diff output"

    monkeypatch.setattr(cli_app, "DefaultDocumentationOrchestrator", FakeOrchestrator)

    result = cli_runner.invoke(
        cli_app.app,
        [
            "run",
            "-c",
            "config.yaml",
            "-p",
            "default",
            "--plugin",
            "demo.plugin",
            "-i",
            str(input_path),
        ],
    )

    assert result.exit_code == 0
    assert "=== CHANGESET ===" in result.stdout
    assert "=== DIFF ===" in result.stdout
    assert "diff output" in result.stdout


def test_run_apply_returns_success_exit_code(
    cli_runner,
    monkeypatch,
    tmp_path,
    changeset_factory,
    apply_result_factory,
) -> None:
    input_path = tmp_path / "input.yaml"
    input_path.write_text("title: Example\n", encoding="utf-8")
    change_set = changeset_factory()
    apply_result = apply_result_factory(statuses=[OperationStatus.APPLIED])

    class FakeOrchestrator:
        def apply_from_file(self, config, profile, plugin, raw_input):
            assert raw_input == {"title": "Example"}
            return change_set, apply_result, "diff output"

    monkeypatch.setattr(cli_app, "DefaultDocumentationOrchestrator", FakeOrchestrator)

    result = cli_runner.invoke(
        cli_app.app,
        [
            "run",
            "-c",
            "config.yaml",
            "-p",
            "default",
            "--plugin",
            "demo.plugin",
            "-i",
            str(input_path),
            "--apply",
        ],
    )

    assert result.exit_code == 0
    assert "=== APPLY RESULT ===" in result.stdout


def test_run_apply_returns_failure_exit_code(
    cli_runner,
    monkeypatch,
    tmp_path,
    changeset_factory,
) -> None:
    input_path = tmp_path / "input.yaml"
    input_path.write_text("title: Example\n", encoding="utf-8")
    change_set = changeset_factory()
    apply_result = ApplyResult(
        provider_name="demo-provider",
        results=[
            AppliedOperationResult(
                operation_id="op-1",
                status=OperationStatus.FAILED,
                message="boom",
            )
        ],
    )

    class FakeOrchestrator:
        def apply_from_file(self, config, profile, plugin, raw_input):
            return change_set, apply_result, "diff output"

    monkeypatch.setattr(cli_app, "DefaultDocumentationOrchestrator", FakeOrchestrator)

    result = cli_runner.invoke(
        cli_app.app,
        [
            "run",
            "-c",
            "config.yaml",
            "-p",
            "default",
            "--plugin",
            "demo.plugin",
            "-i",
            str(input_path),
            "--apply",
        ],
    )

    assert result.exit_code == 1
    assert "=== APPLY RESULT ===" in result.stdout
