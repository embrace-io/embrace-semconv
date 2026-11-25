# The layout

A project's files come from three places:

- `assets/<part>/`, copied to the same paths in the project: `core` and `templates` always,
  `no-drift` when the generated code is committed, `renovate` when it is set up.
- `assets/collections/<collection>/`, the same, for each chosen collection.
- `assets/project/`: the Makefile and the CI workflow, cut down to the project's parts.

The templates are the project's own: `templates/registry/<CODEGEN_TARGET>/`, written for the
language (`templates.md`).

The assets carry no mark of where they came from (a repo's readers couldn't follow one), so a
repo's copied files are the ones at the paths the assets have: tell them from the repo's own
files, and see whether a copy is current, by comparing each with its asset. Many of the files are
dotfiles (`.github/`, `.weaver.toml`, `.gitignore`), so list the assets with hidden files shown.

## Files by part

### `core` (always)

```
versions.env                         the weaver pin
.weaver.toml                         `[template]` settings only, empty until the templates need some
                                     (see below)
.gitignore                           build output, editor and OS noise
scripts/install-weaver.sh            installs pinned weaver locally (`make install-weaver`); CI
                                     installs it with weaver's own setup-weaver action
```

Plus the Makefile's `project` and `common` sections. The install script is run with
`bash <script>`, so it works whether or not the copy kept its executable bit.

### `templates` (always)

```
templates_test/fixture/manifest.yaml the fixture registry's manifest; its definitions come from the
                                     chosen collections
```

Plus the Makefile's `templates` section, and the CI workflow with its `test-templates` job and its
aggregate job. Then `templates_test/golden/<target>/`, the expected output of each template
target, made with `make update-golden`: none ships, since it depends on the templates and the
chosen collections.

### `codegen` (always)

No files of its own: the Makefile's `codegen` section, which adds `generate` (to
`generate-all::`), `validate-generated` (to `test::`) and `package-generated`, the last two as
failing stubs the project replaces (`templates.md`, "The codegen contract"), and the CI workflow's
`validate-generated` job.

### `no-drift` (when the generated code is committed)

```
.github/actions/assert-no-drift/     fails when committed generated files differ from a regeneration
```

Without committed code, delete the `validate-generated` job's "Compare committed code with the
regenerated code" step and leave `no-drift` out.

### `renovate` (when the pins are to be bumped automatically)

```
.github/renovate.json5               the Renovate config
```

Plus `versions.env`'s `renovate` section. Adapting the config to the repo, and checking it:
`renovate.md`.

### Collections

Each kind of convention the project's templates cover is a collection: `attributes`,
`attribute-groups`, `events`, `metrics`, `spans` and `entities`. Choose at least one, and copy
`assets/collections/<collection>/` for each:

```
templates_test/fixture/fixture/<collection>.yaml
                                     a fixture definition, so the templates for it are exercised
```

The attributes fixture defines the fixture's own attributes (a string with a note, an enum, a
deprecated attribute and a long key) and exports them through its own public group,
`registry.fixture.defined`. The other fixtures reference the core registry's attributes, so any
combination of collections resolves. Each fixture imports its kind from the core registry where
it has some, so the templates' provenance filters have something to filter out.

## Sectioned files

The Makefile, the CI workflow and `versions.env` have sections.

- **Where a section runs:** from a `# ==== <name>` line to its `# ==== end <name>` line. The
  Makefile's start lines may carry a description after the name (`# ==== common: tool pins …`).
- **What a name is:** a part, `project`, `common`, or `private`.
- **What to keep:** `project`, `common`, `templates` and `codegen` always; `renovate` with that
  part; `private` exactly when weaver fetches a registry from a private repository: the source
  registry, or a registry it depends on (`sources.md`, "A private source registry"). A private
  repo whose source registry is public needs no `private` sections.
- **Nesting:** sections can nest, and deleting a section deletes the ones inside it.
- **Deleting:** only where a section was deleted, if that leaves two blank lines in a row, keep
  one; if it leaves one at the end of the file, right after a block's opening line (e.g.
  `steps:`) or right before a section's end line, remove it. Blank lines anywhere else are the
  asset's and stay.

## The Makefile

The Makefile is one file, as in the core registry and the other OpenTelemetry registries. Its
sections, in order:

| Section | Targets |
|---|---|
| `project` | `all` (the default goal) |
| `common` | `test`, `generate-all` (aggregators), `install-weaver`, `require-weaver`, `require-jq`, `clean`, `help`, and `RUN_WEAVER` |
| `templates` | `test-templates`, `update-golden` |
| `codegen` | `generate`, `validate-generated`, `package-generated` |

A section uses settings only from sections above it. It starts with its settings, and adds itself
to `test::`, `generate-all::` and `help::` (double-colon rules, so each section's entries stand
alone). A target of the project's own goes outside the sections.

Settings a project may change, at the top of their sections:

| Setting | Section | Default | Meaning |
|---|---|---|---|
| `all:` prerequisites | project | token | what `make` alone runs, usually `validate-generated` |
| `WEAVER_FLAGS` | common | empty; `--allow-git-credentials` with the `private` section | extra flags for every weaver run |
| `WEAVER` | common | `weaver` (the one on `PATH`) | the weaver every target runs: a path to the pinned one when the machine's own weaver must stay, e.g. `make generate WEAVER=<dir>/weaver` |
| `WEAVER_INSTALL_DIR` | common | empty (`~/.local/bin`) | where `make install-weaver` installs weaver: set it on the command line when the machine's own weaver must stay, then run the targets with `WEAVER=<dir>/weaver` |
| `TEMPLATES` | templates | `templates` | the templates directory |
| `TEMPLATE_TARGETS` | templates | token | the template targets to test, including `$(CODEGEN_TARGET)` |
| `FIXTURE`, `GOLDEN` | templates | `templates_test/fixture`, `templates_test/golden` | |
| `SOURCE_REGISTRY` | codegen | token | the registry the code is generated from (`sources.md`) |
| `CODEGEN_TARGET` | codegen | token | the template target under `templates/registry/` |
| `GENERATED_DIR` | codegen | token | the output directory, emptied on every run, so it holds only generated files |

Any of them can also be overridden on the command line (`make test-templates TEMPLATE_TARGETS=x`).

## The CI workflow

`ci-validation.yaml` has the same sections around its jobs. Its aggregate job (`CI_GATE_JOB`,
`required-status-check` by default) tags each `needs` entry with the sections its job belongs to.
Delete an entry when any of its tags isn't set up.

- **The aggregate job:** branch protection names a check by the job's `name:`. So the aggregate
  job's name equals its ID and must be unique among the repo's workflows.
- **Names in a host repo:** a project at the repo root uses the defaults (`ci-validation.yaml`,
  `CI validation`, `required-status-check`). A project in a subdirectory of a repo with its own
  CI (an SDK module, say) prefixes all three with its directory name: e.g.
  `semconv-ci-validation.yaml`, `Semconv CI validation`, `semconv-required-status-check`.
- **Superseded workflows:** a workflow that this one replaces (an older validation or
  drift-check workflow) is deleted in the same change, and branch protection is told about the
  new aggregate job's name. Its jobs that no job here replaces (a `weaver registry check` of the
  project's own registry, say) move into this workflow as the repo's own jobs, outside the
  sections, each with an entry in the aggregate job's `needs`, except a job whose `if:` skips it
  on some events: the aggregate job fails on a skipped job, so that one stays out of `needs`. Its
  `run:` steps now start in the project directory (the workflow's `defaults`), so a moved job
  whose paths are relative to the repo root sets `defaults: run: working-directory: .` of its
  own, as the aggregate job does.
- **Weaver's setup action:** every job that runs weaver installs it with
  `open-telemetry/weaver/.github/actions/setup-weaver`, pinned to the commit of the release
  `versions.env` pins (`gh api repos/open-telemetry/weaver/commits/<tag> --jq .sha`), with that
  version as its `version` input. Bump both together. Where Dependabot bumps the repo's GitHub
  Actions, it would move the action's commit alone: tell the user, give the `github-actions`
  entry of `.github/dependabot.yml` an ignore entry for the action, under the action's full path
  (Dependabot names the dependency that way; `open-telemetry/weaver` alone doesn't match it),
  and bump both together with the `renovate` part or by hand:

  ```yaml
      ignore:
        - dependency-name: open-telemetry/weaver/.github/actions/setup-weaver
  ```

  Dependabot's next run then closes any setup-weaver pull request it has open.
- **When the action isn't allowed:** an organization that allowlists actions must allow
  setup-weaver, or every run that uses it fails to start (`startup_failure`). Where it isn't
  allowed and the user doesn't get it allowed, every job installs weaver with the project's own
  install script instead. Replace the "Read pinned weaver version" and "Install Weaver" steps of
  each job with this one step:

  ```yaml
        - name: Install Weaver
          run: make install-weaver
  ```

  It installs to `~/.local/bin`, which is on `PATH` on GitHub-hosted runners. Without the
  action, Renovate bumps only `WEAVER_VERSION`, and there's no cache. Say which way the
  workflows install weaver in the hand-over.
- **Local actions:** the workflows call the project's own actions as `uses: $/.github/actions/…`,
  GitHub's self-repository syntax. It resolves to the repository at the commit that is running,
  with no checkout, and needs runner 2.336.0 or newer (GitHub-hosted runners have it). zizmor
  1.30 and later report every `uses: ./…` as `help[self-repository]` in all its personas, and a
  repo whose rules block on every zizmor alert can't merge them; `$/…` has no finding. actionlint
  1.7.12 rejects `$/…` ("invalid format because ref is missing"), so tell the user before setting
  this up in a repo whose developers use actionlint: its CI runs it, or its workflows' comments
  name it (a `zizmor: ignore[self-repository]` with an actionlint reason, say). Where the user
  chooses actionlint, the step calls the action as `uses: ./.github/actions/assert-no-drift`,
  ending that line with `# zizmor: ignore[self-repository]` as such a repo's other workflows do
  (zizmor then reports the finding as ignored); the job checks the repo out first, so `./`
  resolves. The workflow's header line about `uses: $/…` then describes nothing: replace it with
  `# The drift step calls this repository's action as ./…, after the checkout, for actionlint.`
- **No path filter:** don't add `paths:` to the workflow. The aggregate job is a required check,
  and a required check that never runs blocks the pull request.
- **The `validate-generated` job** installs weaver the way the other jobs do: when the workflow
  uses the fallback for setup-weaver, it does too. The platform's toolchain setup goes before its
  validate step, as the job's comment says.

## Copying

With your own tools: `cp` and `rm` for whole files, your editor for the rest; the skill ships no
scripts. Read every copied file before editing it, whether `cp` created it or replaced one you had
read (the repo's old Makefile, say): an editor tool refuses edits to a file it hasn't read since it
last changed, and reading the asset doesn't count as reading the copy.

1. For each part set up, copy every file under `assets/<part>/` to the same relative path in the
   project, hidden files included, except that `.github/` goes at the repo root when the project
   is in a subdirectory ("Projects in a subdirectory"). Keep file contents exact. In a new project
   at the repo root, a recursive copy (`cp -R assets/<part>/. <project>/`) is the simplest way.
   Otherwise copy file by file: a recursive copy would overwrite the repo's own files. Then
   compare each copy with its asset (`git diff --no-index <asset> <copy>`): only tokens, deleted
   sections, what the Rules keep of the repo's, the fixture manifest's `# renovate:` line where
   `sources.md` ("The fixture's core registry") deletes it, and the actionlint form of the drift
   step ("Local actions") may differ.
2. Copy `assets/collections/<collection>/` for each chosen collection the same way.
3. Write the project's `Makefile` from `assets/project/Makefile` and
   `.github/workflows/ci-validation.yaml` from `assets/project/ci-validation.yaml`, keeping only
   the sections of the parts set up. Copy the Makefile rather than retyping it: it is indented
   with tabs.
4. Replace every `@@TOKEN@@` (below). Then search the project, hidden files included, for `@@`:
   there must be no matches.
5. Once the templates are in place, run `make update-golden`, and review the golden files.
6. Never overwrite an existing file blindly. Read it first. A file the repo already has (an older
   copy of an action, the Makefile) takes the asset's content, with the exceptions the Rules
   list: carry over the repo's settings and pins, and keep its own additions. The asset's pins,
   to replace with the repo's: the values in `versions.env` and the pinned SHAs of `uses:` lines
   in the workflows.

## Tokens

| Token | Where | Value |
|---|---|---|
| `PROJECT_DIR` | CI workflow | the project directory relative to the repo root (`.` at the root) |
| `DEFAULT_BRANCH` | CI workflow | the branch the repo integrates on, its default branch on GitHub (`gh repo view <owner>/<repo> --json defaultBranchRef --jq .defaultBranchRef.name`); a local clone's `origin/HEAD` can be stale |
| `CI_WORKFLOW_NAME` | CI workflow | `CI validation` at the repo root; prefixed in a subdirectory of a repo with its own CI (e.g. `Semconv CI validation`), as "The CI workflow" says |
| `CI_GATE_JOB` | CI workflow | `required-status-check` at the repo root; prefixed the same way in a subdirectory (e.g. `semconv-required-status-check`) |
| `GENERATED_REPO_PATH` | CI workflow | `GENERATED_DIR` relative to the repo root, normalized (no `..`): e.g. `packages/sdk/src/generated` |
| `ALL_PREREQUISITES` | Makefile `project` | what `make` alone runs, usually `validate-generated` |
| `TEMPLATE_TARGETS` | Makefile `templates` | the template targets the project has: `$(CODEGEN_TARGET)` |
| `LANGUAGE` | Makefile `codegen` | the language generated, e.g. `Kotlin` |
| `SOURCE_REGISTRY` | Makefile `codegen` | see `sources.md`, e.g. `https://github.com/open-telemetry/semantic-conventions@v1.44.0[model]` |
| `CODEGEN_TARGET` | Makefile `codegen` | the template target's directory name, e.g. `kotlin` |
| `GENERATED_DIR` | Makefile `codegen` | where the code goes, relative to the project directory |
| `CORE_VERSION` | fixture manifest | the core registry release the source registry depends on (`sources.md`, "The fixture's core registry"), no `v` (e.g. `1.44.0`) |

## What is required and what is convention

Weaver requires only some of these choices. Keep the conventions anyway: they make every project
look alike.

| Choice | Required by weaver? | Notes |
|---|---|---|
| `manifest.yaml`, exactly that name, directly in a registry directory | **yes** | `manifest.yml` is parsed as a definition file and fails; one in a subdirectory isn't found, so no dependencies load |
| `templates/registry/<target>/` | `registry/` is weaver's documented layout | weaver falls back to `templates/<target>/` only when `registry/<target>/` is missing, undocumented; if both exist the other is silently ignored |
| `templates/` as the templates directory | no | weaver's default for `--templates`; an existing project can keep its path with `TEMPLATES` |

## Things every project gets, and why

- **`.weaver.toml`, with `[template]` settings only.** Weaver applies the first `.weaver.toml` it
  finds walking up from the working directory. Without one here, a stray file in a parent
  directory could skip policies or redirect dependencies (`[resolve.schema_url_overrides]`) for
  every make target. It ships empty; the templates may need `[template]` settings, which some
  templates read from this file alone. Any other setting goes on the Makefile's weaver command
  lines. Its cost is a harmless "⚠ Experimental! - Found config" line on every weaver run.
- **`RUN_WEAVER`** (the `common` section). Every weaver run goes through it: it adds
  `WEAVER_FLAGS`, asks for JSON diagnostics, prints them unwrapped (one line per finding, the
  "definition/2 is not yet stable" warnings collapsed into one), and fails when weaver does or on
  imports that match nothing. The core registry's own files add warnings of their own to every
  run that resolves it (its manifest has no `file_format`, some of its signals no requirement
  level): they are the dependency's, not the project's. The fixture manifest's missing
  `file_format` warning is expected too: the value weaver 0.28 asks for is one older releases reject
  (the asset's comment). Weaver wraps its text
  output to the terminal width, so grepping it is unreliable, and it only warns about dead
  imports.
- **The same pinned weaver locally and in CI**: `versions.env` gives the version to both.
- **One aggregate CI job for branch protection**, so adding or renaming a job never requires
  touching the protection rule.

## Projects in a subdirectory

A codegen project often lives in a subdirectory of an SDK's repo, say `semconv/`, with
`GENERATED_DIR` pointing out of it into the SDK's sources (`../src/generated`):

- the Makefile, `versions.env`, `.weaver.toml`, `scripts/`, `templates/` and `templates_test/` go
  in the subdirectory;
- `.github/actions/` and `.github/workflows/` must be at the repo root; set `PROJECT_DIR` to the
  project's path, and `GENERATED_REPO_PATH` to `GENERATED_DIR` from the repo root, normalized,
  since the CI job's drift check runs there;
- prefix the CI workflow's file name, `CI_WORKFLOW_NAME` and `CI_GATE_JOB` with the project's
  directory name ("The CI workflow");
- run weaver only through the project's make targets, or from the project directory: weaver
  applies the first `.weaver.toml` walking up from where it runs, and only the project's own
  empty one keeps a parent directory's out.

## Keeping a project current

To refresh a project, compare each of its copied files with `assets/` (and its Makefile and CI
sections with `assets/project/`), bring over what changed, keep the project's settings, and run
SKILL.md's Verify step.
