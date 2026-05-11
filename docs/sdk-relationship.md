# Host And SDK Relationship

This page explains the boundary between `docops`, the host repository, and `docops-sdk`, the public SDK repository.

## What Belongs To The SDK

The SDK owns the public language of the ecosystem.

That includes:

- domain models such as `DocumentRef`, `Document`, `ChangeSet`, and `ExecutionContext`
- result models such as `ApplyResult`
- provider capability enums and operation models
- plugin and provider contracts such as `DocumentationPlugin` and `DocumentProvider`
- compatibility helpers and entry point group constants

Canonical SDK documentation:

- [`docops-sdk documentation index`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/index.md)
- [`docops-sdk contracts API`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/api/contracts.md)
- [`docops-sdk domain API`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/api/domain.md)
- [`docops-sdk compatibility`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/compatibility.md)

## What Belongs To The Host

The host owns runtime orchestration and policy.

That includes:

- CLI command definitions
- YAML configuration loading
- extension discovery and instantiation
- runtime compatibility checks
- capability validation
- alias resolution
- document loading
- preview generation
- apply delegation
- built-in provider implementations shipped by the host

## Public API Versus Host Implementation

The most important boundary is this:

- the SDK defines the contract
- the host defines when and how that contract is used

Examples:

- `ChangeSet` is an SDK type
- deciding when a plugin is invoked to produce a `ChangeSet` is host behavior
- `DocumentProvider` is an SDK contract
- discovering provider factories through entry points is host behavior

## Why The Split Exists

The split makes the ecosystem easier to evolve.

- plugins can depend on a stable contract layer without importing host internals
- providers can depend on the same contract layer without depending on plugin logic
- the host can change execution policy without redefining the shared language

## How The Host Uses SDK Compatibility

The host currently uses SDK compatibility helpers during startup and extension loading.

That includes:

- Python runtime checks through `ensure_python_compatible()`
- plugin API checks through `ensure_plugin_api_compatible(...)`
- provider API checks through `ensure_provider_api_compatible(...)`

The host uses the SDK-defined entry point constants rather than duplicating string literals.

## Important Caveat

The host does not redefine SDK contracts locally.

If you are writing a plugin or provider, the authoritative definition of those contracts is still the SDK documentation, not this repository.

This repository documents host-side execution and runtime policy around those contracts.

## Recommended Reading

If you are integrating with `docops`, read these in order:

1. [`architecture.md`](architecture.md)
2. [`execution-flow.md`](execution-flow.md)
3. [`guides/build-a-plugin.md`](guides/build-a-plugin.md) or [`guides/build-a-provider.md`](guides/build-a-provider.md)
4. The corresponding SDK guide:
   - [`Write A Plugin`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/guides/write-a-plugin.md)
   - [`Write A Provider`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/guides/write-a-provider.md)

## Related Documentation

- [`architecture.md`](architecture.md)
- [`execution-flow.md`](execution-flow.md)
- [`guides/build-a-plugin.md`](guides/build-a-plugin.md)
- [`guides/build-a-provider.md`](guides/build-a-provider.md)
- [`reference/internal-boundaries.md`](reference/internal-boundaries.md)
