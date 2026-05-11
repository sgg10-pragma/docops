---
name: docops-host
description: Use this skill when the user wants to configure or operate the DocOps host in natural language: inspect installed plugins or providers, create or update a DocOps YAML config, configure the built-in Azure DevOps Wiki provider, read the current content of a page with `docops docs get`, or execute a plugin with an input YAML through `docops run` in plan or apply mode. If a companion plugin skill exists, use it for plugin-specific input or business rules, then return to this skill for host execution and verification.
compatibility: Requires a shell with the `docops` CLI available directly or through `poetry run docops`. Azure DevOps flows require `AZDO_PAT` or the configured PAT env var.
metadata:
  author: sgg10
  scope: host-runtime
  version: "1.0.0"
---

# DocOps Host

## Use this skill when

Use this skill when the user wants help with the DocOps host runtime itself:

- configure `docops`
- create or update `config.yaml` or `docops.yaml`
- inspect installed plugins or providers
- configure the built-in `azure_devops_wiki` provider
- read the current content of an existing page
- run a plugin with an input YAML
- plan changes first, then optionally apply them

## Do not use this skill for

Do not use this skill as the primary source of truth for plugin business logic.

If the task depends on a plugin-specific input schema, template, managed blocks, examples, or domain rules, load the corresponding plugin skill first. Then return to this skill to run `docops` commands with the generated YAML.

Examples:

- `nequi.datamind` input design belongs to the plugin skill
- provider authoring code does not belong to this skill
- SDK contract design does not belong to this skill

## Companion plugin skills

Some plugins may publish their own companion skills. Treat the relationship like this:

- this host skill owns CLI usage, config structure, provider setup, `docs get`, `run`, plan/apply flow, and verification
- a plugin skill owns plugin-specific input shape, business rules, templates, examples, managed blocks, and domain-specific defaults

When both skills exist, use this handoff pattern:

1. Start in `docops-host` to inspect providers, plugins, config, refs, and current page state
2. Switch to the plugin skill to build or update the correct input YAML
3. Return to `docops-host` to execute `docops run`, inspect the `ChangeSet` and diff, and optionally apply changes
4. Use `docops-host` again to verify the final page content with `docops docs get`

If a companion plugin skill exists, prefer it over reconstructing the plugin input schema from memory.

## Default operating workflow

1. Confirm the runtime surface first.
   - Run `docops providers`
   - Run `docops plugins`
   - If `docops` is not available directly, use `poetry run docops`

2. If the user wants to configure DocOps.
   - Read or create the target YAML config
   - Define `providers`
   - Define `profiles`
   - Define `refs` only for pages the workflow needs
   - Define profile-scoped plugin config under `profiles.<profile>.plugins.<plugin_id>` only when the workflow is plugin-driven
   - Prefer plugin defaults over explicit overrides unless the user really needs custom behavior

3. If the user wants current page content.
   - Prefer `docops docs get --alias` when the page already exists in `profile.refs`
   - Use `docops docs get --path` only when an ad hoc path is needed
   - Default to JSON unless the user only needs the markdown body

4. If the user wants to run a plugin.
     - Confirm the plugin is installed via `docops plugins`
     - Always include `--plugin <plugin_id>` in `docops run`
     - If a companion plugin skill exists and the input YAML is plugin-specific, load that skill first
     - If no companion plugin skill exists, derive the input only from the plugin repo, examples, or validated docs already present in the workspace
     - Generate or update the input YAML
     - Run `docops run` in plan mode first
     - Inspect `=== CHANGESET ===` and `=== DIFF ===`
    - Only use `--apply` when the user explicitly wants persistence

5. After apply.
   - Inspect `=== APPLY RESULT ===`
   - Treat any failed operation as a failed run
   - Only after the apply process has completed, read the page again with `docops docs get`

## Command mapping

For exact command syntax and examples, read:

- [CLI reference](references/cli.md)

For config structure, read:

- [Configuration reference](references/configuration.md)

For the built-in Azure DevOps Wiki provider, read:

- [Azure DevOps provider reference](references/azure-devops-provider.md)

For end-to-end workflows, read:

- [Host workflows](references/workflows.md)

For pitfalls and runtime constraints, read:

- [Gotchas](references/gotchas.md)

## Behavioral rules

- Prefer the host's documented behavior over guessing internals
- Prefer the manifest plugin ID as the config key under `profiles.<profile>.plugins`
- Prefer alias-based reads when possible
- Prefer plan mode before apply
- Do not invent plugin input schemas when a companion plugin skill or plugin source of truth is available
- Do not add plugin config or plugin refs to host config unless the current workflow actually needs them
- Do not override plugin template paths or block names unless there is a concrete reason to diverge from plugin defaults
- Do not assume plugins are built into the host; verify with `docops plugins`
- Do not assume providers beyond the built-in `azure_devops_wiki`; verify with `docops providers`
- If the Azure DevOps PAT env var is missing, stop and ask the user to provide or export it
- If the workflow uses local assets, ensure the plugin config allows the asset roots or intentionally disables that protection
- Do not start post-run verification reads before `docops run --apply` has fully finished

## Companion skill boundary

If the plugin has its own skill, this host skill should not try to replace it.

Use the plugin skill for:

- building plugin-specific `input.yaml`
- deciding which command variant the plugin needs
- choosing plugin-specific defaults
- understanding plugin-managed sections or assets

Use `docops-host` for:

- editing or validating `config.yaml`
- configuring providers and profiles
- reading current page content
- executing `docops run`
- reviewing `ChangeSet`, diff, and `ApplyResult`
- post-run verification

## Coordination with plugin skills

When the user asks for a plugin-driven documentation update:

1. Use this skill to inspect the current runtime configuration and current page content
2. Load the relevant companion plugin skill, if one exists, to build the correct input YAML
3. Return to this skill to execute:
   - `docops run ...` in plan mode
   - inspect output
   - optionally `docops run ... --apply`
4. Use this skill to verify the resulting page state after apply

## Example natural-language intents this skill should handle

- "Configura DocOps para Azure DevOps Wiki con este organization, project y wiki"
- "Muéstrame qué plugins y providers tengo instalados"
- "Lee el contenido actual de la página `sample_dp`"
- "Ejecuta el plugin `nequi.datamind` con este input yaml"
- "Crea o actualiza mi `config.yaml` para que use el provider de Azure DevOps"
- "Dado que ya existe una página, lee su contenido actual y luego corre DocOps con el input que produzca la skill del plugin"

## Validation loop

1. Inspect providers and plugins first.
2. Validate the config path and input path exist.
3. Prefer `docops run` without `--apply`.
4. Review the `ChangeSet` and diff before persisting.
5. If apply was requested, inspect `ApplyResult` before declaring success.
6. When the run updates or creates a page, verify the resulting content with `docops docs get`.

## Bundled files

- [CLI reference](references/cli.md)
- [Configuration reference](references/configuration.md)
- [Azure DevOps provider reference](references/azure-devops-provider.md)
- [Host workflows](references/workflows.md)
- [Gotchas](references/gotchas.md)
- [Azure DevOps config example](assets/config.azure-devops.example.yaml)
- [Activation eval queries](assets/eval-queries.json)

## Design note

This skill intentionally does not bundle wrapper scripts in `scripts/`.

Reason:

- the `docops` CLI is already the stable execution interface
- wrapper scripts would duplicate host behavior and become a second contract to maintain
- the highest-value guidance here is workflow, config structure, command selection, and plugin-skill handoff
