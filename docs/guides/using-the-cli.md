# Using The CLI

This guide documents the current `docops` command-line interface.

## Command Surface

The host currently exposes four command entries:

- `docops plugins`
- `docops providers`
- `docops docs get`
- `docops run`

## `docops plugins`

Lists discovered plugin instances.

Current output format:

```text
- <plugin_id> :: <display_name> (<version>)
```

Example:

```bash
poetry run docops plugins
```

Use this command to confirm that an external plugin package is installed and discoverable before trying to execute it.

## `docops providers`

Lists available provider implementation IDs.

Example:

```bash
poetry run docops providers
```

Use this command to confirm that the built-in provider or any external provider package is discoverable.

## `docops docs get`

Fetches the current state of a single document through the provider configured for a profile.

Required options:

- `--config`, `-c`
- `--profile`, `-p`
- exactly one of `--alias` or `--path`

Optional flags:

- `--output` with `json` or `markdown`

### Select By Alias

Use `--alias` when the target document is already declared in `profile.refs`.

Example:

```bash
poetry run docops docs get \
  --config docops.yaml \
  --profile default \
  --alias handbook
```

### Select By Path

Use `--path` for ad hoc reads when the selected provider supports path resolution.

Example:

```bash
poetry run docops docs get \
  --config docops.yaml \
  --profile default \
  --path "/engineering/platform/runbook"
```

### Output

Default output is JSON so callers such as agents can consume the result predictably.

Current JSON payload includes:

- `profile_name`
- `provider_name`
- `selector_kind`
- `selector_value`
- `link`
- `document`

Use `--output markdown` when you only want the current page content.

## `docops run`

Executes a planning flow and optionally applies the resulting change set.

Required options:

- `--config`, `-c`
- `--profile`, `-p`
- `--plugin`
- `--input`, `-i`

Optional flags:

- `--apply`

## Plan Mode

Without `--apply`, the host runs in plan mode.

Example:

```bash
poetry run docops run \
  --config docops.yaml \
  --profile default \
  --plugin acme.team-docs \
  --input input.yaml
```

Current output sections:

- `=== CHANGESET ===`
- `=== DIFF ===`

The `ChangeSet` is printed as JSON. The diff is printed as text.

## Apply Mode

With `--apply`, the host also persists changes through the selected provider.

Example:

```bash
poetry run docops run \
  --config docops.yaml \
  --profile default \
  --plugin acme.team-docs \
  --input input.yaml \
  --apply
```

Current output sections:

- `=== CHANGESET ===`
- `=== DIFF ===`
- `=== APPLY RESULT ===`

## Exit Codes

Current behavior:

- plan mode returns `0` on success
- apply mode returns `0` when no operation failed
- apply mode returns `1` when any operation failed

This makes the CLI suitable for CI or scripted automation flows that need to fail fast on apply errors.

## Input Files

The input file is loaded as YAML and normalized into a plain dictionary before plugin input validation happens.

Example input file:

```yaml
team_name: Platform
```

## Recommended Workflow

1. Run `docops plugins`.
2. Run `docops providers`.
3. Use `docops docs get` to inspect the current document state when needed.
4. Prepare configuration and input YAML files.
5. Run `docops run` in plan mode first.
6. Inspect the `ChangeSet` and diff.
7. Rerun with `--apply` when ready.

## Related Documentation

- [`../getting-started.md`](../getting-started.md)
- [`../configuration.md`](../configuration.md)
- [`../execution-flow.md`](../execution-flow.md)
