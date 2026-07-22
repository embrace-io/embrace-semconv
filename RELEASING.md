# Releasing

Releases are cut from `main` as GitHub releases with the OTEP 4815 publication
artifacts attached: the publication manifest (`manifest.yaml`, `file_format:
manifest/2.0`) and the resolved registry (`resolved.yaml`, `file_format:
resolved/2.0`), both produced by `scripts/package.sh`.

The single source of truth for the release version is the version segment of
the `schema_url` in [`model/manifest.yaml`](model/manifest.yaml), e.g.
`…/embrace/0.1.0` releases as tag `v0.1.0`. Everything else
(the workflow, `scripts/package.sh`, the resolved-schema URI baked into the
artifacts) derives from it by parsing.

## When to release

Cut a release only when `model/` has changed since the last tag — the model is
the entire surface consumers see through `…@<tag>[model]`. Changes to scripts,
templates, generated docs, or CI are invisible to consumers so do not require
a new version when they are updated.

## How to release

Releasing is deliberately a manual two-step process: the workflow never bumps the
version itself and instead creates a new tag based on whatever version
`model/manifest.yaml` declares. Running the release workflow will fail if
the version in the file was not changed since the last release.

1. Land the model changes on `main` and regenerate markdown files.
2. In a follow-up PR, bump the version segment of `schema_url` in
   `model/manifest.yaml` (e.g. `1.1.0` → `1.2.0`).
3. Run the **Release** workflow from the Actions tab
   (`workflow_dispatch`). It will:
   - derive the tag from the manifest
   - validate the registry (`scripts/check.sh`), including the shared policy
     pack
   - package the publication artifacts (`scripts/package.sh`);
   - create the `v<version>` tag at the workflow's commit and publish it as a
     GitHub **release** with `manifest.yaml` and `resolved.yaml` attached
     and auto-generated notes.

## Rules

- **Tags are immutable.** Never move or delete a pushed tag; consumers pin
  exact tags. A bad release is fixed by a new version, not a re-tag.
- Consumers pin
  `registry_path: https://github.com/embrace-io/embrace-semconv@v<version>[model]`.
