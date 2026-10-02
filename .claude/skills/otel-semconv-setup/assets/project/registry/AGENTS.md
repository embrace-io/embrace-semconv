# @@PROJECT_NAME@@ — agent guide

## What this repo is

@@REGISTRY_DESCRIPTION@@

It is a **federated** [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
registry (OTEP 4815, weaver `definition/2`) that depends on the core registry.

<!-- skeleton: fill in: the namespaces it owns (or, defining nothing yet, the ones it is meant
for), and who consumes it -->

This repo generates **markdown docs for itself** (under `docs/`). It does **not** generate
language-specific code: each consumer runs its own weaver generation referencing this registry.

## Layout

The Makefile is split into sections, one per part of the tooling; each section's project settings
live at its top.

```
model/
  manifest.yaml        # registry identity + version (schema_url), dependencies
templates/registry/markdown/   # doc-generation templates
templates_test/        # fixture registry + golden output for the template regression test
<!-- skeleton: only with the attributes collection -->
policies/              # local weaver policies (public attribute groups)
policies_test/         # OPA unit tests for policies/
<!-- skeleton: end -->
validations_test/      # invalid registries validation must fail on: <make target>/<case>/
docs/                  # GENERATED markdown — do not hand-edit; regenerate
Makefile               # validation, docs and tests (`make help`); CI runs its targets
versions.env           # pinned tool and shared policy pack versions
.weaver.toml           # deliberately empty: stops weaver picking up one from a parent directory
.github/               # workflows/ and actions/ (setup-weaver, assert-no-drift, …)
```

## Dependencies

- **Identity is `schema_url`.** Weaver splits it at the last `/` into the registry's name and
  version; there is no `name:` field. Every dependency is `schema_url` + `registry_path`, and the
  two must change together — weaver never fails when they disagree (at most it warns), so
  `make validate-dependencies` (run by `make validate-registry`) fails unless each `schema_url`
  matches the manifest of the registry its `registry_path` fetches.
- Weaver resolves **one** version per registry for the whole dependency graph (the highest), and
  warns only when it drops a version the root requested. `make validate-dependencies` fails
  whenever the graph requests a registry at more than one version, so keep the core registry
  pinned at the version every other dependency depends on, and the templates fixture's at the
  same version.
- A registry sees only what its **direct** dependencies define, so the core registry stays a direct
  dependency even when another dependency depends on it.

## Mental model: how federated weaver generation works

`definition/2` separates definitions from what references them:

<!-- skeleton: only with the attributes collection -->
- **`attributes:`** — a flat pool of attribute *definitions*, each keyed by `key` (the on-the-wire
  name) with `type`/`brief`/`examples`/`stability`. A definition on its own generates nothing.
<!-- skeleton: end -->
<!-- skeleton: only with the attribute-groups collection -->
- **`attribute_groups:`** — bundles with an `id` that reference attributes via `- ref: <key>`. A
  group does not contain definitions; it points at them. Only `visibility: public` groups reach
  templates and consumers: they are what the registry exports.
<!-- skeleton: end -->
<!-- skeleton: only with a signal collection (events, metrics, spans, entities) -->
- **Signals** (<!-- skeleton: fill in: the chosen signal collections' keys, e.g. `events:` -->)
  reference attributes via `- ref: <key>`, and each sets its own `requirement_level`.
<!-- skeleton: end -->

The rules that govern this repo **and** every consumer:

- weaver **merges** every file under the registry directory plus all dependency registries into
  one registry, then resolves `ref`s. The source *filename* is organizational only.
- **The `ref` drives generation, not the definition.** A group or signal produces output for every
  attribute it refs — wherever that attribute is defined. A `ref` that resolves to nothing is a
  hard error; an import that matches nothing fails `make` too.
<!-- skeleton: only with the attributes collection -->
- An attribute that is defined but exported by no public group generates nothing for consumers,
  and the local public-attribute-groups policy makes that an error.
<!-- skeleton: end -->

## Extending it (add or change a convention)

<!-- skeleton: only with the attributes collection -->
- Add a `key`-ed definition under `attributes:` in a `definition/2` file under `model/` (give it
  `type`/`brief`/`examples`/`stability`), and `ref` it from a public `attribute_group`.
<!-- skeleton: end -->
<!-- skeleton: only with a signal collection (events, metrics, spans, entities) -->
- Add signals under their collection's key
  (<!-- skeleton: fill in: the chosen signal collections' keys, e.g. `events:` -->), referencing
  their attributes. A signal's own `requirement_level` is `recommended` or `opt_in`; each
  attribute reference's is `required`, `recommended`, `opt_in`, or
  `conditionally_required: <when>`.
<!-- skeleton: only with the spans collection -->
  A span also needs a `name` (`name: {note: …}`).
<!-- skeleton: end -->
<!-- skeleton: end -->
- New conventions are
  `stability: <!-- skeleton: fill in: new conventions' stability (SKILL.md step 1, item 3) -->`
  unless decided otherwise.
<!-- skeleton: only for stability "unstable" (the default) -->
- The names the registry defines (its keys, signal names or group IDs) are its public contract:
  until its first release without a pre-release suffix anything may change; after it, removing
  or renaming one is a breaking change, which `make validate-registry` rejects against the last
  release. Deprecate instead.
<!-- skeleton: end -->
<!-- skeleton: only for stability "stable" -->
- The names the registry defines (its keys, signal names or group IDs) are its public contract:
  removing or renaming one is a breaking change. Deprecate instead.
<!-- skeleton: only with a signal collection (events, metrics, spans, entities) -->
  A stable signal may reference a less stable attribute only at `opt_in` (the shared policy
  pack rejects it otherwise).
<!-- skeleton: end -->
<!-- skeleton: only when BASELINE is set -->
  `make validate-registry` rejects breaking changes against the baseline.
<!-- skeleton: end -->
<!-- skeleton: only when BASELINE is empty -->
  Nothing compares changes with an earlier version (`BASELINE` is empty): review for them.
<!-- skeleton: end -->
<!-- skeleton: end -->
<!-- skeleton: only for stability "-dev family" -->
- Conventions may change or disappear between versions: every version is a `-dev` prerelease,
  and no release is ever a baseline.
<!-- skeleton: end -->
- Renaming a `.yaml` *file* is always free. Run the make targets under
  [Before committing](#before-committing) and commit the regenerated `docs/` in the same change.

## Before committing

Weaver is pinned in `versions.env`; install it with `make install-weaver`, or ensure the pinned
version is on `PATH` (the Makefile warns on a mismatch). The make targets also need `jq`. Two
lines on every weaver run are expected: "Experimental! - Found config" (the empty `.weaver.toml`)
and a warning that `definition/2` is not yet stable.
<!-- skeleton: only with the attributes collection -->
OPA is pinned there too: `make install-opa`.
<!-- skeleton: end -->

- **`make validate-registry`** — validates the registry: the resolved dependency trees
  (`make validate-dependencies`), then the schema, then the shared policy pack. Must pass.
<!-- skeleton: only when BASELINE is set -->
  The shared pack's backwards-compatibility policies run against the baseline (`BASELINE` in the
  Makefile), once there is one.
<!-- skeleton: end -->
<!-- skeleton: only with the attributes collection -->
  It also runs the local policy: every attribute must be exported by a public group.
<!-- skeleton: end -->
<!-- skeleton: only when KNOWN_VIOLATIONS is set -->
  Violations listed in `KNOWN_VIOLATIONS` are accepted; any other still fails, and a listed one
  that no longer occurs must be removed from the list. Never add a new key to the list: new keys
  follow the rules.
<!-- skeleton: end -->
- **`make generate-all`** — regenerates `docs/`. Docs are committed, and CI fails when the
  committed docs don't match what this generates, so regenerate and commit them together.
  **Never hand-edit `docs/`.**
- **`make test`** — `make test-templates` (renders the fixture under `templates_test/` and diffs it
  against `templates_test/golden/`) and `make test-validations` (runs each validating make target
  against the invalid registries under `validations_test/<make target>/` and confirms it fails on
  each with the expected error). After an intended template change, refresh the golden files with
  `make update-golden` and review the diff.
<!-- skeleton: only with the attributes collection -->
  It also runs `make test-policies`: OPA unit tests, which must cover every line of rego.
<!-- skeleton: end -->
- **Adding a validation?** Add a case under `validations_test/<make target>/<case>/`: a registry
  that is invalid in the way the validation catches, plus an `expected-error.txt` holding text its
  error must contain. `test-validations` runs the target with the case as `MODEL`, `FIXTURE` and
  `REGISTRIES`.

CI runs the same validations and tests in the `@@CI_WORKFLOW_NAME@@` workflow
(`.github/workflows/ci-validation.yaml`), one job per validation or test. Most jobs are named
after the make target they run; `validate-docs` runs `make generate-docs` and fails if `docs/`
then differs from what's committed. Running the targets locally predicts CI.

<!-- skeleton: only with `release` -->
## Releasing

Bump the version segment of `schema_url` in `model/manifest.yaml` (not for the first release,
which uses the version the manifest already has), prepare a draft release for that version, then
run the `Release` workflow, which publishes the draft — see `RELEASING.md`.
Consumers pin exact tags, so **never move or reuse a tag**: fix a bad release with a new
version. Only the version segment ever moves: the rest of `schema_url` is the registry's identity,
and changing it makes a different registry, not a new version.
<!-- skeleton: end -->

## Terms

Use these consistently in docs, comments and commit messages:

- **registry**: the conventions weaver resolves from `model/`, identified by its `schema_url`
  (not "model" or "schema"). **Registry name**: the `schema_url` up to the version, without the
  scheme.
- **core registry**: the OpenTelemetry semantic conventions registry (never bare "core" or
  "upstream"). **Dependency**: any registry declared in the manifest.
<!-- skeleton: only with the attribute-groups collection -->
- **export**: what a public attribute group does for the attributes it references.
<!-- skeleton: end -->
- **validate**: what `validate-*` targets do (fail on an invalid registry or stale docs).
  **test**: what `test-*` targets do. **check**: only `weaver registry check`.
- **invalid registry** / **case**: a registry under `validations_test/` a validation must fail on.
  **fixture** / **golden files**: the templates' test input and expected output.
- **baseline**: the release (or pinned registry) `validate-registry` compares the registry with.
- **shared policy pack**: the pinned `opentelemetry-weaver-packages` policies.
<!-- skeleton: only when KNOWN_VIOLATIONS is set -->
  **Known violation**: a shared-pack violation the registry accepts.
<!-- skeleton: end -->
<!-- skeleton: only with the attributes collection -->
- **local policy**: a policy under `policies/`.
<!-- skeleton: end -->

## Pointers

<!-- skeleton: only with `release` -->
- `README.md` — what the registry is, and how to consume it.
<!-- skeleton: end -->
<!-- skeleton: only without `release` -->
- `README.md` — what the registry is, and who uses it.
<!-- skeleton: end -->
- `CONTRIBUTING.md` — contributor setup (weaver install, running the make targets).
<!-- skeleton: only with `release` -->
- `RELEASING.md` — the release and tagging process.
<!-- skeleton: end -->
