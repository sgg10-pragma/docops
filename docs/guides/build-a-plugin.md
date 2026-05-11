# Build A Plugin For This Host

This guide explains the host-side expectations for documentation plugins loaded by `docops`.

For the canonical plugin contract, read the SDK guide first:

- [`docops-sdk Write A Plugin`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/guides/write-a-plugin.md)
- [`docops-sdk contracts API`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/api/contracts.md)

This page documents the additional runtime behavior of the host.

## Discovery Model

The host discovers plugins through the SDK-defined entry point group:

```text
docops.plugins
```

The entry point target is expected to be a plugin class that the host can instantiate.

## Contract Expectations

The plugin must structurally conform to `DocumentationPlugin` from `docops_sdk.contracts`.

That means the host expects:

- `manifest`
- `resources`
- `get_config_model()`
- `get_input_model()`
- `required_ref_aliases(...)`
- `plan(ctx)`

The host validates this contract at runtime.

## Compatibility Validation

During plugin loading, the host calls the SDK compatibility helper for the plugin API version declared in the manifest.

The host follows the SDK compatibility behavior rather than redefining its own version policy.

That means strictness is aligned with the SDK behavior, including `DOCOPS_SDK_STRICT_COMPAT`.

## Resource Injection

The host provides a plugin resource accessor backed by the plugin package.

Current host behavior:

- resource paths are relative to the plugin package root
- the host does not assume a fixed `resources/` directory
- if the plugin ships assets under `resources/`, it should read them as `resources/...`

The host accepts these patterns:

- constructor accepts a resource provider
- constructor accepts `resources=`
- constructor is zero-argument and the plugin exposes a writable `resources` attribute
- plugin already owns a `resources` object, in which case the host preserves it

### Example

```python
class TeamDocsPlugin:
    manifest = PluginManifest.for_current_api(
        plugin_id="acme.team-docs",
        display_name="Team Docs",
        version="1.0.0",
        description="Plans team documentation pages.",
    )

    def __init__(self, resources):
        self.resources = resources
```

### Important Note

The constructor compatibility behavior is a host runtime feature, not an SDK guarantee.

If you want the most predictable host behavior, prefer an explicit constructor that accepts `resources`.

## Config And Input Flow

During execution, the host:

1. loads profile-scoped plugin config from YAML
2. validates it through `get_config_model()`
3. loads runtime input YAML
4. validates it through `get_input_model()`
5. stores normalized dictionaries in `ExecutionContext.plugin_config` and `ExecutionContext.input_data`

That means `plan(ctx)` currently receives dictionaries inside the context, not the original typed model instances.

`ExecutionContext.input_data` preserves only fields explicitly provided by the user input. Omitted optional fields stay omitted, while explicit `null` values are preserved as `None`.

## Reference Resolution Flow

The plugin should declare required aliases through `required_ref_aliases(...)`.

The host then:

- resolves those aliases from the selected profile
- asks the provider to normalize or resolve each `DocumentRef`
- loads the corresponding current documents

The plugin should treat `ExecutionContext.refs` and `ExecutionContext.documents` as the main runtime inputs for resolved document state.

## Capability Matching

The host validates `plugin.manifest.required_capabilities` against the selected provider before planning begins.

Recommended practice:

- declare only the capabilities you genuinely require
- do not assume all providers can create hierarchical pages, build links, or perform version checks

## Recommended Plugin Workflow

1. Define a manifest with an explicit plugin ID.
2. Define config and input models.
3. Declare required aliases narrowly.
4. Use `ExecutionContext.refs` and `ExecutionContext.documents` during planning.
5. Return a provider-agnostic `ChangeSet`.
6. Use warnings and notes when planning is partial or degraded.

## Common Mistakes To Avoid

- importing host internals instead of relying on `docops-sdk`
- hardcoding provider-specific persistence behavior into the plugin
- bypassing `required_ref_aliases(...)` and trying to resolve provider details manually
- assuming plugin resource paths start inside a fixed `resources/` root
- relying on host-private behaviors as if they were SDK guarantees

## Related Documentation

- [`../sdk-relationship.md`](../sdk-relationship.md)
- [`../execution-flow.md`](../execution-flow.md)
- [`../reference/internal-boundaries.md`](../reference/internal-boundaries.md)
- [`docops-sdk Write A Plugin`](https://github.com/sgg10-pragma/docops-sdk/blob/main/docs/guides/write-a-plugin.md)
