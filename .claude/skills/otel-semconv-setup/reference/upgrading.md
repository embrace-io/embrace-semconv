# Updating an existing repo

An update applies any subset of: the standard layout and tooling, the validations, the upgrade
to `definition/2`, the release workflow, generated docs, and a new registry dependency. Ask which
the user wants; don't assume all.

## 1. Inventory first

Read the repo before changing anything:

- **The registry**: where the manifest is and what it's called. `manifest.yaml` with a
  `schema_url` is current; `registry_manifest.yaml` with `semconv_version` / `schema_base_url` is
  weaver's legacy form (weaver warns about it). Which definition files are v1 (top-level `groups:`,
  no `file_format`) and which are `file_format: definition/2`.
- **Tooling**: the Makefile or scripts, pinned tool versions and where (a build tool may pin
  weaver too, e.g. a Gradle version catalog), CI workflows and their job names, release
  workflows, dependency bots (Renovate, Dependabot) and what they bump, and any build-tool task
  that runs weaver.
- **Branch protection**: which check names are required. Classic protection:
  `gh api repos/<owner>/<repo>/branches/<branch>/protection`. Repos using rulesets return 404
  there; use `gh api repos/<owner>/<repo>/rules/branches/<branch>`. A 404 there too, or `[]`,
  means no protection or no access to see it: ask. A 403 "Upgrade to GitHub Pro or make this
  repository public" means a private repo on GitHub Free, which can't have protection. A check is
  named by the job's `name:`, not its ID, and renaming a required one breaks merging until the
  rule is updated. Note any `code_scanning` rule too, and the tools it names: the layout's
  workflows must pass them (`layout.md`, "Local actions"; SKILL.md step 5 item 13).
- **What consumers rely on**: published tags, the `schema_url` name, keys, signal names, group
  IDs, generated code paths and names, and any of the repo's actions or workflows that other
  repos reference (a `uses: <owner>/<repo>/.github/actions/...` in someone else's CI: search
  with `gh search code "<owner>/<repo>/.github/actions"`). None of these may change as a side
  effect of the update; an action's inputs and its description for other repos stay.
- **The tags**: which `v*` tags exist and whose they are (SKILL.md step 1), for `BASELINE`.

Then run the existing validations and tests the way the repo runs them (its make targets, its
build), so you know what passed before you touched anything. Code generated at build time isn't
committed: copy its output to scratch now, to compare with afterwards. With `release`, when the
repo already has `make package`, run it and copy `.build/package` to scratch too (SKILL.md step
5, item 12, compares it). Run weaver by hand only
from the repo's own project directory: weaver applies the first `.weaver.toml` walking up from
where it runs, so a run from anywhere else can pick up an unrelated one.

## 2. Adopt the layout's tooling

Copy the layout's files for the features the repo has ("Copying the layout" in `layout.md`).
Files the repo lacks are simply added. For files it already has:

- **Layout-owned files** (the actions, the invalid registries, the policy and its tests, the
  fixture, the Makefile's sections, the workflows' layout jobs) take the layout's content, with
  the exceptions SKILL.md's Rules list. Carry the repo's settings into the layout's settings and
  tokens (e.g. `MODEL := src/main/semconv` keeps a registry where it is), keep the repo's pins
  (`versions.env` values, pinned action SHAs) unless the user agrees to bump them, and keep the
  repo's own additions. The layout's invalid registries and policy tests use `example.*` names:
  adopting them replaces the repo's own copies' names, which is expected.
- **Superseded files**: delete the repo's workflows, scripts and build tasks the layout replaces,
  in the same change (a drift-check workflow, a dev release workflow, a build task that
  generated committed code). If deleting isn't possible from where you are, say so in the hand
  over: a superseded workflow left behind usually fails.
- **Prose files** (README.md, AGENTS.md, CONTRIBUTING.md, RELEASING.md) are merged: keep the
  repo's text and bring in what the layout's skeletons add.

Work through them one at a time, and keep the old validations and tests passing as you go. The
Makefile is the biggest merge: move the repo's settings into the layout's section settings, and
drop the repo's own versions of targets the layout provides.

Renames from pre-layout setups (e.g. a registry bootstrapped before this layout):

| Before | In the layout |
|---|---|
| `make check-policies` | `make validate-registry` (runs `validate-dependencies` first) |
| `check-weaver`, `check-opa` | `require-weaver`, `require-opa` (and `require-jq`) |
| awk schema_url/registry_path guard, grep for weaver's "Selected version" warning | `validate-dependencies` (reads the resolved tree) |
| grep for "matched nothing" | `RUN_WEAVER` fails on unmatched imports (JSON diagnostics) |
| `opa test` alone | plus the 100% coverage gate |
| scripts under `scripts/` | make targets in the Makefile's sections |
| workflow `check.yaml` ("Check" / "Repo Check") | `ci-validation.yaml` ("CI validation") |
| jobs `check`, `docs-drift`, `templates`, `policies` | `validate-registry`, `validate-docs`, `test-templates`, `test-policies`, plus `test-validations` |
| `templates_test/golden/*` | `templates_test/golden/<target>/*` (one directory per template target) |
| a separate `-dev` release workflow using `--prerelease`, refusing versions without `-dev` | `release.yml` (prerelease exactly when the version has a pre-release suffix) plus `VERSION_SUFFIX := -dev` in the Makefile's release section, which keeps the refusal |
| a Gradle/npm task that runs weaver | see `templates.md`, "Platform integration" |

**The aggregate CI job.** Branch protection sees the job's `name:`. If the repo's aggregate job
had another name, adopting the layout's changes the required check, if it is one: set
`CI_GATE_JOB` to keep the old name when it is a valid job ID (no spaces; "Run All Checks" isn't),
or update the protection rule in the same change, or ask the user to. If the repo already has a job named `required-status-check` in another workflow, give
this one its own `CI_GATE_JOB`. If the repo's protection requires other job names, update the rule
in the same change or ask the user to.

**Dependency bots.** Renovate: follow `layout.md`'s `renovate` section (merge into the repo's
existing config, skip what the repo already bumps another way); the layout's `versions.env` and
manifests already carry the `# renovate:` annotations. Make it bump each dependency's
`schema_url` and `registry_path` together, and the fixture's core registry with the registry's
(the invalid registries' pins don't need to follow). A repo's own bump workflow for the core
registry also bumps the fixture's manifest. A core registry bump can change the golden files and
the docs (they show the briefs of the core registry's attributes they reference, and the
fixture imports from the core registry), so its pull request can fail `test-templates` or
`validate-docs` until someone runs `make update-golden generate-all` on its branch, reviews the
diff and commits it: say so in the hand over. Dependabot can't bump these pins; keep it for
what it already does.

**Existing conventions the shared pack rejects.** A registry that predates the shared pack's
rules may fail its naming or stability policies on keys consumers already use. Never rename them
in the update: list them as known violations (`validations.md`), and tell the user about the
migration that clears them.

**Size.** An update touches many files. If the repo limits pull request size, split it: the
`definition/2` migration first (it must keep the generated output identical), then the tooling
and CI. When the migration alone is too big, port the templates (and a build tool's `--v2`)
first: `--v2` resolves `definition/1` files into the same v2 shape, so ported templates render
the unchanged files with identical output, and the definition files move in later changes. Check
that with the same before-and-after comparison.

## 3. Upgrade definitions to `definition/2`

Weaver (0.26.1) has no converter: migrate by hand, file by file. v1 and v2 files can coexist in
one registry (the core registry itself mixes them), and v2 files can `ref` attributes defined in v1
files, so a partial migration is a valid state. After each file, run `make validate-registry`.

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
| `deprecated: { reason: renamed, renamed_to: <dependency attribute> }` | the same, plus an import of a group holding the replacement, or the shared pack rejects it (`validations.md`) |
| manifest `name:` fields (top-level, and on each dependency) | dropped: weaver ignores them, `schema_url` is the identity |
| a top-level `imports:` block | the same block, unchanged |

Enum `members` keep their shape. Group IDs that consumers import must survive the migration
unchanged: they are public API. Signal groups' IDs (`event.app.start`) have no counterpart in
`definition/2`, whose signals are identified by `name` or `type` alone: keep those unchanged,
and tell the user the IDs are gone.

Then run the templates with `--v2` (the layout always does, and so must any build tool that runs
weaver). Templates written for v1's resolved shape need rework (`attribute.name` becomes
`attribute.key`, and v1-era jq helpers over `groups` are replaced by filters over
`.registry.*`): see `templates.md` for what v2 exposes, including where referenced dependency
attributes appear. To see the context itself, render a scratch target whose `weaver.yaml` has
one template (`pattern: context.json.j2`, `filter: .`, `application_mode: single`,
`file_name: context.json`) holding `{{ ctx | tojson(true) }}`, through the project's make
targets so weaver runs from the project directory, e.g.
`make generate-docs TEMPLATES=<scratch> DOCS_DIR=<scratch-out>` with the target directory named
`markdown` (or `make generate` with `CODEGEN_TARGET` and `GENERATED_DIR`). Prove the rework by
comparing the generated output before and after the migration: it should be byte-identical.

An existing registry keeps its version, whatever its form: the `schema_url` is its identity. In
any update, add the manifest's `stability` field if it lacks one (`development` unless its
conventions are stable).

## 4. Add the release workflow

Needs the `registry` and `release` features. Check the manifest's version is SemVer
(`make print-version`), that the existing tags follow `v<version>` and are all this registry's
releases (if the repo tags `v*` for anything else, ask the user before going on), and whether any
published version carries a pre-release suffix. For a `-dev` family (`versioning.md`), set
`VERSION_SUFFIX := -dev`. The first release made with the layout compares against the latest
existing `vX.Y.Z` tag, so run `make validate-registry` before making it: removals since that tag
will fail.

## 5. Add generated docs

Needs `docs`, with the collections the registry defines (SKILL.md step 1 says how to scan for
them). Run `make generate-docs`, review `docs/`, and commit it; from then on CI's `validate-docs`
job fails on stale docs. If the repo already had docs templates, compare them with the layout's:
keep the layout's filters (local definitions only), and bring over wording the project wants.

Which collections to keep follows SKILL.md step 1.4's rule. Expect the docs to gain a page per
collection the old templates lacked (e.g. `docs/attribute-groups.md` for a registry that defines
groups): that is an intended change, not drift. The docs README template's intro paragraph is the
project's prose: keep the repo's wording there (a link to the core registry's docs, say).

## Support a new kind of convention

When a project starts defining (or generating code for) a kind of convention it didn't before,
e.g. its first events:

1. Copy `assets/collections/<collection>/common/` into the project, and with `docs` also
   `assets/collections/<collection>/docs/`.
2. With `docs`, add the collection's sections to the project's docs `weaver.yaml` (its page entry,
   and its part of the README filter) and `readme.md.j2`, from the layout's copies of those files.
3. For codegen, extend the language templates to cover the collection.
4. Add the conventions to `model/` (`stability: development` unless decided otherwise).
5. Run `make update-golden` and review the new golden files, then `make generate-all`,
   `make validate-registry` and `make test`.

## 6. Consume a new registry

Add the dependency to the registry's `manifest.yaml` (`dependencies.md`), check its core registry
version against the repo's, `ref` or import what the project uses, and run
`make validate-registry`, `make test` and, with codegen, `make validate-generated`. If the
dependency's repo is private, see `dependencies.md` first.

## Finish

Run SKILL.md step 5 in full, then summarize every rename and moved file for the user, and call
out anything that needs a human: branch protection rules, bot configuration, the next release.
