# Migrations

The moves no other skill covers: definition files from v1 to `definition/2`, and what earlier
setups called the targets, jobs and files the current practices have.

## v1 to `definition/2`

Weaver (0.28.0) has no converter: migrate by hand, file by file. v1 and v2 files can coexist in one
registry (the core registry itself mixes them), and v2 files can `ref` attributes defined in v1
files, so a partial migration is a valid state. After each file, run the repo's validation
(`make validate-registry` once the registry skill's part is in).

| v1 | `definition/2` |
|---|---|
| no `file_format`, one top-level `groups:` list typed by `type:` | `file_format: definition/2`, then `attributes`, `attribute_groups`, `events`, `metrics`, `spans`, `entities`, `imports` and the `*_refinements` lists |
| `type: attribute_group` with inline attribute `id:`s | the attributes under top-level `attributes:` keyed by `key:`; a public `attribute_groups` entry that `ref`s them, if they are exported |
| attribute `id:` | `key:` (same type/brief/examples fields; `stability` and `brief` required) |
| attribute `ref:` with overrides | `- ref: <key>` under a group or signal; only `brief`, `note`, `examples` and `annotations` can be refined. **`stability` and `deprecated` can't be set on a reference** (weaver 0.26.0+): they come from the definition |
| `type: span` / `event` / `metric` groups | `spans:` (`type` + `kind`) / `events:` (`name`) / `metrics:` (`name`, `instrument`, `unit`), each with its own `requirement_level` (weaver warns without one, and will require it) |
| `type: resource` groups | `entities:` (`type`, `identity`) |
| `extends:` | a `*_refinements` entry that `ref`s the base signal, or an `attribute_groups` bundle included with `ref_group` |
| (none) | `visibility: public` or `internal` on attribute groups; only public groups reach templates and consumers |
| `deprecated: { reason: renamed, renamed_to: <dependency attribute> }` | the same, plus an import of a group holding the replacement, or the shared pack rejects it (the registry skill's `validations.md`) |
| manifest `name:` fields (top-level, and on each dependency) | dropped: weaver ignores them, `schema_url` is the identity |
| a top-level `imports:` block | the same block, unchanged |

Enum `members` keep their shape. Group IDs that consumers import must survive the migration
unchanged: they are public API. Signal groups' IDs (`event.app.start`) have no counterpart in
`definition/2`, whose signals are identified by `name` or `type` alone: keep those unchanged, and
tell the user the IDs are gone.

Then run the templates with `--v2` (every make target does, and so must any build tool that runs
weaver). Templates written for v1's resolved shape need rework (`attribute.name` becomes
`attribute.key`, and v1-era jq helpers over `groups` are replaced by filters over `.registry.*`):
the codegen skill's `templates.md` says what v2 exposes. To see the context itself, render a
scratch target whose `weaver.yaml` has one template (`pattern: context.json.j2`, `filter: .`,
`application_mode: single`, `file_name: context.json`) holding `{{ ctx | tojson(true) }}`, from
the project directory so the project's `.weaver.toml` applies. Prove the rework by comparing the
generated output before and after the migration: it should be byte-identical.

An existing registry keeps its version, whatever its form: the `schema_url` is its identity. Add
the manifest's `stability` field if it lacks one (`development` unless its conventions are
stable).

## Renames from earlier setups

| Before | Now |
|---|---|
| `make check-policies` | `make validate-registry` (runs `validate-dependencies` first) |
| `check-weaver`, `check-opa` | `require-weaver`, `require-opa` (and `require-jq`) |
| awk schema_url/registry_path guard, grep for weaver's "Selected version" warning | `validate-dependencies` (reads the resolved tree) |
| grep for "matched nothing" | `RUN_WEAVER` fails on unmatched imports (JSON diagnostics) |
| `opa test` alone | plus the 100% coverage gate |
| scripts under `scripts/` that run weaver | make targets in the Makefile's sections (`scripts/install-weaver.sh` stays: `make install-weaver` runs it) |
| a local `setup-weaver` action | weaver's own setup-weaver action, or `make install-weaver` (the base skill) |
| docs templates under `templates/registry/markdown/` | the shared docs templates (the docs skill) |
| workflow `check.yaml` ("Check" / "Repo Check") | `ci-validation.yaml` ("CI validation") |
| jobs `check`, `docs-drift`, `templates`, `policies` | `validate-registry`, `validate-docs`, `test-templates`, `test-policies`, plus `test-validations` |
| `templates_test/golden/*` | `templates_test/golden/<target>/*` (one directory per template target) |
| a separate `-dev` release workflow using `--prerelease`, refusing versions without `-dev` | `release.yml` (prerelease exactly when the version has a pre-release suffix) plus `VERSION_SUFFIX := -dev`, which keeps the refusal |

## Required check names

Branch protection sees a job's `name:`. If the repo's aggregate job had another name, adopting the
base's changes the required check, if it is one: set `CI_GATE_JOB` to keep the old name when it is
a valid job ID (no spaces; "Run All Checks" isn't), or update the protection rule in the same
change, or ask the user to. If the repo already has a job named `required-status-check` in another
workflow, give this one its own `CI_GATE_JOB`. If the repo's protection requires other job names,
update the rule in the same change or ask the user to.

## Size

An update touches many files. If the repo limits pull request size, split it by practice: the
`definition/2` migration first (it must keep the generated output identical), then the tooling
and CI. When the migration alone is too big, port the templates (and a build tool's `--v2`) first:
`--v2` resolves `definition/1` files into the same v2 shape, so ported templates render the
unchanged files with identical output, and the definition files move in later changes. Check that
with the same before-and-after comparison.
