# CLI Reference

This file documents the current `docops` CLI behavior that an agent should rely on.

## Preferred command prefix

Use `docops` if the executable is already installed in the current environment.

If the project is being run from a Poetry-managed checkout and `docops` is not on `PATH`, use:

```bash
poetry run docops
```

The command surface is the same either way.

## Available commands

- `docops plugins`
- `docops providers`
- `docops docs get`
- `docops run`

## `docops plugins`

Lists discovered plugins.

Example:

```bash
docops plugins
```

Current output shape:

```text
- <plugin_id> :: <display_name> (<version>)
```

Use this command before attempting to run a plugin.

## `docops providers`

Lists discovered provider types.

Example:

```bash
docops providers
```

Use this command to confirm that the built-in `azure_devops_wiki` provider is available.

## `docops docs get`

Fetches the current state of a single page through the provider configured for a profile.

Required options:

- `--config`, `-c`
- `--profile`, `-p`
- exactly one of `--alias` or `--path`

Optional flags:

- `--output json|markdown`

### Read by alias

Prefer alias-based reads when the page already exists in `profile.refs`.

```bash
docops docs get -c config.yaml -p test --alias sample_dp
```

### Read by path

Use this when the config does not already define a ref alias for the page.

```bash
docops docs get -c config.yaml -p test --path "/Engineering/Platform/Runbook"
```

### Output modes

- `json` is the default and is better for agents
- `markdown` prints only the page content body

Examples:

```bash
docops docs get -c config.yaml -p test --alias sample_dp --output json
docops docs get -c config.yaml -p test --alias sample_dp --output markdown
```

## `docops run`

Executes a plugin planning flow and optionally applies the changes.

Required options:

- `--config`, `-c`
- `--profile`, `-p`
- `--plugin`
- `--input`, `-i`

Optional flags:

- `--apply`

### Plan mode

Without `--apply`, the host only plans.

```bash
docops run -c config.yaml -p test --plugin nequi.datamind -i datamind_commands_inputs/create_dp_input.yaml
```

Expected sections:

- `=== CHANGESET ===`
- `=== DIFF ===`

### Apply mode

With `--apply`, the host also persists changes.

```bash
docops run -c config.yaml -p test --plugin nequi.datamind -i datamind_commands_inputs/create_dp_input.yaml --apply
```

Expected sections:

- `=== CHANGESET ===`
- `=== DIFF ===`
- `=== APPLY RESULT ===`

### Exit codes

- plan mode returns `0` on success
- apply mode returns `0` when no operation failed
- apply mode returns `1` when any operation failed

## Recommended runtime sequence

1. `docops providers`
2. `docops plugins`
3. `docops docs get` if current page state matters
4. `docops run` in plan mode
5. Inspect `ChangeSet` and diff
6. `docops run ... --apply` only if persistence is desired and the plan is acceptable
