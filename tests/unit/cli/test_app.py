from __future__ import annotations

from types import SimpleNamespace

from wikiops.cli import app as cli_app
from wikiops.core.document_reader import DocumentReadResult
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


def test_docs_get_command_prints_json_output(
    cli_runner,
    monkeypatch,
    document_factory,
    doc_ref_factory,
) -> None:
    document = document_factory(
        ref=doc_ref_factory(provider="default", path="/Docs/Page"),
        title="Page",
        content="# Page\n",
    )
    read_result = DocumentReadResult(
        profile_name="default",
        provider_name="default",
        selector_kind="alias",
        selector_value="inventory",
        link="https://example.test/docs/page",
        document=document,
    )

    class FakeReader:
        def get_from_file(self, config, profile, alias=None, path=None):
            assert config == "config.yaml"
            assert profile == "default"
            assert alias == "inventory"
            assert path is None
            return read_result

    monkeypatch.setattr(cli_app, "DocumentReader", FakeReader)

    result = cli_runner.invoke(
        cli_app.app,
        [
            "docs",
            "get",
            "-c",
            "config.yaml",
            "-p",
            "default",
            "--alias",
            "inventory",
        ],
    )

    assert result.exit_code == 0
    assert '"selector_kind": "alias"' in result.stdout
    assert '"selector_value": "inventory"' in result.stdout
    assert '"title": "Page"' in result.stdout


def test_docs_get_command_prints_markdown_output(
    cli_runner,
    monkeypatch,
    document_factory,
    doc_ref_factory,
) -> None:
    document = document_factory(
        ref=doc_ref_factory(provider="default", path="/Docs/Page"),
        title="Page",
        content="# Page\n",
    )
    read_result = DocumentReadResult(
        profile_name="default",
        provider_name="default",
        selector_kind="path",
        selector_value="/Docs/Page",
        link=None,
        document=document,
    )

    class FakeReader:
        def get_from_file(self, config, profile, alias=None, path=None):
            assert config == "config.yaml"
            assert profile == "default"
            assert alias is None
            assert path == "/Docs/Page"
            return read_result

    monkeypatch.setattr(cli_app, "DocumentReader", FakeReader)

    result = cli_runner.invoke(
        cli_app.app,
        [
            "docs",
            "get",
            "-c",
            "config.yaml",
            "-p",
            "default",
            "--path",
            "/Docs/Page",
            "--output",
            "markdown",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout == "# Page\n"


def test_docs_get_command_requires_a_selector(cli_runner) -> None:
    result = cli_runner.invoke(
        cli_app.app,
        ["docs", "get", "-c", "config.yaml", "-p", "default"],
    )

    assert result.exit_code == 2
    assert "Exactly one of --alias or --path must be provided." in result.output


def test_docs_get_command_rejects_multiple_selectors(cli_runner) -> None:
    result = cli_runner.invoke(
        cli_app.app,
        [
            "docs",
            "get",
            "-c",
            "config.yaml",
            "-p",
            "default",
            "--alias",
            "inventory",
            "--path",
            "/Docs/Page",
        ],
    )

    assert result.exit_code == 2
    assert "Exactly one of --alias or --path must be provided." in result.output


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
        def plan_from_file(
            self,
            config,
            profile,
            plugin,
            raw_input,
            dry_run=True,
            input_path=None,
        ):
            assert config == "config.yaml"
            assert profile == "default"
            assert plugin == "demo.plugin"
            assert raw_input == {"title": "Example"}
            assert dry_run is True
            assert input_path == str(input_path_arg)
            return object(), object(), change_set, "diff output"

    monkeypatch.setattr(cli_app, "DefaultDocumentationOrchestrator", FakeOrchestrator)

    input_path_arg = input_path

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
        def apply_from_file(self, config, profile, plugin, raw_input, input_path=None):
            assert raw_input == {"title": "Example"}
            assert input_path == str(input_path_arg)
            return change_set, apply_result, "diff output"

    monkeypatch.setattr(cli_app, "DefaultDocumentationOrchestrator", FakeOrchestrator)

    input_path_arg = input_path

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
        def apply_from_file(self, config, profile, plugin, raw_input, input_path=None):
            assert input_path == str(input_path_arg)
            return change_set, apply_result, "diff output"

    monkeypatch.setattr(cli_app, "DefaultDocumentationOrchestrator", FakeOrchestrator)

    input_path_arg = input_path

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
