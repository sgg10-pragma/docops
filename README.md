# docops

`docops` is the host application and CLI runtime for the DocOps ecosystem.

It orchestrates documentation automation workflows around `docops-sdk` by loading configuration, discovering plugins and providers, building execution context, rendering previews, and applying planned changes.

## What This Repository Contains

- A command-line interface for DocOps execution workflows.
- The host orchestrator that coordinates planning and apply flows.
- Runtime loading for plugins and providers through Python entry points.
- YAML configuration loading for providers, profiles, refs, and plugin config.
- Document loading, diff rendering, and apply delegation.
- A built-in Azure DevOps Wiki provider.
- A strict `pytest` suite with coverage enforcement.

## What This Repository Does Not Contain

- The public extension contracts and shared domain models.
- A stable SDK-level API surface for plugins and providers.
- Built-in documentation plugins.
- Project-specific documentation business logic.

Those concerns belong to `docops-sdk` and external plugin repositories.

## Relationship To `docops-sdk`

The DocOps ecosystem is intentionally split across repositories:

```text
plugin -> sdk <- host
provider -> sdk <- host
```

- `docops-sdk`
  - defines the shared contracts, domain models, and compatibility helpers
- `docops`
  - orchestrates execution around those SDK contracts
- plugins
  - implement documentation planning logic
- providers
  - implement persistence and read-side infrastructure

Canonical SDK documentation lives in the separate SDK repository:

- [`docops-sdk README`](https://github.com/sgg10-pragma/docops-sdk/blob/main/README.md)
- [`docops-sdk architecture`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/architecture.md)
- [`docops-sdk contracts API`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/api/contracts.md)
- [`docops-sdk domain API`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/api/domain.md)

## Quick Start

Install the host and its runtime dependencies:

```bash
poetry install --with test
```

Inspect the currently available extensions:

```bash
poetry run docops plugins
poetry run docops providers
```

The host currently ships with a built-in provider implementation:

- `azure_devops_wiki`

Plugins are expected to be installed separately through Python packages that expose the `docops.plugins` entry point group.

### Example Configuration

The host reads YAML configuration with provider definitions, profiles, refs, and plugin-specific settings.

```yaml
providers:
  azdo:
    type: azure_devops_wiki
    organization: acme
    project: engineering
    wiki: platform

profiles:
  default:
    provider: azdo
    refs:
      docs_root:
        provider: azdo
        kind: path
        locator:
          path: /Engineering/Teams
    plugins:
      acme.team-docs:
        parent_alias: docs_root
```

### Example Input

```yaml
team_name: Platform
```

### Plan A Run

Replace `acme.team-docs` with an installed plugin ID shown by `docops plugins`.

```bash
poetry run docops run \
  --config docops.yaml \
  --profile default \
  --plugin acme.team-docs \
  --input input.yaml
```

This prints:

- the planned `ChangeSet` as JSON
- a preview diff

### Apply A Run

```bash
poetry run docops run \
  --config docops.yaml \
  --profile default \
  --plugin acme.team-docs \
  --input input.yaml \
  --apply
```

On apply, the CLI also prints the provider `ApplyResult` and exits with code `1` if any operation failed.

## Plugin Resources

`docops` injects a `PluginResourceProvider` when loading plugin entry points.

- Resource paths are relative to the plugin package root.
- The host does not assume a fixed `resources/` directory.
- If a plugin stores assets under `resources/`, it should request them as `resources/...`.
- If a plugin already provides its own `resources` object, the host leaves it untouched.

## Documentation Map

Start here depending on your role:

- New to the host: [`docs/getting-started.md`](docs/getting-started.md)
- Need the host architecture: [`docs/architecture.md`](docs/architecture.md)
- Need the runtime execution lifecycle: [`docs/execution-flow.md`](docs/execution-flow.md)
- Need the YAML configuration model: [`docs/configuration.md`](docs/configuration.md)
- Need the host/SDK boundary: [`docs/sdk-relationship.md`](docs/sdk-relationship.md)
- Using the CLI: [`docs/guides/using-the-cli.md`](docs/guides/using-the-cli.md)
- Building a plugin for this host: [`docs/guides/build-a-plugin.md`](docs/guides/build-a-plugin.md)
- Building a provider for this host: [`docs/guides/build-a-provider.md`](docs/guides/build-a-provider.md)
- Need module-level runtime reference: [`docs/reference/core-modules.md`](docs/reference/core-modules.md)
- Need the built-in Azure DevOps provider reference: [`docs/reference/azure-devops-wiki.md`](docs/reference/azure-devops-wiki.md)
- Need host internal boundaries: [`docs/reference/internal-boundaries.md`](docs/reference/internal-boundaries.md)

The full host documentation index lives at [`docs/index.md`](docs/index.md).

## Tests

This repository ships with a strict `pytest` suite and coverage threshold.

```bash
poetry run pytest
```

The tests are also useful as executable examples of the current host behavior.
