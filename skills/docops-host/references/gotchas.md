# Gotchas

These are runtime facts the agent should keep in mind.

## 1. The host ships no built-in plugins

`docops` includes the CLI and the built-in Azure DevOps provider, but not business plugins.

Always verify plugin availability with:

```bash
docops plugins
```

## 2. Use the plugin skill for plugin input shape

The host validates plugin input, but it does not define plugin business schemas.

If the user asks for a plugin-specific YAML and the structure is not already known from the repo, load the plugin skill first.

## 3. `docs get` requires exactly one selector

`docops docs get` must receive exactly one of:

- `--alias`
- `--path`

Do not pass both.

## 4. Prefer alias-based reads when possible

If the config already defines a ref alias, use it instead of duplicating the path on the command line.

This keeps the workflow more stable and easier to reuse.

## 5. Azure DevOps requires a PAT env var

The built-in provider fails in `validate_settings()` if the configured PAT variable does not exist.

Default:

```text
AZDO_PAT
```

## 6. Plan before apply

`docops run --apply` mutates the remote documentation system.

Default behavior for agents should be:

1. run plan mode
2. inspect `ChangeSet` and diff
3. apply only if the user intends persistence

## 7. `docops run` always needs `--plugin`

If the workflow is plugin-driven, do not forget:

```bash
docops run --plugin <plugin_id> ...
```

The host cannot infer the plugin from the input file alone.

## 8. Asset workflows may depend on plugin policy

If a plugin uses local assets, the plugin config may require:

- `asset_policy.allowed_asset_roots`

Without that, local file assets can fail before apply or during apply.

## 9. `docops` and `docops-sdk` must stay aligned

If the host is loaded from a local checkout but `docops-sdk` comes from an older wheel in the virtualenv, runtime imports can fail.

If you see host/SDK API drift, reinstall the local SDK into the same environment.

## 10. Package-relative plugin resources are a host behavior

Plugin resource paths are package-relative, not implicitly rooted at `resources/` unless the plugin chose that convention itself.

Do not guess resource paths from host intuition alone; inspect the plugin repo or load its skill.

## 11. Do not verify before apply completes

If you run `docops run --apply`, wait for the command to finish and inspect `=== APPLY RESULT ===` before trying to read the resulting page. Reading too early can produce false 404s or stale content.

## 12. `docops` can be executed directly or through Poetry

In installed environments, prefer `docops ...`.

In source checkouts, it may be necessary to use:

```bash
poetry run docops ...
```
