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


if __name__ == "__main__":
    app()
