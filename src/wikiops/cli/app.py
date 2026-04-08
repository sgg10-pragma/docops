from typing import Any
from pathlib import Path

import yaml
import typer

from wikiops.core.orchestrator import DefaultDocumentationOrchestrator

app = typer.Typer(
    help="WikiOps CLI - A tool for Markdown-based documentation automation."
)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


@app.command("plugins")
def list_plugins() -> None:
    """List discovered plugins."""

    orchestrator = DefaultDocumentationOrchestrator()
    for plugin in orchestrator.plugin_manager.list():
        typer.echo(
            f"- {plugin.manifest.plugin_id} :: {plugin.manifest.display_name} ({plugin.manifest.version})"
        )


@app.command("providers")
def list_providers() -> None:
    """List discovered provider types."""

    orchestrator = DefaultDocumentationOrchestrator()
    for provider_type in orchestrator.provider_manager.list_types():
        typer.echo(f"- {provider_type}")


@app.command("run")
def run(
    config: str = typer.Option(
        ..., "--config", "-c", help="Path to the YAML config file."
    ),
    profile: str = typer.Option(
        ..., "--profile", "-p", help="Profile name to execute."
    ),
    plugin: str = typer.Option(
        ..., "--plugin", help="Plugin identifier or entry point name."
    ),
    input: str = typer.Option(
        ..., "--input", "-i", help="Path to the YAML input file."
    ),
    apply: bool = typer.Option(False, "--apply", help="Persist the planned changes."),
) -> None:
    """Plan or apply a documentation use case."""

    orchestrator = DefaultDocumentationOrchestrator()
    raw_input = _load_yaml(input)

    if apply:
        change_set, apply_result, diff = orchestrator.apply_from_file(
            config, profile, plugin, raw_input
        )
        typer.echo("=== CHANGESET ===")
        typer.echo(change_set.model_dump_json(indent=2))
        typer.echo("\n=== DIFF ===")
        typer.echo(diff or "(No diff available)")
        typer.echo("\n=== APPLY RESULT ===")
        typer.echo(apply_result.model_dump_json(indent=2))
        raise typer.Exit(code=1 if apply_result.has_failures() else 0)

    _, _, change_set, diff = orchestrator.plan_from_file(
        config, profile, plugin, raw_input, dry_run=True
    )
    typer.echo("=== CHANGESET ===")
    typer.echo(change_set.model_dump_json(indent=2))
    typer.echo("\n=== DIFF ===")
    typer.echo(diff or "(No diff generated)")


if __name__ == "__main__":
    app()
