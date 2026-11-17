---
name: otel-semconv-release
description: Publish an OpenTelemetry semantic conventions registry as GitHub releases with its OTEP 4815 publication artifacts (publication manifest and resolved registry from weaver registry package), through a workflow that releases only a draft a maintainer prepared, from the default branch, after validating the registry; with print-version and package make targets and a RELEASING.md for the process. Builds on the otel-semconv-registry skill. Use when a registry is to be published, to add or fix a registry's release workflow, or to make a first release.
---

# Releases for a semantic conventions registry

This skill adds releases to a project with a registry (the otel-semconv-registry skill, on the
otel-semconv-base skill): the Makefile's `print-version` and `package`, the Release workflow, and
RELEASING.md. Read the base skill's `reference/layout.md` ("Adding a part") and this skill's
`reference/part.md` before changing anything, and use the terms in the base skill's
`reference/glossary.md`.

## 1. Gather facts first

1. **The registry**: the project must have the registry skill's part; set it up first with that
   skill if not, as part of this change. Its stability (unstable, stable, or a `-dev` family, the
   registry skill's `reference/versioning.md`) decides `VERSION_SUFFIX` and the RELEASING.md
   blocks.
2. **The repo's tags**: `git ls-remote --tags <repo-url> 'v*'`. If the repo tags `v*` for
   anything else (an SDK's releases, another registry), stop and ask the user how to tell the
   registry's releases apart (`reference/part.md`).
3. **The canonical repo**: whether `origin` is it (not a fork, nor a contributor's fork). If not,
   set the registry part's `REPO_URL` to it: the release URLs come from it.
4. **What's there already**: a release workflow or a separate dev release workflow (replaced by
   this one, and deleted in the same change), and the repo's own release docs.

## 2. Add the part

1. Copy `assets/release/` (`.github/` at the repo root), add the Makefile section the way the
   base's "Adding a part" says, and replace the tokens (`reference/part.md`). Set
   `VERSION_SUFFIX := -dev` for a `-dev` family.
2. Write RELEASING.md from `assets/skeletons/` (the base skill's `reference/layout.md`,
   "Skeletons"). Where the repo already has release docs, merge instead.

## 3. Verify

Don't call the work done until every item below that applies has passed, and say which ones you
ran. Run them from the project directory.

1. The base and registry skills' Verify items, for the parts they set up.
2. `make print-version` prints the manifest's version, and `make package` succeeds; the packaged
   manifest's `resolved_registry_uri` is `<REPO_URL>/releases/download/v<version>/resolved.yaml`.
3. No `<!-- skeleton` is left in RELEASING.md.
4. In an update, compare `make package`'s output with what the old tooling packaged (built before
   the change): no difference means the update needs no release.
5. Once the user has pushed: the first release is theirs to make (`RELEASING.md`).

## 4. Hand over

Tell the user what was created or changed, which Verify items ran and their results, and what is
left for a human: preparing the draft and running the Release workflow for the first release, and
for a published registry, asking consumers to pin releases, never branches.

## Rules

The base skill's Rules apply to this part's files too. And:

- Releases and tags are immutable: fix a bad release with a newer version, never a re-tag.
- The workflow publishes only a draft a person prepared: don't make it create releases on its own.
