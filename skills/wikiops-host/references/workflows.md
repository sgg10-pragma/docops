# Host Workflows

This file gives concrete workflows an agent can follow.

## Workflow 1: Configure WikiOps from natural language

User intent example:

> "Configura WikiOps para Azure DevOps Wiki con organization GrupoBancolombia, project Nequi y wiki Nequi.wiki"

Agent workflow:

1. Inspect the current config file if it exists
2. Add or update `providers.azdo`
3. Add or update `profiles.<name>.provider`
4. Add refs only if the workflow needs them
5. If the workflow is plugin-driven, add profile-scoped plugin config only for that plugin
6. Prefer plugin defaults unless there is a specific reason to override plugin settings
6. Validate by using:
   - `wikiops providers`
   - `wikiops plugins`

## Workflow 2: Read the current content of an existing page

User intent example:

> "Lee el contenido actual de la página sample_dp"

Agent workflow:

1. Inspect the profile refs in `config.yaml`
2. If the alias exists, run:

```bash
wikiops docs get -c config.yaml -p test --alias sample_dp --output markdown
```

3. If the alias does not exist but the path is known, run:

```bash
wikiops docs get -c config.yaml -p test --path "/Known/Path" --output markdown
```

4. Use JSON output when the caller is another tool or agent step that needs structure

## Workflow 3: Execute a plugin with an input YAML

User intent example:

> "Ejecuta el plugin nequi.datamind con este input yaml"

Agent workflow:

1. Confirm the plugin is installed:

```bash
wikiops plugins
```

2. Confirm the provider exists:

```bash
wikiops providers
```

3. Always prepare the command with `--plugin <plugin_id>`
4. If the input YAML depends on plugin-specific schema, load the plugin skill first
   - If a companion plugin skill exists, prefer it over rebuilding the input shape from memory
   - If no plugin skill exists, derive the input only from the plugin repo, examples, or validated docs in the workspace
5. Run plan mode first:

```bash
wikiops run -c config.yaml -p test --plugin nequi.datamind -i datamind_commands_inputs/create_dp_input.yaml
```

6. Inspect:
   - `=== CHANGESET ===`
   - `=== DIFF ===`

7. Only if persistence is intended, run:

```bash
wikiops run -c config.yaml -p test --plugin nequi.datamind -i datamind_commands_inputs/create_dp_input.yaml --apply
```

8. Inspect `=== APPLY RESULT ===`
9. Only after the apply command finishes, verify the resulting page with `wikiops docs get`

## Workflow 4: Host skill + plugin skill handoff

This is the most important compound workflow.

User intent example:

> "Ya existiendo una página de documentación, lee el contenido actual, propone cambios según el repo, genera el input del plugin y luego ejecuta WikiOps"

Recommended sequence:

1. Use this host skill to read the current page with `wikiops docs get`
2. Analyze the current content and the requested source changes
3. Load the companion plugin skill for the target plugin
4. Ask the plugin skill to produce the correct input YAML shape
5. Return to this host skill
6. Run `wikiops run` in plan mode with that YAML
7. Review the `ChangeSet` and diff
8. Apply only if the user wants persistence
9. Wait until apply fully completes
10. Read the page again to verify the final state

Responsibility split:

- plugin skill: input schema, domain rules, templates, examples, managed blocks
- host skill: config, providers, page reads, command execution, plan/apply verification

## Workflow 5: Configure the built-in Azure provider plus a plugin profile

Pattern:

1. Create a provider entry under `providers`
2. Create one profile under `profiles`
3. Add reusable refs for pages that will be read or updated often
4. Add plugin config under `profiles.<profile>.plugins.<plugin_id>`
5. Keep provider configuration host-level and plugin rules plugin-level

## Sample workspace notes

In the sample workspace:

```text
/home/sgg10/companies/pragma/clients-accounts/nequi/samples/azure-devops-wiki-api
```

useful commands include:

```bash
wikiops providers
wikiops plugins
wikiops docs get -c config.yaml -p test --alias sample_tribe --output markdown
wikiops docs get -c config.yaml -p test --alias sample_dp --output json
wikiops run -c config.yaml -p test --plugin nequi.datamind -i datamind_commands_inputs/create_dp_input.yaml
```
