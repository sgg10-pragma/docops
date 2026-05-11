#!/usr/bin/env python3
"""Run a basic smoke test against an installed docops distribution."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from importlib import import_module
from importlib.metadata import distribution, entry_points, version as distribution_version


EXPECTED_PROVIDER_ENTRYPOINT = "azure_devops_wiki"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exercise the installed docops host surface after installation."
    )
    parser.add_argument(
        "--expected-distribution-version",
        required=False,
        help="Expected installed version of the docops distribution.",
    )
    return parser.parse_args()


def assert_distribution_version(expected_version: str | None) -> None:
    if expected_version is None:
        return

    installed_version = distribution_version("docops")
    if installed_version != expected_version:
        raise RuntimeError(
            f"Installed docops version '{installed_version}' does not match "
            f"expected version '{expected_version}'."
        )


def assert_imports() -> None:
    docops = import_module("docops")
    cli_app = import_module("docops.cli.app")
    provider_module = import_module("docops.providers.azure_devops")

    assert hasattr(docops, "__version__")
    assert cli_app.app is not None
    assert hasattr(provider_module, "AzureDevOpsWikiProviderFactory")


def assert_entry_points() -> None:
    provider_groups = entry_points(group="docops.providers")
    names = {entry_point.name for entry_point in provider_groups}
    assert EXPECTED_PROVIDER_ENTRYPOINT in names


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("docops")
    if executable is None:
        raise RuntimeError("Installed docops console script was not found on PATH.")

    return subprocess.run(
        [executable, *args],
        check=False,
        text=True,
        capture_output=True,
    )


def assert_cli_behavior() -> None:
    help_result = run_cli("--help")
    if help_result.returncode != 0:
        raise RuntimeError(help_result.stderr or help_result.stdout)
    assert "DocOps CLI" in help_result.stdout
    assert "docs" in help_result.stdout

    providers_result = run_cli("providers")
    if providers_result.returncode != 0:
        raise RuntimeError(providers_result.stderr or providers_result.stdout)
    assert EXPECTED_PROVIDER_ENTRYPOINT in providers_result.stdout

    plugins_result = run_cli("plugins")
    if plugins_result.returncode != 0:
        raise RuntimeError(plugins_result.stderr or plugins_result.stdout)

    docs_result = run_cli("docs", "get", "--help")
    if docs_result.returncode != 0:
        raise RuntimeError(docs_result.stderr or docs_result.stdout)
    assert "Fetch and print the current state of a document." in docs_result.stdout


def assert_distribution_metadata() -> None:
    package = distribution("docops")
    assert package.metadata["Name"] == "docops"


def main() -> int:
    args = parse_args()
    assert_distribution_version(args.expected_distribution_version)
    assert_distribution_metadata()
    assert_imports()
    assert_entry_points()
    assert_cli_behavior()

    print("docops smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
