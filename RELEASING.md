# Releasing

A release is a `v<version>` tag plus a GitHub release carrying the OTEP 4815 publication artifacts
that `make package` produces: the publication manifest (`manifest.yaml`) and the resolved registry
(`resolved.yaml`).

The version is the last segment of the `schema_url` in [`model/manifest.yaml`](model/manifest.yaml),
e.g. `…/embrace/0.1.0` releases as tag `v0.1.0`. The release workflow and `make package` both read
it from there.

## When to release

Only when `model/` has changed since the last tag. The model is everything consumers get through
`…@<tag>[model]`; changes to the Makefile, templates, generated docs or CI don't need a release.

## How to release

1. Land the model changes on `main`.
2. In a follow-up PR, bump the version segment of `schema_url` in `model/manifest.yaml`.
3. Run the **Release** workflow from the Actions tab. It validates and packages the registry, tags
   the workflow's commit as `v<version>`, and publishes the release with both artifacts attached.
   It never bumps the version itself, and refuses to run if that tag already exists.

## Rules

- **Tags are immutable.** Never move or delete a pushed tag; consumers pin exact tags. Fix a bad
  release with a new version.
- **The registry's identity never changes.** Everything in `schema_url` before the version segment
  (`embrace.io/schemas/embrace`) is the registry's name; only the version moves. Weaver treats a
  new name as a different registry, not a new version, so consumers would end up with two
  unrelated registries.
- **Release only with dependencies pinned to tags.** A dependency tracking a branch makes the same
  tag resolve differently as that branch moves.
