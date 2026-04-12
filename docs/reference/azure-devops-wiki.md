# Azure DevOps Wiki Provider

This page documents the built-in Azure DevOps Wiki provider shipped by the host.

## Purpose

The current built-in provider integrates WikiOps with Azure DevOps Wiki through the REST API.

It is implemented in:

- `wikiops.providers.azure_devops.provider.AzureDevOpsWikiProvider`
- `wikiops.providers.azure_devops.provider.AzureDevOpsWikiProviderFactory`

## Provider ID

The provider implementation ID is:

```text
azure_devops_wiki
```

This is the `type` value used in host configuration.

## Settings Model

The host currently exposes a PAT-based settings model.

Required settings:

- `organization`
- `project`
- `wiki`

Optional settings:

- `api_version`
- `timeout_seconds`
- `pat_token_env`

Inherited host/runtime fields:

- `provider_name`
- `provider_api_version`

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

## Authentication Model

The provider uses a Personal Access Token read from an environment variable.

Default variable:

- `AZDO_PAT`

If the configured PAT variable is missing, `validate_settings()` fails.

## Supported Capabilities

The current provider advertises:

- `READ_DOCUMENT`
- `CHECK_EXISTS`
- `CREATE_DOCUMENT`
- `UPDATE_DOCUMENT`
- `CREATE_CHILD_DOCUMENT`
- `BUILD_LINK`
- `PUT_ASSET`
- `RESOLVE_BY_PATH`
- `HIERARCHICAL_PAGES`
- `VERSION_CHECK`

## Reference Model

The current implementation supports path-based refs only.

That means:

- `RefKind.PATH` is supported
- path refs must include `locator.path`
- the provider normalizes missing `DocumentRef.provider` values to the configured `provider_name`

### Important Note

This provider does not currently support ID-based ref resolution for runtime execution.

## Read-Side Behavior

### `exists(ref)`

Checks whether the given page path exists in Azure DevOps Wiki.

### `get_document(ref)`

Fetches:

- title
- content
- ETag
- selected metadata such as remote URLs

The provider returns an SDK `Document` model.

### `build_link(ref)`

Builds a user-facing Azure DevOps Wiki URL from the page path.

## Asset Behavior

The provider can upload wiki attachments through the Azure DevOps Wiki attachments endpoint.

Current asset behavior:

- uploads use attachment storage under `/.attachments/`
- stored names are rewritten with a short content hash suffix
- the provider returns path-based asset refs
- embeddable asset references are absolute wiki paths such as `/.attachments/logo--abcd1234.png`

## Apply Behavior

The provider supports three planned operation types:

- `UpdateDocumentOperation`
- `CreateDocumentOperation`
- `CreateChildDocumentOperation`

Host-managed asset uploads are applied before document mutations so logical `asset://...` references can be rewritten to Azure DevOps attachment paths.

### Update

Updates the page content at the resolved path.

If an expected version with `etag` is present, the provider sends `If-Match` headers.

### Create Document

Creates content at either:

- an explicit target ref, or
- a derived child path when `parent_ref` is used as a placement hint

### Create Child Document

Creates a child page under the given parent path by deriving a child path from `parent_ref` and `child_title`.

## Result Reporting

For successful operations, the provider returns:

- `OperationStatus.APPLIED`
- the resulting ref when relevant
- the resulting version when Azure DevOps returns an ETag

For unsupported operation types, the provider returns:

- `OperationStatus.SKIPPED`

For runtime errors during an operation, the provider returns:

- `OperationStatus.FAILED`
- a failure message

## Current Implementation Boundaries

The current provider is intentionally focused:

- path-based refs only
- PAT-based authentication only
- one Azure DevOps Wiki endpoint family
- no delete, move, or rename operations

## Related Documentation

- [`../configuration.md`](../configuration.md)
- [`../guides/build-a-provider.md`](../guides/build-a-provider.md)
- [`core-modules.md`](core-modules.md)
- [`wikiops-sdk provider guide`](https://github.com/sgg10/wikiops-sdk/blob/main/docs/guides/write-a-provider.md)
