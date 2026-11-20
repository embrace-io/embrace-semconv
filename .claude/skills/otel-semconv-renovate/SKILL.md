---
name: otel-semconv-renovate
description: Set up Renovate to bump a weaver-based OpenTelemetry semantic conventions project's pins - the weaver CLI and its setup-weaver action together, the shared policy pack's commit, OPA, the core registry dependency in the manifests, a codegen project's source registry release, and the pinned GitHub Actions - on a weekly schedule, with the Renovate version pinned and the config checked by Renovate itself. Builds on the otel-semconv-base skill and reads the pins the other otel-semconv skills add. Use when a semconv project should get its pins bumped automatically, or to merge these rules into a repo's existing Renovate config.
---

# Renovate for a semantic conventions project

This skill adds a Renovate config that bumps every pin the otel-semconv skills put in a project, and
pins the Renovate version used to check it. Read this skill's `reference/part.md` before changing
anything, and use the terms in the base skill's `reference/glossary.md`.

## 1. Gather facts first

1. **The project**: which otel-semconv parts it has (the base at least), and so which pins:
   `versions.env`'s, the manifests', a codegen `SOURCE_REGISTRY`, a build tool's own weaver pin.
2. **Renovate in the repo**: an existing config (`renovate.json`, `renovate.json5`,
   `.renovaterc*`, `.github/renovate.json*`), the hosted app or a self-hosted workflow, a config
   validator workflow, and whether the repo bumps the core registry some other way.
3. **The Renovate version** (`reference/part.md`, "The Renovate version").

## 2. Add the part

1. With no config yet, copy `assets/renovate/` (`.github/` at the repo root); otherwise merge its
   `customManagers` and `packageRules` into the repo's (`reference/part.md`).
2. Append `assets/project/versions.env` to the project's `versions.env`, with the version from
   step 1.3.
3. Annotate the pins the other parts don't annotate themselves: a codegen project's
   `SOURCE_REGISTRY`, a build tool's weaver pin (`reference/part.md`).
4. With a validator workflow of the repo's own, make it validate the way `reference/part.md` says.

## 3. Verify

1. The config validates (`reference/part.md`, "Checking the config").
2. Renovate's extraction lists every `# renovate:` line in the project's files, under its file and
   `depName`.
3. Once the user has pushed, Renovate's Dependency Dashboard issue appears (with the hosted app,
   once the app is enabled for the repo) and lists the pins.

## 4. Hand over

Tell the user what was created or merged, which Verify items ran and their results, and what is
left for a human: enabling the Renovate app for the repo, if it isn't; reviewing and merging the
bump pull requests, which arrive on Monday mornings (UTC). A bump to the core registry can change
generated docs and golden files: its pull request then needs them regenerated.

## Rules

- Never pin Renovate's version to `@latest` or leave it unversioned in a validator.
- Keep a repo's own `extends`, `schedule` and `labels` when merging.
