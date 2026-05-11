# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

`docops` — host application and CLI runtime for the DocOps ecosystem (Python 3.10+, Poetry, Typer, Pydantic v2). This repo is the **host**, not the SDK. Shared contracts and domain models live in `docops-sdk` (external dependency). Plugins and providers ship as separate packages discovered via Python entry points.

Dependency direction: `plugin -> sdk <- host`, `provider -> sdk <- host`. Never import plugin or provider internals into host code — speak only through SDK contracts.

## Commands

Install dev deps (Poetry required):

```bash
poetry install --with test
```

Run the test suite (strict pytest config — `--strict-config --strict-markers -ra`, branch coverage, `--cov-fail-under=90`):

```bash
poetry run pytest
poetry run pytest tests/unit/core/test_orchestrator.py          # single file
poetry run pytest tests/unit/core/test_orchestrator.py::TestName::test_case  # single test
poetry run pytest -k "expression"                               # by name expression
```

Build / packaging checks (mirrors CI `build-check` job):

```bash
poetry check
poetry build
python -m twine check dist/*
python scripts/smoke_test_host.py --expected-distribution-version "$(poetry version -s)"
```

CLI surface (after `poetry install`):

```bash
poetry run docops plugins                # list discovered plugins (entry point group: docops.plugins)
poetry run docops providers              # list provider types     (entry point group: docops.providers)
poetry run docops docs get --config C --profile P --alias A [--output json|markdown]
poetry run docops docs get --config C --profile P --path /Some/Path
poetry run docops run --config C --profile P --plugin ID --input I.yaml          # plan mode
poetry run docops run --config C --profile P --plugin ID --input I.yaml --apply  # persist; exits 1 on any failed op
```

`docs get` requires exactly one of `--alias` or `--path` — enforced in `cli/app.py`.

## Architecture

### Layout

```text
src/docops/
  cli/app.py                  # Typer entrypoint: plugins, providers, docs get, run
  core/
    orchestrator.py           # DefaultDocumentationOrchestrator — the main lifecycle
    config_loader.py          # YAML -> AppConfig (providers, profiles, refs, plugins)
    plugin_manager.py         # Loads `docops.plugins` entry points; injects PluginResourceProvider
    provider_manager.py       # Loads `docops.providers` entry points; validates settings
    reference_resolver.py     # Resolves profile alias -> DocumentRef
    document_loader.py        # Thin wrapper over provider read
    document_reader.py        # Backs `docops docs get`
    diff_engine.py            # Unified diff for updates; descriptive preview for creates
    apply_engine.py           # Delegates persistence to provider.apply_changes
    asset_source_resolver.py  # Resolves PutAssetOperation sources (local files, plugin resources)
    asset_reference_rewriter.py # Collects/rewrites asset://... keys inside document content
    plugin_resources.py       # PluginResourceProvider — package-relative resource access
    exceptions.py             # ConfigurationError, ProviderCompatibilityError
  providers/azure_devops/provider.py  # Built-in `azure_devops_wiki` provider
tests/                        # pytest; fixtures live in tests/conftest.py and tests/fixtures/
scripts/                      # release/version helpers + smoke_test_host.py used by CI
skills/docops-host/           # Natural-language operator skill for the CLI (host-runtime scope)
docs/                         # Canonical host docs; start at docs/index.md
```

### Execution Lifecycle (`DefaultDocumentationOrchestrator`)

`plan_from_file` / `apply_from_file` drive this sequence — keep edits aligned with it:

1. `ensure_python_compatible()` from SDK at orchestrator construction.
2. `ConfigLoader.load(config_path)` → `AppConfig`. Host injects `provider_name` into provider settings when absent.
3. Resolve profile + provider definition. Missing → `ConfigurationError`.
4. `ProviderManager.create(type, settings)` — validates provider API compat, contract, and `validate_settings()`.
5. `PluginManager.get(plugin_id)` — validates plugin API compat; injects `PluginResourceProvider` only if plugin does not already expose `resources`.
6. Capability check: `plugin.manifest.required_capabilities - provider.capabilities()` must be empty, else `ProviderCompatibilityError`.
7. Validate profile-scoped plugin config (lookup order: `plugins[manifest.plugin_id]` → `plugins[plugin_id_arg]` → `{}`) against `plugin.get_config_model()`. Validate input YAML against `plugin.get_input_model()`.
8. Resolve `plugin.required_ref_aliases(...)` via `ReferenceResolver` → `provider.resolve_ref(...)`.
9. `DocumentLoader.load(provider, resolved_refs)` for current content.
10. Build `ExecutionContext` (SDK type) with `run_id`, refs, documents, normalized config, input `model_dump(exclude_unset=True)` (preserves omitted-vs-null semantics), and `runtime_vars` (`plugin_id`, `provider_id`, `config_dir`, `input_dir`).
11. `plugin.plan(ctx)` → `ChangeSet`. Host re-validates via `ChangeSet.model_validate(change_set.model_dump())`.
12. Host-side validations on the planned ChangeSet: operation capabilities (`PUT_ASSET`), duplicate asset keys, asset references reachable, asset sources resolvable, asset-policy warnings.
13. `DiffEngine.render(documents, change_set)` for preview.
14. Apply mode only: provider is **recreated** before `ApplyEngine.apply(provider, change_set, ctx, plugin.resources)`. CLI exits `1` if `ApplyResult.has_failures()`.

`plan(...)` and `apply(...)` without `_from_file` raise `NotImplementedError` by design — file-based entry is the supported path.

### Plan vs Apply

- Default CLI behavior is plan mode (`dry_run=True`).
- `--apply` runs the same planning flow with `dry_run=False`, then recreates the provider and calls `provider.apply_changes(...)` via `ApplyEngine`.
- Dry-run is a **host** concern; providers do not see `ExecutionContext` during `apply_changes(...)`.

### Asset Handling

`PutAssetOperation` upload orchestration is host-managed. Document content references assets via `asset://<key>` placeholders that the host rewrites. `LocalFileAssetSource` is gated by `AssetPolicy.allowed_asset_roots` from `plugin_config.asset_policy`; setting `deactivate_allowed_asset_roots: true` appends a `asset_policy_unrestricted_local_files` warning to the ChangeSet — do not remove that warning, it is the documented escape hatch signal.

### Extension Discovery

Entry point groups:

- `docops.providers` → zero-arg factory classes. Built-in: `azure_devops_wiki = docops.providers.azure_devops:AzureDevOpsWikiProviderFactory`. Preferred host convention: factory exposes `settings_model`.
- `docops.plugins` → plugin classes loaded by `PluginManager`. Host injects `PluginResourceProvider` when the plugin does not already expose `resources`. Plugin IDs must be unique.

### Stable vs Internal

Treat as stable host behavior (`docs/reference/internal-boundaries.md`): CLI commands/options/exit codes, YAML config shape, entry point groups, capability matching, plan/apply split, asset orchestration, Azure DevOps provider settings.

Treat as internal (subject to change): `_plan_internal` and other underscore helpers, exact diff heading text beyond top-level sections, `ExecutionContext.runtime_vars` exact shape, provider recreation strategy between plan and apply, plugin constructor introspection rules.

## Testing Conventions

- Coverage gate is **90%** branch coverage on `docops`. New code must keep the suite passing or coverage is rejected.
- `tests/conftest.py` provides shared factories: `entry_point_factory`, `doc_ref_factory`, `document_factory`, `changeset_factory`, `apply_result_factory`, `app_config_factory`, `cli_runner`. Prefer these over hand-rolling SDK domain objects.
- CLI tests use `typer.testing.CliRunner` via the `cli_runner` fixture.
- `xfail_strict = true` — do not use `xfail` to paper over real failures.

## CI

`.github/workflows/ci.yml` runs:

- `pytest` on Python 3.10 / 3.11 / 3.12.
- `poetry check`, `poetry build`, `twine check`, then installs the wheel into a fresh venv and runs `scripts/smoke_test_host.py`. Run that smoke script locally before any release-touching change.

Version is static in `pyproject.toml` (`[project] version`). Bump it manually when cutting a release. There is no PyPI publish pipeline — distribution is GitHub-only (`pip install git+https://github.com/sgg10-pragma/docops.git`).

## Operator-Facing Skill

`skills/docops-host/SKILL.md` is a natural-language skill for operating the CLI. It is *not* a contract — keep it aligned with actual CLI behavior, but the CLI in `src/docops/cli/app.py` is the source of truth.

## When Changing The Lifecycle

If you touch `orchestrator.py`, walk both `docs/architecture.md` and `docs/execution-flow.md` and update them in the same change. They are referenced by the operator skill and external integrators and silently drifting them creates real downstream confusion.
