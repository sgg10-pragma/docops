# Using The CLI

This guide documents the current `wikiops` command-line interface.

## Command Surface

The host currently exposes three commands:

- `wikiops plugins`
- `wikiops providers`
- `wikiops run`

## `wikiops plugins`

Lists discovered plugin instances.

Current output format:

```text
- <plugin_id> :: <display_name> (<version>)
```

Example:

```bash
poetry run wikiops plugins
```

Use this command to confirm that an external plugin package is installed and discoverable before trying to execute it.

## `wikiops providers`

Lists available provider implementation IDs.

Example:

```bash
poetry run wikiops providers
```

Use this command to confirm that the built-in provider or any external provider package is discoverable.

## `wikiops run`

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
poetry run wikiops run \
  --config wikiops.yaml \
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
poetry run wikiops run \
  --config wikiops.yaml \
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

1. Run `wikiops plugins`.
2. Run `wikiops providers`.
3. Prepare configuration and input YAML files.
4. Run `wikiops run` in plan mode first.
5. Inspect the `ChangeSet` and diff.
6. Rerun with `--apply` when ready.

## Related Documentation

- [`../getting-started.md`](../getting-started.md)
- [`../configuration.md`](../configuration.md)
- [`../execution-flow.md`](../execution-flow.md)
