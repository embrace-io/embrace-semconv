# embrace-semconv — agent guide

## What this repo is

The canonical, cross-platform [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
registry for Embrace's `emb.*` namespace. It is a **federated** registry (OTEP 4815, weaver
`definition/2`) that depends on the core registry (the OpenTelemetry semantic conventions). It
will also depend on the
[client-side semantic conventions](https://github.com/open-telemetry/semantic-conventions-client-side)
registry once that publishes a release. It offers the same make targets as the other OpenTelemetry
semantic-convention registries.

It is the single source of truth for Embrace attribute **definitions**. Embrace SDKs (Android first,
others to follow) consume it as a dependency and generate their own language-specific constants from
it — so a `emb.*` attribute is defined once here instead of being redefined in each SDK.

This repo generates **markdown docs for itself** (under `docs/`). It does **not** generate SDK code —
each consuming SDK runs its own weaver generation referencing this registry.

Intent (high level, kept deliberately vague — sequencing/roadmap lives outside this repo): grow this
into the shared home for all `emb.*` conventions across every Embrace SDK. It currently holds a
starter set of attributes and will expand over time.

## Layout

```
model/
  manifest.yaml        # registry identity + version (schema_url), dependencies (the core registry)
  emb/registry.yaml    # emb.* attribute definitions + the attribute_group that bundles them
templates/registry/markdown/   # doc-generation templates (this repo emits docs, not code)
templates_test/        # fixture registry + golden output for the template regression test
policies/              # local weaver policy (public attribute groups)
policies_test/         # OPA unit tests for policies/
validations_test/      # invalid registries validation must fail on: <make target>/<case>/
docs/                  # GENERATED markdown — do not hand-edit; regenerate
Makefile               # validation, docs, tests, packaging (`make help`); CI runs its targets
versions.env           # pinned weaver + OPA + shared policy pack versions
.weaver.toml           # deliberately empty: stops weaver picking up one from a parent directory
.github/               # workflows/ (ci-validation.yaml, release.yml),
                       # actions/ (setup-weaver, setup-opa, assert-no-drift)
```

## Dependencies

- **Identity is `schema_url`.** Weaver splits it at the last `/` into the registry's name and
  version; there is no `name:` field. Every dependency is `schema_url` + `registry_path`, and the
  two must change together — weaver never fails when they disagree (at most it warns), so
  `make validate-dependencies` (run by `make validate-registry`) fails unless each `schema_url`
  matches the manifest of the registry its `registry_path` fetches.
- **The core registry** is pinned to a release tag in `model/manifest.yaml`.
- Weaver resolves **one** version per registry for the whole dependency graph (the highest), and
  warns only when it drops a version the root requested. `make validate-dependencies` fails
  whenever the graph requests a registry at more than one version, so when a dependency that itself
  depends on the core registry is added (e.g. client-side), keep this repo's core registry pin in
  lockstep with it.
- A registry sees only what its **direct** dependencies define: the core registry's attributes
  would not be reachable through client-side, so the core registry stays a direct dependency even
  once client-side is added.

## Mental model: how federated weaver generation works

`definition/2` separates two things:

- **`attributes:`** — a flat pool of attribute *definitions*, each keyed by `key` (the on-the-wire
  name) with `type`/`brief`/`examples`/`stability`. A definition on its own generates nothing.
- **`attribute_groups:`** — bundles with an `id` that reference attributes via `- ref: <key>`. A
  group does not contain definitions; it points at them.

The rules that govern this repo **and** every consumer:

- weaver **merges** every file under the registry dir plus all dependency registries into one model,
  then resolves `ref`s. The source *filename* is organizational only.
- **The `ref` drives generation, not the definition.** A group produces output for every attribute
  it refs — wherever that attribute is defined (here, a dependency, or the core registry). An
  attribute that is defined but ref'd by no group generates nothing. A `ref` that resolves to
  nothing is a hard error (a useful safety net).
- Consumers declare this repo as a dependency and `ref` its attributes from their *own* groups, so
  the definition here becomes a constant in the consumer's generated class. Definitions live once
  (here); each SDK generates its own constants.

## Using it (as a consumer, e.g. an SDK)

Declare it in the consumer's `manifest.yaml`, pinned by tag, then `ref` the attributes you need from
your own groups:

```yaml
dependencies:
  - schema_url: https://embrace.io/schemas/embrace/<version>
    registry_path: https://github.com/embrace-io/embrace-semconv@v<version>[model]
```

Pin an exact tag, never a branch. `schema_url` and `registry_path` name the same release and must
move together: weaver fetches from `registry_path` but identifies the dependency (for version
conflicts and provenance) by `schema_url`, and never fails when they disagree. See `README.md` for
the full consuming guide.

## Extending it (add or change an attribute)

1. Add a `key`-ed definition under `attributes:` in `model/emb/registry.yaml` (give it
   `type`/`brief`/`examples`/`stability`). Use `stability: stable`: this registry only holds
   conventions the Embrace backend already consumes, so they are stable from the start.
2. `ref` it from an `attribute_group` (e.g. `registry.embrace.emb`) — otherwise it generates nothing.
3. `key`s and group `id`s are the **on-the-wire contract** with the Embrace backend. Renaming them is
   a breaking change and requires backend agreement; renaming a `.yaml` *file* is free.
4. Run the make targets under [Before committing](#before-committing) and commit the regenerated
   `docs/` in the same change.

Events are not currently modeled (Embrace doesn't use OTel events internally yet). If needed, add
them as `events:` blocks that `ref` attributes, the same way groups do.

## Before committing

Weaver and OPA are pinned in `versions.env`; install them with `make install-weaver` /
`make install-opa`, or ensure the pinned versions are on `PATH` (the Makefile warns on a mismatch).
The tests also need `jq`.

- **`make validate-registry`** — validates the registry: the resolved dependency trees
  (`make validate-dependencies`), then the schema, then the shared + local policies, including
  the shared pack's backwards-compatibility policies against the latest release tag (`BASELINE`
  overrides it; empty skips it). Must pass.
- **`make generate-all`** — regenerates `docs/`. Docs are committed, and CI fails when the
  committed docs don't match what this generates, so regenerate and commit them together.
  **Never hand-edit `docs/`.**
- **`make test`** — `make test-templates` (renders the fixture under `templates_test/` and diffs it
  against `templates_test/golden/`), `make test-policies` (OPA unit tests, which must cover every
  line of rego) and `make test-validations` (runs each validating make target against the invalid
  registries under `validations_test/<make target>/` and confirms it fails on each with the
  expected error). After an intended template change, refresh the golden files with
  `make update-golden` and review the diff.
- **Adding a validation?** Add a case under `validations_test/<make target>/<case>/`: a registry
  that is invalid in the way the validation catches, plus an `expected-error.txt` holding text its
  error must contain. `test-validations` runs the target with the case as `MODEL`, `FIXTURE` and
  `REGISTRIES`. A case that needs a baseline names a registry under `validations_test/registries/`
  in its `baseline.txt`.

CI runs the same targets in the `CI validation` workflow (`.github/workflows/ci-validation.yaml`),
one job per target and named after it. Its `validate-docs` job runs `make generate-all` and fails
if `docs/` then differs from what's committed. Running the targets locally predicts CI.
Standard hygiene otherwise: commit only when asked, keep messages focused.

## Releasing

Bump the version segment of `schema_url` in `model/manifest.yaml`, prepare a draft release for that
version, then run the `Release` workflow, which publishes the draft — see `RELEASING.md`.
Consumers pin exact tags and **tags are immutable**: fix a bad release with a new version, never a
re-tag. Only the version segment ever moves: the rest of `schema_url`
(`embrace.io/schemas/embrace`) is the registry's identity, and changing it makes a different
registry, not a new version.

## Terms

Use these consistently in docs, comments and commit messages:

- **registry**: the conventions weaver resolves from `model/`, identified by its `schema_url`
  (not "model" or "schema"). **Registry name**: the `schema_url` up to the version.
- **core registry**: the OpenTelemetry semantic conventions registry (never bare "core" or
  "upstream"). **Dependency**: any registry declared in the manifest.
- **validate**: what `validate-*` targets do (fail on an invalid registry or stale docs).
  **test**: what `test-*` targets do. **check**: only `weaver registry check`.
- **invalid registry** / **case**: a registry under `validations_test/` a validation must fail on.
  **fixture** / **golden files**: the templates' test input and expected output.
- **baseline**: the release `validate-registry` compares the registry with.
- **shared policy pack** (the pinned `opentelemetry-weaver-packages` policies) vs **local policy**
  (under `policies/`).

## Pointers

- `README.md` — what the registry is + the full consuming/extending guide.
- `CONTRIBUTING.md` — contributor setup (weaver install, running the make targets).
- `RELEASING.md` — the release and tagging process.
