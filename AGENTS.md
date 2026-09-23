# embrace-semconv — agent guide

## What this repo is

The canonical, cross-platform [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
registry for Embrace's `emb.*` namespace. It is a **federated** registry (OTEP 4815, weaver
`definition/2`) that depends on the core OTel semantic conventions. It will also depend on the
[client-side semantic conventions](https://github.com/open-telemetry/semantic-conventions-client-side)
registry once that publishes a release.

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
  manifest.yaml        # registry identity + version (schema_url), dependencies (core OTel)
  emb/registry.yaml    # emb.* attribute definitions + the attribute_group that bundles them
templates/registry/markdown/   # doc-generation templates (this repo emits docs, not code)
policies/              # local weaver policy (public attribute groups)
docs/                  # GENERATED markdown — do not hand-edit; regenerate
Makefile               # validation, docs generation, packaging (`make help`); CI runs its targets
versions.env           # pinned weaver + shared policy pack versions
.github/               # workflows/ (check.yaml, release.yml) + actions/setup-weaver/ (weaver installer)
```

## Dependencies

- **Identity is `schema_url`.** Weaver splits it at the last `/` into the registry's name and
  version; there is no `name:` field. Every dependency is `schema_url` + `registry_path`, and the
  two must change together — weaver does not check they agree, so `make check-policies` does for
  any `registry_path` pinned to a release tag.
- **Core OTel** is pinned to a release tag in `model/manifest.yaml`.
- Weaver resolves **one** version per registry for the whole dependency graph, only warning when
  requests differ. `make check-policies` turns that warning into a failure, so when a dependency
  that itself depends on core is added (e.g. client-side), keep this repo's core pin in lockstep
  with it.
- A registry sees only what its **direct** dependencies define: core attributes would not be
  reachable through client-side, so core stays a direct dependency even once client-side is added.

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
  it refs — wherever that attribute is defined (here, a dependency, or core OTel). An attribute that
  is defined but ref'd by no group generates nothing. A `ref` that resolves to nothing is a hard
  error (a useful safety net).
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
conflicts and provenance) by `schema_url`, and does not check that they agree. See `README.md` for
the full consuming guide.

## Extending it (add or change an attribute)

1. Add a `key`-ed definition under `attributes:` in `model/emb/registry.yaml` (give it
   `type`/`brief`/`examples`/`stability`).
2. `ref` it from an `attribute_group` (e.g. `registry.embrace.emb`) — otherwise it generates nothing.
3. `key`s and group `id`s are the **on-the-wire contract** with the Embrace backend. Renaming them is
   a breaking change and requires backend agreement; renaming a `.yaml` *file* is free.
4. Run the validation workflow below and commit the regenerated `docs/` in the same change.

Events are not currently modeled (Embrace doesn't use OTel events internally yet). If needed, add
them as `events:` blocks that `ref` attributes, the same way groups do.

## Workflow — run before committing

Weaver is pinned in `versions.env`; install it with `make install-weaver`, or ensure the pinned
version is on `PATH` (the Makefile warns on a version mismatch).

- **`make check-policies`** — validates the schema, resolves the dependencies, and runs the
  shared + local policies. Must pass.
- **`make generate-all`** — regenerates `docs/`. Docs are committed and CI fails on drift, so
  regenerate and commit them together. **Never hand-edit `docs/`.**

These are exactly the jobs in `.github/workflows/check.yaml`, so running them locally predicts CI. Standard hygiene otherwise: commit only when asked, keep messages focused.

## Releasing

Bump the version segment of `schema_url` in `model/manifest.yaml`, then tag — see `RELEASING.md`.
Consumers pin exact tags and **tags are immutable**: fix a bad release with a new version, never a
re-tag. Only the version segment ever moves: the rest of `schema_url`
(`embrace.io/schemas/embrace`) is the registry's identity, and changing it makes a different
registry, not a new version.

## Pointers

- `README.md` — what the registry is + the full consuming/extending guide.
- `CONTRIBUTING.md` — contributor setup (weaver install, running checks).
- `RELEASING.md` — the release and tagging process.
