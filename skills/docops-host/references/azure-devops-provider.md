# Azure DevOps Provider Reference

This file documents the built-in provider shipped by the host.

## Provider type

Use this `type` value in config:

```text
azure_devops_wiki
```

## Typical config

```yaml
providers:
  azdo:
    type: azure_devops_wiki
    organization: GrupoBancolombia
    project: Nequi
    wiki: Nequi.wiki
    pat_token_env: AZDO_PAT
    api_version: "7.1"
    timeout_seconds: 30
```

## Required settings

- `organization`
- `project`
- `wiki`

## Common optional settings

- `pat_token_env`
- `api_version`
- `timeout_seconds`

## Authentication

- The provider uses a Personal Access Token from an environment variable
- Default variable: `AZDO_PAT`
- If that variable is missing, provider validation fails before planning starts

## Supported capabilities

The built-in provider supports:

- reading documents
- checking if a page exists
- creating documents
- updating documents
- creating child documents
- building page links
- uploading assets
- resolving path-based refs

## Ref model

This provider supports path refs only.

Use:

```yaml
kind: path
locator:
  path: /Engineering/Platform/Runbook
```

Do not assume ID-based execution support.

## Reading the current content of a page

Preferred by alias:

```bash
docops docs get -c config.yaml -p test --alias sample_dp
```

Ad hoc by path:

```bash
docops docs get -c config.yaml -p test --path "/Engineering/Platform/Runbook"
```

## Asset behavior

Current asset behavior in Azure DevOps Wiki:

- uploaded assets are stored under `/.attachments/`
- attachment names get a short content hash suffix
- document content uses embeddable references such as `/.attachments/file--abcd1234.png`

If a plugin run uses local assets, the plugin config may also need `asset_policy.allowed_asset_roots`.

## Practical example from the sample workspace

The sample at:

```text
/home/sgg10/companies/pragma/clients-accounts/nequi/samples/azure-devops-wiki-api
```

uses:

- provider key: `azdo`
- profile: `test`
- PAT env var: `AZDO_PAT`

An agent can read the current tribe page with:

```bash
docops docs get -c config.yaml -p test --alias sample_tribe --output markdown
```
