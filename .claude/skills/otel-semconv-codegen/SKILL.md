---
name: otel-semconv-codegen
description: Generate language-specific source code (constants, typed attribute keys) from an OpenTelemetry semantic conventions registry with Weaver and custom templates - from the core registry, from a published federated registry (all of it or some of its keys), or from a registry of the project's own - with the pinned weaver version and its local install, make targets that generate, validate and package the code for its platform, a template regression test with its fixture and golden files, and a CI workflow that fails on stale or invalid generated code, behind one aggregate check, plus Renovate to bump its pins if wanted. Use when a project needs semantic convention constants generated for a language, when the published package for the core registry doesn't fit, or to set up or update a weaver codegen project.
---

# Code generation from a semantic conventions registry

This skill sets up a project that generates code from a semantic conventions registry with weaver:
the pinned weaver version and its local install, a Makefile whose targets generate, validate and
package the code, a template regression test, and a CI workflow behind one aggregate check. Its
files are under `assets/`, and you copy them into the project with your own file tools: nothing
beyond what the project needs anyway (weaver, make, jq, git) is required. Everything the project
does is a make target, so it works the same for any language and in CI.

Read `reference/layout.md` before changing anything, and use the terms in
`reference/glossary.md` in everything you write.

| Reference | Read it for |
|---|---|
| `reference/layout.md` | the files, where they go, the Makefile and CI workflow, settings and tokens |
| `reference/sources.md` | choosing and pinning the registry the code is generated from |
| `reference/templates.md` | what weaver templates see, writing them for any language, the codegen contract |
| `reference/renovate.md` | the `renovate` part: adapting the config, the Renovate version, checking the config |

## Parts

| Part | Adds | When |
|---|---|---|
| `core` | `versions.env` (the weaver pin), `.weaver.toml`, `.gitignore`, `scripts/install-weaver.sh`, the Makefile's `project` and `common` sections | always |
| `templates` | the fixture registry, the Makefile's `templates` section (`test-templates`, `update-golden`), the CI workflow with its aggregate job | always |
| `codegen` | the Makefile's `codegen` section (`generate`, `validate-generated`, `package-generated`), the CI workflow's `validate-generated` job | always |
| `no-drift` | the `assert-no-drift` action | the generated code is committed |
| `renovate` | the Renovate config, `versions.env`'s `renovate` section (`RENOVATE_VERSION`) | the user wants the pins bumped automatically, or the repo already runs Renovate |

## When this is the wrong tool

A project that needs only the core registry's conventions, in a language whose SIG publishes them
as a package for other projects to depend on, depends on that package instead: the
otel-semconv-consume skill. Its `reference/languages.md` lists those languages, and the ones whose
constants are part of the SDK rather than such a package. Use this one when there is no such
package, it lags the core registry release the project needs, the conventions come from another
registry, or the project wants code of its own shape.

## 1. Gather facts first

Ask the user, or look up, rather than assuming:

1. **The source registry** (`reference/sources.md`): the core registry, a published federated
   registry, or a registry of the project's own. Code generated from a registry another project
   publishes is a consumer: it gets codegen alone, with no registry of its own, whether it wants
   all of that registry or some of its keys. Also whether it, or a registry it depends on, is in a
   private repository, which keeps the `private` sections (`reference/layout.md`, "Sectioned
   files").
2. **The repo and where the project lives in it**: the repo root or a subdirectory (an SDK
   module, say), which changes a few settings (`reference/layout.md`, "Projects in a
   subdirectory"). The branch it integrates on (`DEFAULT_BRANCH`, `reference/layout.md`,
   "Tokens"). Also whether the repo is private (`gh api repos/<owner>/<repo> --jq .private`), for
   branch protection (step 4) and a Renovate validator's permissions.
3. **The language**, where the generated code goes (a directory holding only generated code; in an
   update, look for hand-written files already in it, which each need a template of their own),
   and whether it is committed.
4. **Which kinds of conventions** the code covers (attributes, metrics, …): the collections the
   template test needs, at least one. Never add one nobody asked for. And the core registry
   release the fixture's manifest depends on (`reference/sources.md`, "The fixture's core
   registry").
5. **How the platform validates and packages code**: its compiler or type-checker, test runner,
   package format, and whether a build tool already runs weaver (`reference/templates.md`,
   "Platform integration"). Check the host's own toolchain pins (Node `devEngines`, the JDK)
   against what's installed.
6. **What's there already**: a Makefile, `versions.env`, `.weaver.toml`, CI workflows that run
   weaver, an older copy of any of these files. In an update, list each and compare it with its
   asset.
7. **Whether the organization allows weaver's setup-weaver action.** An organization that
   allowlists actions must allow it (`reference/layout.md`, "The CI workflow"). When you can't
   tell, set up the action, and say that the first CI run shows it: a run blocked by the
   allowlist fails with `startup_failure`. If it is blocked and won't be allowed, switch to the
   fallback.
8. **The weaver pin**: `weaver --version` must be the pinned version (`assets/core/versions.env`);
   `make install-weaver` installs it. When the machine's weaver is another version that other
   projects use, install the pin elsewhere and run the targets with it (`WEAVER_INSTALL_DIR` and
   `WEAVER`, `reference/layout.md`) rather than replacing it. Look for a newer release
   (`gh api repos/open-telemetry/weaver/releases --jq '.[0].tag_name'`) and ask before bumping. In
   an update the repo's pins stay as they are unless the user agrees. The layout is tested with
   the pinned release, and its template test also with weaver 0.26.1; with an older pin, run the
   template test with it before keeping it. A weaver pin is in two places, `WEAVER_VERSION` and the
   setup-weaver action's commit in the workflows: they always name the same release.
9. **Renovate in the repo**: an existing config (`renovate.json`, `renovate.json5`,
   `.renovaterc*`, `.github/renovate.json*`), the hosted app or a self-hosted workflow, a config
   validator workflow, and whether the repo bumps the core registry some other way. A config
   means the repo runs Renovate, even when the app has opened no pull request yet: then the
   hand-over asks the user to check that the app is enabled. With the `renovate` part, the
   Renovate version (`reference/renovate.md`, "The Renovate version").

## 2. Set it up

1. Follow "Copying" in `reference/layout.md`: copy each part's files and the chosen collections,
   write the Makefile and the CI workflow from `assets/project/` with only the sections of the
   parts set up, and replace every `@@TOKEN@@` (`reference/layout.md`, "Tokens"). Read every file
   that exists before replacing it. Set `TEMPLATE_TARGETS` to include `$(CODEGEN_TARGET)`, and
   `all:` to run `validate-generated`.
2. Write `templates/registry/<CODEGEN_TARGET>/` for the language, covering only the chosen
   collections (`reference/templates.md`). In an update, the generated code staying unchanged
   comes first (Verify 7): a rule from `reference/templates.md` that the repo's templates don't
   follow yet goes in only where it leaves the output unchanged (sorting output that is already
   sorted, say). List the others for the user as changes of their own, saying which the Rules
   require (keeping deprecated constants), so the user decides when the output changes.
3. Replace the `validate-generated` and `package-generated` stubs with the platform's own tools
   ("The codegen contract"), and add the toolchain's setup steps to the CI job.
4. Run `make update-golden` and read every golden file: they are the expected output from here
   on. Golden files of a codegen target are source files of that language: keep them out of the
   host project's build and lint, or make them pass both.
5. With `renovate`: where the repo already has a Renovate config, merge the asset's
   `customManagers` and `packageRules` into it instead of copying the file. Annotate
   `SOURCE_REGISTRY` when it is pinned to a release, keep or delete the fixture manifest's
   `# renovate:` line (`reference/sources.md`, "The fixture's core registry"), and with a
   validator workflow of the repo's own, make it validate the way `reference/renovate.md` says.
   Without `renovate`, the fixture manifest's line stays as it is.
6. Tell the project's developers how to regenerate, in the host project's own docs.

## 3. Verify

Don't call the work done until every item below that applies has passed, and say which ones you
ran. Run them from the project directory.

1. Nothing left to fill in: searching the project's files (hidden files included, ignored build
   output not, e.g. `rg --hidden --glob '!.git'`) for `@@` finds nothing. A project in a
   subdirectory also searches the repo root's `.github/`. Then run the repo's formatter or linter
   in check mode over the copied files, where it has one, and check them against its
   `.editorconfig`: fix the whitespace the Rules keep as the repo's, and say in the hand-over what
   else it flags in a copied file, which stays as the asset has it. For a linter that can only
   auto-correct (writes files), stage the change first (`git add`), run it, and read what it
   changed in the unstaged `git diff`: nothing, or only what the Rules keep as the repo's.
2. Every sectioned file has balanced `==== <name>` / `==== end <name>` lines, and only the
   sections of the parts set up (and `private` only where `reference/layout.md`, "Sectioned
   files", keeps it).
3. `make help` lists `test`, `generate-all`, `install-weaver`, `clean`, `test-templates`,
   `update-golden`, `generate`, `validate-generated` and `package-generated`.
   `make require-weaver` passes.
4. `make test-templates` passes, and the golden files hold output for every chosen collection.
5. `make validate-generated` and `make package-generated` pass; then read some of the generated
   code yourself. The host project's own checks pass on what the change adds too: the build,
   lint and test tasks its CI runs over the generated code and any new module or target (an
   Android module's lint writes a baseline on its first run and fails, say).
6. `validate-generated` fails on bad output: make the template emit code that can't compile, see
   it fail, and revert ("The codegen contract"). Check that the compile or type-check is what
   failed, not a step before it (a linter that rejects the same code would hide a compile step
   that passes it).
7. In an update: the generated code is unchanged unless the update was meant to change it.
   Regenerate and compare with what was committed (`git diff`, plus `git status` for new files),
   and account for every difference.
8. The CI workflow keeps exactly the parts' jobs and `needs` entries, with the
   `validate-generated` job among them, plus the jobs a superseded workflow brings over
   (`reference/layout.md`, "Superseded workflows"), and installs weaver one way in every job.
   Check the workflows with zizmor only when the repo uses it (a workflow of its own runs it, or its
   rulesets' `code_scanning` rule names it), at the version and persona it uses there, e.g.
   `uv tool run zizmor --offline .github` (the default persona; uv may reuse a version it has
   cached), run from the repo root; where the repo's own runs are online, drop `--offline` and
   give it a `GH_TOKEN` (`gh auth token`) for the online audits. Once the user has pushed the
   change, watch the first run (`gh run watch`) and fix what fails.
9. With `renovate`: the config validates, and Renovate's extraction lists every `# renovate:` line
   in the project's files, under its file and `depName` (`reference/renovate.md`, "Checking the
   config"). Once the user has pushed, Renovate's Dependency Dashboard issue appears (with the
   hosted app, once the app is enabled for the repo) and lists the pins.

## 4. Hand over

Tell the user what was created or changed, what each make target does, which Verify items ran and
their results, how the workflows install weaver (the action or the fallback), the platform
decisions you made in `validate-generated` and `package-generated`, and what is left for a human:
committing the generated code, if it is committed; a code review of the templates' output; bumping
`SOURCE_REGISTRY` when a new release is wanted, or with `renovate`, enabling the Renovate app for
the repo if it isn't and reviewing the bump pull requests, which arrive on the config's schedule
(Monday mornings, UTC, with the asset's) and need the golden files and generated code regenerated
when they change what is generated (and the fixture's core registry moved by hand where
`reference/sources.md` says); requiring the CI aggregate job (`CI_GATE_JOB`,
`required-status-check` by default) in branch protection, which a private repo has only on a paid
GitHub plan (on GitHub Free, say so instead); and getting setup-weaver allowed where the fallback
is in use and the user wants the action.

## Rules

- Never replace a file in the user's repo without reading it first.
- Name neither this skill nor "the layout" in what you write into the repo (docs, comments,
  commit-ready text), even when the user's request does: its readers can't follow either.
- Keep the copied files identical to `assets/`: the Makefile's targets, the action, the
  workflow's steps, the fixture. Project choices go in the settings at the top of each Makefile
  section and in the tokens, and the platform's own tools in `validate-generated` and
  `package-generated`; the fixture manifest loses its `# renovate:` line where
  `reference/sources.md` ("The fixture's core registry") says, and the workflow's drift step and
  header line take the actionlint form where `reference/layout.md` ("Local actions") gives it. A
  file the repo already has takes
  the asset's content, except for what stays the repo's:
  - its pins: the values in `versions.env` and the pinned action SHAs (bump them only with the
    user's agreement);
  - its own additions: extra CI steps and jobs, extra targets outside the asset's sections,
    `# renovate:` annotations, comments pairing a pin with another copy of it;
  - the repo's formatting rules for the file types it formats (`.editorconfig`, a formatter
    config), as whitespace. A line longer than the repo allows stays as it is.

  When the layout itself must change, change it in this skill and say so.
- Use the glossary's terms, and never the ones it rules out.
- Add no third-party GitHub Actions: the layout's jobs use `actions/*`, weaver's own setup-weaver
  action and local actions only, and fall back to the install script where setup-weaver isn't
  allowed (`reference/layout.md`, "The CI workflow"). In those jobs, replace a third-party setup
  action with its `actions/*` equivalent where one exists, and any other way of installing weaver
  with setup-weaver. The repo's own jobs and workflows keep their actions, and the platform's
  toolchain setup in the `validate-generated` job uses `actions/setup-*`, or a runner image that
  ships the toolchain (`reference/templates.md`, "Platform integration").
- Never pin `SOURCE_REGISTRY` to a branch: a release tag, or the path of the project's own
  registry directory.
- Never pin Renovate's version to `@latest` or leave it unversioned in a validator, and keep a
  repo's own Renovate `extends`, `schedule` and `labels` when merging.
- Keep deprecated conventions in the generated code, marked deprecated, unless nobody compiles
  against the code yet (`reference/templates.md`, "Writing the Jinja").
