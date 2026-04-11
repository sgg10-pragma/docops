# Internal Boundaries

This page documents which host behaviors should be treated as stable runtime behavior and which should be treated as internal implementation details.

## Purpose

The host has to balance two goals:

- provide a predictable runtime for users and extension authors
- preserve enough freedom to evolve internal implementation details

This page makes that line explicit.

## Stable Enough To Document As Host Behavior

The following behaviors are stable enough to rely on as current host behavior:

- CLI commands, options, and exit codes
- the host-managed read-only `wikiops docs get` flow
- YAML configuration structure for providers, profiles, refs, and plugin config
- plugin and provider discovery through the SDK-defined entry point groups
- runtime compatibility checks for Python, plugins, and providers
- provider capability matching against plugin manifest requirements
- package-relative plugin resource access
- preservation of plugin-owned `resources` when already present
- plan versus apply behavior in the CLI
- built-in Azure DevOps provider settings, capabilities, and path-based ref behavior

## Host Conventions Rather Than SDK Guarantees

The following conventions belong to the host, not to `wikiops-sdk`:

- plugin constructor compatibility behavior during resource injection
- provider factory loading through zero-argument factory classes
- `settings_model` as the preferred host factory convention
- `provider_name` injection into provider settings
- profile-scoped plugin configuration lookup order

These conventions are documented because they matter for integration with this host, but they should not be mistaken for SDK-level guarantees.

## Internal Implementation Details

The following details should not be treated as public contracts:

- exact constructor introspection rules inside `PluginManager`
- exact helper method names such as `_request`, `_upload_content`, or `_plan_internal`
- exact shape of `ExecutionContext.runtime_vars`
- exact normalization mechanics used when re-validating a planned `ChangeSet`
- exact diff formatting text or heading strings beyond the CLI-level sections
- exact provider recreation strategy between planning and apply

These details may change without changing the intended host behavior.

## Recommended Documentation Rule

When documenting or integrating with the host:

- document lifecycle and policy at the host level
- document contracts and domain models at the SDK level
- avoid publishing private helper behavior as if it were a stable extension API

## Tests As Behavioral Evidence

The host test suite is a useful source of runtime truth for current behavior.

In particular, tests currently reinforce:

- CLI exit-code behavior
- plugin resource loading behavior
- provider factory validation behavior
- orchestrator flow and failure cases
- built-in Azure DevOps provider behavior

That does not make every test-backed implementation detail a public API, but it does make the tests useful evidence when clarifying current runtime semantics.

## Related Documentation

- [`../sdk-relationship.md`](../sdk-relationship.md)
- [`../architecture.md`](../architecture.md)
- [`core-modules.md`](core-modules.md)
