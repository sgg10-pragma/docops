# Core Modules

This page maps the main runtime modules of the host and explains how they interact.

## `wikiops.cli.app`

### Purpose

Defines the public CLI entry point.

### Responsibilities

- parse CLI arguments
- load input YAML
- invoke the default orchestrator for plan/apply runs
- invoke `DocumentReader` for read-only document inspection
- print `ChangeSet`, diff, and `ApplyResult` output
- print read-only document output as JSON or Markdown
- determine the exit code for apply runs

### Interactions

- instantiates `DefaultDocumentationOrchestrator`
- instantiates `DocumentReader`
- delegates plan, apply, and read-only inspection logic to the core runtime

## `wikiops.core.orchestrator`

### Purpose

Implements the host execution lifecycle.

### Responsibilities

- validate Python runtime compatibility
- load YAML configuration
- create the provider
- load the plugin
- validate provider capabilities against plugin requirements
- validate plugin config and input payloads
- resolve refs and load current documents
- build `ExecutionContext`
- invoke plugin planning
- render preview diffs
- apply changes through the provider

### Key Class

- `DefaultDocumentationOrchestrator`

### Interactions

- `ConfigLoader`
- `PluginManager`
- `ProviderManager`
- `ReferenceResolver`
- `DocumentLoader`
- `DiffEngine`
- `ApplyEngine`

## `wikiops.core.config_loader`

### Purpose

Loads and validates YAML configuration.

### Responsibilities

- validate provider definitions
- validate profile definitions
- parse refs into SDK `DocumentRef` values
- inject `provider_name` into provider settings

### Key Models

- `ProviderDefinition`
- `ProfileDefinition`
- `AppConfig`
- `ConfigLoader`

## `wikiops.core.plugin_manager`

### Purpose

Discovers and instantiates plugins.

### Responsibilities

- load plugin classes from `wikiops.plugins`
- validate plugin API compatibility
- validate plugin contract conformance
- detect duplicate plugin IDs
- inject host-managed plugin resource access when needed

### Important Note

The plugin constructor compatibility behavior is part of the host runtime, not part of the SDK contract itself.

## `wikiops.core.plugin_resources`

### Purpose

Expose plugin package files through the SDK resource contract.

### Responsibilities

- resolve package-relative paths
- reject absolute and parent-traversal paths
- read packaged text resources
- list available resource files

### Current Convention

Paths are relative to the plugin package root, not to a forced `resources/` root.

## `wikiops.core.document_reader`

### Purpose

Fetch the current state of a single document through the selected provider.

### Responsibilities

- validate Python runtime compatibility
- load YAML configuration
- create the provider
- validate read capabilities for the requested selector
- resolve alias or path selectors into a `DocumentRef`
- fetch the current document payload
- build a user-facing link when supported

### Key Models

- `DocumentReadResult`
- `DocumentReader`

## `wikiops.core.provider_manager`

### Purpose

Discovers provider factories and creates provider instances.

### Responsibilities

- load provider factories from `wikiops.providers`
- validate duplicate provider IDs
- validate typed settings when `settings_model` is present
- validate provider API compatibility
- validate provider contract conformance
- invoke provider `validate_settings()`

### Host Convention

The current host expects provider entry points to expose a factory class rather than a provider instance directly.

## `wikiops.core.reference_resolver`

### Purpose

Resolve logical aliases from a selected profile.

### Responsibilities

- map profile aliases to declared `DocumentRef` values
- fail early when a required alias is missing

## `wikiops.core.document_loader`

### Purpose

Fetch current documents through the provider.

### Responsibilities

- iterate resolved refs
- ask the provider for the corresponding current document
- return an alias-keyed document map

## `wikiops.core.diff_engine`

### Purpose

Build preview output for planned changes.

### Responsibilities

- render unified diffs for update operations
- render descriptive preview text for create-style operations

### Current Limitation

The current diff model is strongest for updates against existing document content.

## `wikiops.core.apply_engine`

### Purpose

Delegate persistence to the selected provider.

### Responsibilities

- call `provider.apply_changes(changeset)`
- return the provider `ApplyResult`

## `wikiops.providers.azure_devops.provider`

### Purpose

Provide the built-in Azure DevOps Wiki implementation.

### Responsibilities

- validate PAT-based configuration
- resolve and validate path-based refs
- read documents from Azure DevOps Wiki
- build user-facing links
- apply update, create, and create-child operations

See the dedicated provider reference:

- [`azure-devops-wiki.md`](azure-devops-wiki.md)

## Related Documentation

- [`../architecture.md`](../architecture.md)
- [`../execution-flow.md`](../execution-flow.md)
- [`../configuration.md`](../configuration.md)
- [`azure-devops-wiki.md`](azure-devops-wiki.md)
