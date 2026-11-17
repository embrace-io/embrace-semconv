# Inventory

Read the repo before changing anything:

- **The registry**: where the manifest is and what it's called. `manifest.yaml` with a
  `schema_url` is current; `registry_manifest.yaml` with `semconv_version` / `schema_base_url` is
  weaver's legacy form (weaver warns about it). Which definition files are v1 (top-level `groups:`,
  no `file_format`) and which are `file_format: definition/2`. Which kinds of conventions it
  defines: `definition/2` files list them under top-level `attributes:`, `attribute_groups:`,
  `events:`, `metrics:`, `spans:` and `entities:`; v1 files as groups of `type: attribute_group`,
  `event`, `metric`, `span` or `resource`.
- **Tooling**: the Makefile or scripts, pinned tool versions and where (a build tool may pin weaver
  too, e.g. a Gradle version catalog), how CI installs weaver, CI workflows and their job names,
  release workflows, docs templates of the repo's own, dependency bots (Renovate, Dependabot) and
  what they bump, and any build-tool task that runs weaver.
- **Branch protection**: which check names are required. Classic protection:
  `gh api repos/<owner>/<repo>/branches/<branch>/protection`. Repos using rulesets return 404
  there; use `gh api repos/<owner>/<repo>/rules/branches/<branch>`. A 404 there too, or `[]`,
  means no protection or no access to see it: ask. A 403 "Upgrade to GitHub Pro or make this
  repository public" means a private repo on GitHub Free, which can't have protection. A check is
  named by the job's `name:`, not its ID, and renaming a required one breaks merging until the
  rule is updated. Note any `code_scanning` rule too, and the tools it names: the new workflows
  must pass them.
- **Allowed actions**: whether the organization allowlists actions, which decides how CI installs
  weaver (the base skill's `reference/layout.md`, "The CI workflow").
- **What consumers rely on**: published tags, the `schema_url` name, keys, signal names, group IDs,
  generated code paths and names, and any of the repo's actions or workflows that other repos
  reference (a `uses: <owner>/<repo>/.github/actions/...` in someone else's CI: search with
  `gh search code "<owner>/<repo>/.github/actions"`). None of these may change as a side effect of
  an update; an action's inputs and its description for other repos stay.
- **The tags**: which `v*` tags exist and whose they are (the registry skill's step 1), for the
  baseline and the releases.

Then run the existing validations and tests the way the repo runs them (its make targets, its
build), so you know what passed before you touched anything. Save copies to compare with
afterwards: generated docs and committed code are in git already; code generated at build time
isn't committed, so copy its output to scratch; when the repo already packages releases
(`make package`), run it and copy `.build/package` to scratch too. Run weaver by hand only from
the repo's own project directory: weaver applies the first `.weaver.toml` walking up from where it
runs, so a run from anywhere else can pick up an unrelated one.
