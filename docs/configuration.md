# Configuration

This page documents the current YAML configuration model used by the host.

## Purpose

The host uses YAML configuration to describe:

- which provider instances exist
- which execution profiles exist
- which document references are available in each profile
- which plugin configuration payloads should be applied for a profile

The current configuration model is implemented by `docops.core.config_loader.ConfigLoader`.

## Top-Level Sections

The host currently recognizes these top-level sections:

- `providers`
- `profiles`

## Providers

Each provider entry describes one configured provider instance.

Example:

```yaml
providers:
  azdo:
    type: azure_devops_wiki
    organization: acme
    project: engineering
    wiki: platform
    pat_token_env: AZDO_PAT
```

### Required Fields

- `type`

The value of `type` is the provider implementation ID resolved through `ProviderManager`.

### Settings Normalization

All provider fields except `type` are normalized into the provider settings payload.

The host also injects:

- `provider_name`

using the key of the provider definition itself.

For the example above, the effective provider settings include:

```yaml
provider_name: azdo
organization: acme
project: engineering
wiki: platform
pat_token_env: AZDO_PAT
```

## Profiles

Each profile defines one execution context selection for a run.

Example:

```yaml
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

### Required Fields

- `provider`

This value must match a key defined under `providers`.

### Optional Fields

- `refs`
- `plugins`

## Refs

`refs` is a mapping of logical aliases to SDK `DocumentRef` objects.

Example:

```yaml
refs:
  docs_root:
    provider: azdo
    kind: path
    locator:
      path: /Engineering/Teams
```

The host validates each ref using the SDK domain model, which means refs must match the `DocumentRef` shape expected by `docops-sdk`.

## Plugin Configuration

`plugins` is a mapping of plugin identifiers to plugin-specific config payloads.

Example:

```yaml
plugins:
  acme.team-docs:
    parent_alias: docs_root
    section_title: Platform
```

During execution, the host resolves plugin config in this order:

1. `profile.plugins[plugin.manifest.plugin_id]`
2. `profile.plugins[plugin_id_from_command]`
3. `{}`

### Recommended Practice

Use the manifest plugin ID as the configuration key.

The host still supports lookup by the requested plugin ID, but the manifest ID is the more stable convention.

## Complete Example

```yaml
providers:
  azdo:
    type: azure_devops_wiki
    organization: acme
    project: engineering
    wiki: platform
    timeout_seconds: 30

profiles:
  default:
    provider: azdo
    refs:
      docs_root:
        provider: azdo
        kind: path
        locator:
          path: /Engineering/Teams
      inventory_page:
        provider: azdo
        kind: path
        locator:
          path: /Engineering/Inventory
    plugins:
      acme.team-docs:
        parent_alias: docs_root
      acme.inventory-sync:
        inventory_ref_alias: inventory_page
```

## Validation Rules

The host currently validates these cases explicitly:

- configuration path must exist
- configuration path must be a file
- provider definitions must include `type`
- profiles must include `provider`
- refs must validate as SDK `DocumentRef` objects

## Host Conventions

The current host uses these conventions:

- the provider config key is the runtime `provider_name`
- `providers.<name>.type` selects the provider implementation
- profile refs are declared upfront and plugins ask for a subset through alias requirements
- plugin config is profile-scoped rather than global

## Related Documentation

- [`getting-started.md`](getting-started.md)
- [`execution-flow.md`](execution-flow.md)
- [`guides/using-the-cli.md`](guides/using-the-cli.md)
- [`reference/core-modules.md`](reference/core-modules.md)
