# The base layout

A project's base files come from three places:

- `assets/<part>/`, copied to the same paths in the project: `core` always, `templates` and
  `no-drift` when a skill asks for them.
- `assets/collections/<collection>/`, the same, for each chosen collection, with `templates`.
- `assets/project/`: the Makefile and the CI workflow, cut down to the project's parts.

The assets carry no mark of where they came from (a repo's readers couldn't follow one), so a
repo's base files are the ones at the paths the assets have: tell them from the repo's own files,
and see whether a copy is current, by comparing each with its asset. Many of the files are
dotfiles (`.github/`, `.weaver.toml`, `.gitignore`), so list the assets with hidden files shown.

## Files by part

### `core` (always)

```
versions.env                         the weaver pin; other parts add theirs in sections
.weaver.toml                         `[template]` settings only, empty until a part adds some (see
                                     below)
.gitignore                           build output, editor and OS noise
scripts/install-weaver.sh            installs pinned weaver locally (`make install-weaver`); CI
                                     installs it with weaver's own setup-weaver action
```

Plus the Makefile's `project` and `common` sections. The install script is run with
`bash <script>`, so it works whether or not the copy kept its executable bit.

### `templates` (when the project has templates of its own, for generated code say)

```
templates_test/fixture/manifest.yaml the fixture registry's manifest; its definitions come from the
                                     chosen collections
```

Plus the Makefile's `templates` section, and the CI workflow with its `test-templates` job: the
workflow comes with the first part that adds a job. Then `templates_test/golden/<target>/`, the
expected output of each template target, made with `make update-golden`: none ships, since it
depends on the templates and the chosen collections.

### `no-drift` (when the project commits generated output: docs, or committed generated code)

```
.github/actions/assert-no-drift/     fails when committed generated files differ from a regeneration
```

### Collections

Each kind of convention the project's templates cover is a collection: `attributes`,
`attribute-groups`, `events`, `metrics`, `spans` and `entities`. With `templates`, choose at least
one, and copy `assets/collections/<collection>/` for each:

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

The Makefile, `versions.env` and the CI workflow have sections, and other parts' files may too.

- **Where a section runs:** from a `# ==== <name>` line to its `# ==== end <name>` line. In a
  Jinja file the lines are `{#- ==== <name> #}` and `{#- ==== end <name> #}`, and the Makefile's
  start lines may carry a description after the name (`# ==== common: tool pins …`).
- **What a name is:** a part, a collection, `project`, or `private`.
- **What to keep:** `project` and `common` always; `templates` with the templates part; `private`
  only for a private repo, or one whose weaver runs fetch a private registry; every other section
  only when its part or collection is set up.
- **Nesting:** sections can nest, and deleting a section deletes the ones inside it.
- **Deleting:** only where a section was deleted, if that leaves two blank lines in a row, keep
  one; if it leaves one at the end of the file, right after a block's opening line (e.g.
  `steps:`) or right before a section's end line, remove it. Blank lines anywhere else are the
  asset's and stay.

## Skeletons

Some parts ship prose files as skeletons (the docs part's README.md, AGENTS.md and
CONTRIBUTING.md, the release part's RELEASING.md): not sectioned, but with two kinds of markers.

- **Conditional blocks**, between `<!-- skeleton: only … -->` and `<!-- skeleton: end -->`, each on
  a line of its own, apply to some projects only. Keep a block's text when its condition holds,
  drop it otherwise, and remove the markers either way. Blocks can nest (an `end` closes the
  innermost open block), and can sit inside code blocks. The conditions:
  - **stability**, exactly one of: "unstable" (the default: `0.x.0-dev` versions until the
    registry graduates to stable), "stable" (stable from the start, or graduated), or "`-dev`
    family" (every version carries `-dev` for good, `VERSION_SUFFIX := -dev`); a block naming
    two of them (`"unstable" (the default) or "stable"`) holds when either does;
  - with or without `release` (published or not), and "when `BASELINE` is set" (`auto` or a
    pinned path) or empty;
  - a collection being chosen, the registry's `public-groups` policy, "a private repo", "when
    `KNOWN_VIOLATIONS` is set".
- **`<!-- skeleton: fill in: … -->`** is replaced by the text it asks for: what the registry is
  for, its namespaces, the default stability for new conventions.

When done, no `<!-- skeleton` is left. The skeletons link `model/`: adjust the paths when `MODEL`
differs. In a repo that already has these files, merge what's useful into them instead: keep its
text, add what the kept blocks say that it lacks, and correct what they contradict.

## Adding a part

Other skills add their parts to a project set up with this one. A part adds:

- **A Makefile section**, in this order: `project`, `common`, `templates`, then the parts as they
  come: `registry` (with its nested sections), `docs`, `release`, `codegen`. A section
  uses settings only from sections above it. It starts with its settings, and adds itself to
  `test::`, `generate-all::` and `help::` (double-colon rules, so each section's entries stand
  alone). Removing a part means deleting its section, nothing else.
- **Its pins** in `versions.env`, in a section named for the part, below the weaver pin, each with
  its `# renovate:` line.
- **Its CI jobs**, in a section named for the part, above the aggregate job, and one entry per job
  in the aggregate job's `needs`, tagged with the sections the job belongs to
  (`- test-policies # registry policies`), leaving out an entry with any tag not set up. When
  the project has no CI workflow yet, write it from `assets/project/ci-validation.yaml` first,
  keeping only the sections of the parts set up: without `templates`, that is the aggregate job
  alone, with no `needs` entries until the part adds its own.
- **The `all:` prerequisites** (`ALL_PREREQUISITES`), when what `make` alone should run changes.

A part that installs weaver in a CI job does it the way the base jobs do ("The CI workflow").

## The Makefile

The Makefile is one file, as in the core registry and the other OpenTelemetry registries:

| Section | Targets |
|---|---|
| `project` | `all` (the default goal) |
| `common` | `test`, `generate-all` (aggregators), `install-weaver`, `require-weaver`, `require-jq`, `clean`, `help`, and `RUN_WEAVER` |
| `templates` | `test-templates`, `update-golden` |

Settings a project may change, at the top of their sections:

| Setting | Section | Default | Meaning |
|---|---|---|---|
| `all:` prerequisites | project | token | what `make` alone runs |
| `WEAVER_FLAGS` | common | empty | extra flags for every weaver run, e.g. `--allow-git-credentials` for private registries |
| `TEMPLATES` | templates | `templates` | the templates directory |
| `TEMPLATE_TARGETS` | templates | token | the template targets to test |
| `FIXTURE`, `GOLDEN` | templates | `templates_test/fixture`, `templates_test/golden` | |

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
  new aggregate job's name.
- **Weaver's setup action:** every job that runs weaver installs it with
  `open-telemetry/weaver/.github/actions/setup-weaver`, pinned to the commit of the release
  `versions.env` pins (`gh api repos/open-telemetry/weaver/commits/<tag> --jq .sha`), with that
  version as its `version` input. Bump both together. A job that publishes (a release) passes
  `cache: false`.
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
  this up in a repo whose CI runs actionlint.
- **No path filter:** don't add `paths:` to the workflow. The aggregate job is a required check,
  and a required check that never runs blocks the pull request.

## Copying

With your own tools: `cp` and `rm` for whole files, your editor for the rest; the skill ships no
scripts. Read every copied file before editing it, whether `cp` created it or replaced one you had
read (the repo's old Makefile, say): an editor tool refuses edits to a file it hasn't read since it
last changed, and reading the asset doesn't count as reading the copy.

1. For `core`, and each other part asked for, copy every file under `assets/<part>/` to the same
   relative path in the project, hidden files included, except that `.github/` goes at the repo
   root when the project is in a subdirectory ("Projects in a subdirectory"). Keep file contents
   exact. In a new project at the repo root, a recursive copy (`cp -R assets/<part>/. <project>/`)
   is the simplest way. Otherwise copy file by file: a recursive copy would overwrite the repo's
   own files. Then compare each copy with its asset (`git diff --no-index <asset> <copy>`): only
   tokens, deleted sections and what the Rules keep of the repo's may differ.
2. With `templates`, copy `assets/collections/<collection>/` for each chosen collection the same
   way.
3. Write the project's `Makefile` from `assets/project/Makefile`, and with `templates`
   `.github/workflows/ci-validation.yaml` from `assets/project/ci-validation.yaml`, keeping only
   the sections of the parts set up. Copy the Makefile rather than retyping it: it is indented
   with tabs.
4. Replace every `@@TOKEN@@` (below). Then search the project, hidden files included, for `@@`:
   there must be no matches.
5. With `templates`, run `make update-golden` once the templates are in place, and review the
   golden files.
6. Never overwrite an existing file blindly. Read it first. A base file the repo already has (an
   older copy of an action, the Makefile) takes the asset's content, with the exceptions the
   Rules list: carry over the repo's settings and pins, and keep its own additions. The asset's
   pins, to replace with the repo's: the values in `versions.env` and the pinned SHAs of `uses:`
   lines in the workflows.

## Tokens

| Token | Where | Value |
|---|---|---|
| `PROJECT_DIR` | CI workflow | the project directory relative to the repo root (`.` at the root) |
| `CI_WORKFLOW_NAME` | CI workflow | `CI validation` at the repo root; prefixed in a subdirectory of a repo with its own CI (e.g. `Semconv CI validation`), as "The CI workflow" says |
| `CI_GATE_JOB` | CI workflow | `required-status-check` at the repo root; prefixed the same way in a subdirectory (e.g. `semconv-required-status-check`) |
| `ALL_PREREQUISITES` | Makefile `project` | what `make` alone runs: `test` until a part sets it (e.g. `validate-registry generate-all`) |
| `TEMPLATE_TARGETS` | Makefile `templates` | the template targets the project has, e.g. `markdown`, `$(CODEGEN_TARGET)`, or both |
| `CORE_VERSION` | fixture manifest | the core registry release the project depends on, no `v` (e.g. `1.44.0`) |

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
  every make target. It ships empty; a part may add `[template]` settings, which some templates
  read from this file alone. Any other setting goes on the Makefile's weaver command lines. Its
  cost is a harmless "⚠ Experimental! - Found config" line on every weaver run.
- **`RUN_WEAVER`** (the `common` section). Every weaver run goes through it: it adds
  `WEAVER_FLAGS`, asks for JSON diagnostics, prints them unwrapped (one line per finding, the
  "definition/2 is not yet stable" warnings collapsed into one), fails on imports that match
  nothing, and applies a known violations file when a target gives it one. Weaver wraps its text
  output to the terminal width, so grepping it is unreliable, and it only warns about dead
  imports.
- **The same pinned weaver locally and in CI**: `versions.env` gives the version to both.
- **One aggregate CI job for branch protection**, so adding or renaming a job never requires
  touching the protection rule.

## Projects in a subdirectory

For a project living under, say, `semconv/` in a larger repo (typical for codegen inside an SDK):

- the Makefile, `versions.env`, `.weaver.toml`, `scripts/`, `templates/` and `templates_test/` go
  in the subdirectory;
- `.github/actions/` and `.github/workflows/` must be at the repo root; set `PROJECT_DIR` to the
  project's path;
- prefix the CI workflow's file name, `CI_WORKFLOW_NAME` and `CI_GATE_JOB` with the project's
  directory name ("The CI workflow");
- run weaver only through the project's make targets, or from the project directory: weaver
  applies the first `.weaver.toml` walking up from where it runs, and only the project's own
  empty one keeps a parent directory's out.

## Keeping a project current

To refresh a project, compare each of its base files with `assets/` (and its Makefile and CI
sections with `assets/project/`), bring over what changed, keep the project's settings, and run
SKILL.md step 5.
