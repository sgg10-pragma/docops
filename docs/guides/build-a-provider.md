# Build A Provider For This Host

This guide explains the host-side expectations for provider packages loaded by `wikiops`.

For the canonical provider contract, read the SDK guide first:

- [`wikiops-sdk Write A Provider`](https://github.com/sgg10/wikiops-sdk/blob/main/docs/guides/write-a-provider.md)
- [`wikiops-sdk contracts API`](https://github.com/sgg10/wikiops-sdk/blob/main/docs/api/contracts.md)

This page documents the additional runtime behavior of the host.

## Discovery Model

The host discovers providers through the SDK-defined entry point group:

```text
wikiops.providers
```

The current host expects each entry point target to be a provider factory class that can be instantiated with no arguments.

## Host Factory Convention

The current host uses a host-local provider factory convention.

Recommended members:

- `provider_id`
- `settings_model`
- `create(settings)`

### Example

```python
class DemoProviderFactory:
    provider_id = "demo-provider"
    settings_model = DemoProviderSettings

    def create(self, settings: DemoProviderSettings) -> DemoProvider:
        return DemoProvider(settings)
```

### Important Note

This factory convention belongs to the host. It is not defined by `wikiops-sdk`.

The SDK defines the provider contract itself. The host defines how provider implementations are discovered and instantiated.

## Settings Validation And Compatibility

The host currently validates providers in two stages.

### Typed Settings Path

If the factory exposes `settings_model`, the host:

1. validates the YAML settings against that model
2. validates provider API compatibility through the SDK helper
3. passes the typed settings into `create(settings)`

### Legacy Path

If the factory does not expose `settings_model`, the host still supports the factory as long as the resulting provider exposes `settings` based on `ProviderSettings`.

This keeps the current host compatible with older provider factory shapes while favoring explicit typed settings models.

## Contract Expectations

The resulting provider instance must structurally conform to `DocumentProvider` from `wikiops_sdk.contracts`.

That means the host expects:

- `provider_id`
- `capabilities()`
- `validate_settings()`
- `resolve_ref(ref, ctx)`
- `exists(ref)`
- `get_document(ref)`
- `build_link(ref)`
- `apply_changes(changeset)`

The host validates this contract at runtime.

## Capability Matching

The host compares the selected provider capabilities against the plugin manifest requirements before planning begins.

If a provider does not advertise the required capabilities, the run fails before plugin execution.

## Apply Model

Providers do not receive a host-owned execution plan callback sequence. They receive a normalized SDK `ChangeSet` and are expected to translate and persist its operations.

Recommended practice:

- advertise only real capabilities
- return precise `ApplyResult` and `AppliedOperationResult` values
- populate `resolved_ref` for newly created pages when possible
- populate `resulting_version` when version-aware persistence is available

## Recommended Provider Workflow

1. Define a typed settings model based on `ProviderSettings`.
2. Expose a zero-argument factory with `provider_id` and `settings_model`.
3. Create a provider instance that implements `DocumentProvider`.
4. Validate credentials and settings in `validate_settings()`.
5. Implement deterministic `resolve_ref`, `get_document`, and `apply_changes` behavior.

## Common Mistakes To Avoid

- exporting a provider instance directly instead of a factory class
- omitting `settings_model` without ensuring the provider exposes typed `settings`
- advertising unsupported capabilities
- mixing plugin business logic into provider code
- treating the host factory model as if it were defined by the SDK itself

## Related Documentation

- [`../sdk-relationship.md`](../sdk-relationship.md)
- [`../execution-flow.md`](../execution-flow.md)
- [`../reference/azure-devops-wiki.md`](../reference/azure-devops-wiki.md)
- [`wikiops-sdk Write A Provider`](https://github.com/sgg10/wikiops-sdk/blob/main/docs/guides/write-a-provider.md)
