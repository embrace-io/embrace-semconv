# Current practices

Each practice, how to tell a repo lacks it, and the skill that applies it. They are in the order to
apply them: later ones build on earlier ones, and the `definition/2` migration comes before
anything that regenerates output, so its before-and-after comparison stays clean.

| # | Practice | The repo lacks it when | Applied by |
|---|---|---|---|
| 1 | **Pinned weaver, one Makefile, one runner**: `versions.env` pins weaver; every weaver run goes through the Makefile's `RUN_WEAVER` (JSON diagnostics, unmatched imports fail); an empty-or-template-only `.weaver.toml` | weaver is unpinned or pinned in several places, scripts run weaver directly, there's no `.weaver.toml` | otel-semconv-base |
| 2 | **weaver installed in CI by its setup-weaver action**, pinned to the commit of the release `versions.env` pins, or by `make install-weaver` where the organization doesn't allow that action | a workflow downloads weaver itself, uses a local install action, a container image, or `cargo install` | otel-semconv-base |
| 3 | **One aggregate CI check** that needs every job, required by branch protection | branch protection requires each job by name, or nothing is required | otel-semconv-base |
| 4 | **`definition/2` definition files** | any definition file is v1 (top-level `groups:`, no `file_format`), or the manifest is `registry_manifest.yaml` | this skill (`migrations.md`), then otel-semconv-registry |
| 5 | **The registry's validations**: the resolved dependency tree, the shared policy pack at a pinned commit, OPA unit tests for any local policies, backwards compatibility against a baseline, known violations for legacy keys, invalid registries that prove each validation | `weaver registry check` runs with no shared pack or an unpinned one, there's no baseline, local policies have no tests, or nothing proves the validations still fail | otel-semconv-registry |
| 6 | **Docs from the shared templates** of opentelemetry-weaver-packages, at the policy pack's commit, with imported namespaces left out | the repo has docs templates of its own (`templates/registry/markdown/`), or its docs aren't generated, or aren't checked for drift in CI | otel-semconv-docs |
| 7 | **Releases from a prepared draft**, with the OTEP 4815 publication artifacts, from the default branch, after validation | the registry is published another way (tags pushed by hand, a workflow that creates releases on its own), or a `-dev` family has a release workflow of its own | otel-semconv-release |
| 8 | **Generated code with a template test and a platform check**, generated only by `make generate` when it's committed | a build task generates committed code, templates have no golden-file test, or nothing compiles the generated code in CI | otel-semconv-codegen |
| 9 | **A published package for the core registry alone**: code that needs only the core registry's conventions, in a language whose SIG publishes them as a package for other projects to depend on (the otel-semconv-consume skill's `reference/languages.md`), depends on that package | the repo generates constants from the core registry alone, in a language with such a package that has what it uses | otel-semconv-consume |
| 10 | **Renovate for every pin**, weekly, with weaver's CLI and action together and the Renovate version pinned | pins are bumped by hand, by Dependabot (which can't bump these), or by a Renovate config without these rules | otel-semconv-renovate |

## Notes on some practices

- **2.** Replacing a local install action: check first whether other repos use it (the
  inventory's consumer search). If they do, keep it (with its inputs and description) for them,
  and switch only this repo's workflows.
- **5.** The public-attribute-groups policy is not a practice to add: it fits only a registry
  whose consumers import its attributes by group, and rejects every attribute of one whose
  attributes are in no public group. Keep it where the repo has it, and propose it only when the
  user says consumers import by group (the otel-semconv-registry skill, step 1).
- **6.** The docs change: different layout (a directory per namespace), badges, wording, links
  under the docs' base URL. That is the expected result, not drift; say so in the change's
  description. Golden files and a template test that only the repo's docs templates used go with
  them; the base's template test stays only for templates the repo still has (codegen). The
  docs target replaces everything under `DOCS_DIR`: in a repo whose `docs/` also holds
  hand-written pages (spec prose with tables the repo refreshes with
  `weaver registry update-markdown`), set `DOCS_DIR` to the directory of generated docs alone
  (e.g. `docs/registry`), and keep the pages and their refresh as the repo had them.
- **9.** Switching to the package removes the generated code and its templates, and changes how the
  project's code imports the constants: it's a code change in the consuming project, and the
  constants' names follow the package's. Check the package carries the core registry release the
  project needs, and every convention it uses, before proposing it.
