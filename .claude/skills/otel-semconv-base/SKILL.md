---
name: otel-semconv-base
description: Set up the shared Weaver tooling that a weaver-based OpenTelemetry semantic conventions project needs before anything else, and that the other otel-semconv skills (registry, docs, codegen, release, renovate) build on - the pinned weaver version and its local install, a Makefile with the weaver runner, a CI workflow that installs weaver with its setup-weaver action (or the install script where an organization doesn't allow that action) behind one aggregate check, and the template regression test with its fixture and golden files. Use to start a weaver-based semconv project, when another otel-semconv skill needs the base, or to bring a project's weaver pin, install, Makefile runner or CI gate up to date.
---

# Weaver base for semantic conventions projects

This skill sets up what every weaver-based semantic conventions project shares, whatever else it
does. Other skills add parts on top: a registry, docs, generated code, releases, Renovate. Its
files are under `assets/`, and you copy them into the project with your own file tools: nothing
beyond what the project needs anyway (weaver, make, jq, git) is required. Everything the project
does is a make target, so it works the same for any language and in CI.

Read `reference/layout.md` before changing anything, and use the terms in
`reference/glossary.md` in everything you write.

## Parts

| Part | Adds | When |
|---|---|---|
| `core` | `versions.env` (the weaver pin), `.weaver.toml`, `.gitignore`, `scripts/install-weaver.sh`, the Makefile's `project` and `common` sections | always |
| `templates` | the fixture registry, the Makefile's `templates` section (`test-templates`, `update-golden`), the CI workflow with its aggregate job | the project has templates of its own (for generated code, say) |
| `no-drift` | the `assert-no-drift` action | the project commits generated output |

A skill that builds on this one says which parts it needs. Asked for directly, set up `core`, and
the others only when the user wants what they're for.

## 1. Gather facts first

Ask the user, or look up, rather than assuming:

1. **The repo and where the project lives in it**: the repo root or a subdirectory (an SDK
   module, say), which changes a few settings (`reference/layout.md`, "Projects in a
   subdirectory"). Also whether the repo is private (`gh api repos/<owner>/<repo> --jq .private`).
2. **What's there already**: a Makefile, `versions.env`, `.weaver.toml`, CI workflows that run
   weaver, an older copy of any base file. In an update, list each and compare it with its asset.
3. **Whether the organization allows weaver's setup-weaver action.** An organization that
   allowlists actions must allow it (`reference/layout.md`, "The CI workflow"). When you can't
   tell, set up the action, and say that the first CI run shows it: a run blocked by the
   allowlist fails with `startup_failure`. If it is blocked and won't be allowed, switch to the
   fallback.
4. **With `templates`**: which collections the templates cover (at least one), and the core
   registry release the project depends on, for the fixture's manifest. The latest is
   `gh api repos/open-telemetry/semantic-conventions/releases/latest --jq .tag_name`.
5. **The weaver pin**: `weaver --version` must be the pinned version (`assets/core/versions.env`);
   `make install-weaver` installs it. Look for a newer release
   (`gh api repos/open-telemetry/weaver/releases --jq '.[0].tag_name'`) and ask before bumping. In
   an update the repo's pins stay as they are unless the user agrees. A weaver pin is in two
   places, `WEAVER_VERSION` and the setup-weaver action's commit in the workflows: they always
   name the same release.

## 2. Copy the layout

Follow "Copying" in `reference/layout.md`: copy each part's files, write the Makefile (and, with
`templates`, the CI workflow) from `assets/project/` with only the sections of the parts set up,
and replace every `@@TOKEN@@`. Read every file that exists before replacing it.

## 3. Verify

Don't call the work done until every item below that applies has passed, and say which ones you
ran. Run them from the project directory.

1. Nothing left to fill in: searching the project's files (hidden files included, ignored build
   output not, e.g. `rg --hidden --glob '!.git'`) for `@@` finds nothing. A project in a
   subdirectory also searches the repo root's `.github/`. Then run the repo's formatter or linter
   in check mode over the copied files, where it has one, and check them against its
   `.editorconfig`: fix the whitespace the Rules keep as the repo's, and say in the hand-over what
   else it flags in a base file, which stays as the asset has it.
2. Every sectioned file has balanced `==== <name>` / `==== end <name>` lines, and only the
   sections of the parts set up (and `private`, for a private repo).
3. `make help` lists `test`, `generate-all`, `install-weaver` and `clean`, and with `templates`
   `test-templates` and `update-golden`. `make require-weaver` passes.
4. With `templates`: `make update-golden`, then review the golden files; then `make test-templates`
   passes.
5. With a CI workflow: it keeps exactly the parts' jobs and `needs` entries, and installs weaver
   one way in every job. Check the workflows with zizmor only when the repo uses it (a workflow
   of its own runs it, or its rulesets' `code_scanning` rule names it). Once the user has pushed
   the change, watch the first run (`gh run watch`) and fix what fails.

## 4. Hand over

Tell the user what was created or changed, what each make target does, which Verify items ran
and their results, how the workflows install weaver (the action or the fallback), and what is
left for a human: requiring the CI aggregate job (`CI_GATE_JOB`, `required-status-check` by
default) in branch protection, which a private repo has only on a paid GitHub plan (on GitHub
Free, say so instead), and getting setup-weaver allowed where the fallback is in use and the user
wants the action.

## Rules

- Never replace a file in the user's repo without reading it first.
- Name neither this skill nor "the layout" in what you write into the repo (docs, comments,
  commit-ready text), even when the user's request does: its readers can't follow either.
- Keep the copied files identical to `assets/`: the Makefile's targets, the action, the
  workflow's steps, the fixture. Project choices go in the settings at the top of each Makefile
  section and in the tokens. A base file the repo already has takes the asset's content, except
  for what stays the repo's:
  - its pins: the values in `versions.env` and the pinned action SHAs (bump them only with the
    user's agreement);
  - its own additions: extra CI steps and jobs, extra targets outside the base sections,
    `# renovate:` annotations, comments pairing a pin with another copy of it;
  - the repo's formatting rules for the file types it formats (`.editorconfig`, a formatter
    config), as whitespace. A line longer than the repo allows stays as it is.

  When the layout itself must change, change it in this skill and say so.
- Use the glossary's terms, and never the ones it rules out.
- Add no third-party GitHub Actions: the layout's jobs use `actions/*`, weaver's own setup-weaver
  action and local actions only, and fall back to the install script where setup-weaver isn't
  allowed (`reference/layout.md`, "The CI workflow"). In those jobs, replace a third-party setup
  action with its `actions/*` equivalent where one exists, and any other way of installing weaver
  with setup-weaver. The repo's own jobs and workflows keep their actions.
