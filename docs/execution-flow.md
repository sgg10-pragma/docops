# Execution Flow

This page describes how the current host processes a command from configuration loading to preview or apply.

## Command-Level Flow

The main plan/apply CLI workflow is implemented by `wikiops.cli.app` and delegated to `wikiops.core.orchestrator.DefaultDocumentationOrchestrator`.

At a high level, the host executes this sequence:

```text
CLI command
-> load config
-> resolve profile and provider
-> load plugin
-> validate compatibility and capabilities
-> resolve refs
-> load documents
-> build execution context
-> plan changes
-> render diff
-> optionally apply changes
```

## Read-Only Document Inspection Flow

`wikiops docs get` follows a smaller host-managed read path implemented by `wikiops.core.document_reader.DocumentReader`.

At a high level, the host executes this sequence:

```text
CLI command
-> load config
-> resolve profile and provider
-> validate read capabilities
-> resolve alias or path into a DocumentRef
-> fetch the current document
-> optionally build a user-facing link
-> print JSON or Markdown output
```

## Step-By-Step Runtime Lifecycle

### 1. The CLI Parses The Command

`wikiops run` reads:

- `--config`
- `--profile`
- `--plugin`
- `--input`
- optional `--apply`

The input file is loaded as YAML and normalized into a Python dictionary.

### 2. The Host Validates The Python Runtime

When the default orchestrator is created, it calls the SDK helper `ensure_python_compatible()`.

This keeps runtime compatibility policy centralized and aligned with the SDK.

### 3. Configuration Is Loaded

The host reads the YAML file through `ConfigLoader` and normalizes it into:

- provider definitions
- profile definitions
- typed `DocumentRef` values for profile refs

At this stage, the host also injects `provider_name` into provider settings when it is not explicitly present.

### 4. The Profile And Provider Are Resolved

The orchestrator looks up the requested profile and the provider referenced by that profile.

If either is missing, the run fails before plugin execution begins.

### 5. The Provider Is Created

`ProviderManager` loads provider factories through the `wikiops.providers` entry point group and creates the requested provider.

During this phase, the host validates:

- provider settings shape
- provider API compatibility
- provider contract conformance
- provider runtime settings through `validate_settings()`

### 6. The Plugin Is Loaded

`PluginManager` loads plugin classes through the `wikiops.plugins` entry point group and instantiates them.

During this phase, the host validates:

- plugin API compatibility
- plugin contract conformance
- duplicate plugin IDs

If needed, the host injects a `PluginResourceProvider` so the plugin can read packaged assets.

### 7. Capabilities Are Validated

Before planning begins, the host compares:

- `plugin.manifest.required_capabilities`
- `provider.capabilities()`

If the provider cannot satisfy the plugin, the run fails before any planning occurs.

### 8. Plugin Config And Input Are Validated

The host asks the plugin for:

- `get_config_model()`
- `get_input_model()`

It validates:

- profile-level plugin config
- runtime input YAML data

The host stores normalized dictionaries in the `ExecutionContext` rather than passing the original Pydantic model instances into `plan(ctx)`.

For runtime input, the host preserves the user's intent when serializing into `ExecutionContext.input_data`: omitted optional fields stay omitted, while explicit `null` values remain `None`.

### 9. Required Ref Aliases Are Resolved

The plugin declares required aliases through `required_ref_aliases(...)`.

The host then:

- resolves those aliases from the profile
- asks the provider to normalize or resolve each `DocumentRef`

This keeps provider-specific resolution out of plugin business logic.

### 10. Current Documents Are Loaded

The host fetches the current documents associated with the resolved refs through `DocumentLoader`.

This allows planning workflows that depend on current content.

### 11. The Execution Context Is Built

The host constructs an SDK `ExecutionContext` that includes:

- `run_id`
- `profile_name`
- `provider_name`
- `dry_run`
- resolved refs
- loaded documents
- normalized plugin config
- normalized input data that preserves omitted-vs-null input semantics
- host runtime vars such as plugin and provider identity

### 12. The Plugin Plans Changes

The plugin receives the `ExecutionContext` and returns a `ChangeSet`.

The host normalizes that result back through the SDK model layer to ensure it remains a valid `ChangeSet`.

### 13. The Host Renders A Preview Diff

The host calls `DiffEngine.render(...)` with the loaded documents and the planned change set.

Current preview behavior:

- update operations get a unified diff against current content
- create-style operations get descriptive preview text rather than a line-by-line diff

## Plan Mode Versus Apply Mode

### Plan Mode

Default CLI behavior is plan mode.

The host:

- produces a `ChangeSet`
- renders a diff preview
- does not persist changes

### Apply Mode

When `--apply` is used, the host:

1. executes the full planning flow with `dry_run=False`
2. recreates the provider
3. delegates persistence to `ApplyEngine`, which calls `provider.apply_changes(changeset)`
4. prints the `ApplyResult`

The CLI exits with code `1` if any operation failed.

## Dry-Run Enforcement

Dry-run is primarily a host concern in the current design.

The host controls whether a command stops after preview or continues into provider apply behavior. The SDK exposes `dry_run` in `ExecutionContext`, but providers are not given the execution context directly during `apply_changes(...)`.

## Failure Model

The host uses different failure layers for different problems:

- configuration errors
- compatibility errors from the SDK
- provider capability mismatches
- provider apply failures surfaced through `ApplyResult`

This separation lets the host fail early during setup while still reporting per-operation outcomes during apply.

## Related Documentation

- [`architecture.md`](architecture.md)
- [`configuration.md`](configuration.md)
- [`guides/using-the-cli.md`](guides/using-the-cli.md)
- [`reference/core-modules.md`](reference/core-modules.md)
