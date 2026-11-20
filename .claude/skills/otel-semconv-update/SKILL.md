---
name: otel-semconv-update
description: Bring an existing weaver-based OpenTelemetry semantic conventions repo up to current practice, one practice at a time - weaver installed in CI with its setup-weaver action, the shared docs templates instead of templates of the repo's own, the shared policy pack and validations, definition/2 definition files instead of v1, a release workflow, Renovate for the pins, a published package instead of constants generated from the core registry alone - by taking an inventory, comparing it with the practices the other otel-semconv skills set up, and applying each with the skill that owns it while keeping what consumers rely on unchanged. Use to modernize or audit a semconv registry or codegen repo, or when a new practice should reach repos already set up.
---

# Updating a semantic conventions repo to current practice

This skill updates a repo that already works with semantic conventions through weaver (a registry,
docs, generated code) to the practices the other otel-semconv skills set up today. It owns no
files of its own: each practice is applied by the skill that owns it, and this skill decides what
to change, in what order, and makes sure nothing consumers rely on moves. Use the terms in the
base skill's `reference/glossary.md`.

| Reference | Read it for |
|---|---|
| `reference/inventory.md` | what to read in the repo before changing anything |
| `reference/practices.md` | each current practice: how to tell a repo lacks it, which skill applies it |
| `reference/migrations.md` | moves no other skill covers: v1 to `definition/2`, renamed targets and jobs |

## 1. Take the inventory

Follow `reference/inventory.md`: the registry and its definition files, the tooling and CI,
branch protection, what consumers rely on, the tags. Then run the repo's own validations and tests
the way it runs them, and save what they produce (packaged artifacts, generated docs and code), so
there is a "before" to compare with.

## 2. Compare with current practice

Go through `reference/practices.md`, and for each practice note whether the repo has it, lacks
it, or has a version the practice supersedes. Practices that don't apply (docs for a codegen-only
repo, releases for an unpublished registry) are skipped, and say so. A practice whose skill isn't
installed alongside this one can't be applied here: report the gap and the skill it needs.

## 3. Propose the changes, and let the user choose

Present the gaps as a list of changes, one per practice, in the order `reference/practices.md`
gives (the base first, the `definition/2` migration before anything that regenerates output),
each with what it changes, what it costs (output that changes on purpose, a check name branch
protection must learn), and the skill that applies it. Ask which to make; don't assume all. Each
change is its own commit, or its own pull request when the repo limits pull request size.

## 4. Apply each change

For each chosen change, in order, follow the owning skill's steps for an update (its gather, add,
fill in and verify steps), with these rules on top:

- **Nothing consumers rely on changes as a side effect**: the `schema_url` name, published tags,
  keys, signal names, group IDs, generated code paths and names, and any action or workflow other
  repos use (its inputs and description stay).
- **Compare before and after.** Regenerate and compare with the inventory's copies: packaged
  artifacts identical unless the change is meant to change them; generated code identical; docs
  identical, except when the change replaces the docs templates (expected, and said so).
- **Keep the old validations passing** as you go, or account for each one that a new one replaces.
- **Delete what a change supersedes** in the same change (an old workflow, a script, a build task
  that generated committed code, the repo's own docs templates), or say in the hand over why it
  couldn't be.
- **Check names**: when a change renames a required CI check, update branch protection in the same
  change, or ask the user to (`reference/migrations.md`).

## 5. Verify and hand over

Run each owning skill's Verify items for what it changed, and this skill's before-and-after
comparisons. Then tell the user, per change: what moved or was renamed, what output changed and
why, which checks ran, and what needs a human (branch protection, enabling the Renovate app, the
next release, known violations and their migration).

## Rules

- Never rename a key, signal name or group ID that consumers use, to get a validation to pass or
  to follow a convention: list legacy names as known violations (the registry skill) instead.
- Keep the repo's pins unless the user agrees to bump them.
- Keep what the repo has beyond these practices: other workflows (security scans, link checks, a
  changelog check), extra jobs, targets and actions, a changelog process, hand-written docs pages.
  A change touches only what its practice owns, and the repo's docs (CONTRIBUTING, RELEASING)
  keep describing what stays.
- One practice per change: don't fold an unrelated cleanup into a practice's change.
