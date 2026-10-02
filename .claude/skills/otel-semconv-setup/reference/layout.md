# The canonical layout

A project's files come from three places:

- `assets/<feature>/`, copied to the same paths in the project. `common` also holds the
  `templates` feature's files; `codegen` has no files of its own.
- `assets/collections/<collection>/<feature>/`, the same, for each chosen collection and each
  chosen feature it has files for.
- `assets/project/`: the Makefile and CI workflow, cut down to the project's features and
  collections, and the doc skeletons (README.md, AGENTS.md, CLAUDE.md, CONTRIBUTING.md).

The assets carry no mark of where they came from (a repo's readers couldn't follow one), so a
repo's layout files are the ones at the paths the assets have: tell them from the repo's own
files, and see whether a copy is current, by comparing each with its asset. Many of the files
are dotfiles (`.github/`,
`.weaver.toml`, `.gitignore`, `.gitattributes`), so list the assets with hidden files shown.

## Files by feature

### `common` and `templates` (always)

```
versions.env                         weaver pin; with `registry`, the shared policy pack pin and
                                     (with `attributes`) the OPA pin, in sections
.weaver.toml                         deliberately empty (see below)
.gitignore                           build output, editor and OS noise
templates_test/fixture/manifest.yaml the fixture registry's manifest; its definitions come from the
                                     chosen collections
.github/actions/setup-weaver/        installs pinned weaver (install script shared with make)
.github/actions/assert-no-drift/     fails when committed generated files differ from a regeneration
                                     (used with `docs` and with committed generated code)
```

The install scripts are run with `bash <script>`, so they work whether or not the copy kept their
executable bit.

Plus `templates_test/golden/<target>/`, the expected output of each template target, made with
`make update-golden` (the layout ships none: they depend on the chosen collections).

### `registry` (a registry defined and validated here, published or not)

```
model/manifest.yaml                  schema_url (registry name + version), dependencies
model/<area>/*.yaml                  the conventions, in definition/2 files (written by you)
validations_test/test-templates/     an import that matches nothing
validations_test/validate-dependencies/   version conflicts, schema_url/registry_path mismatches
validations_test/validate-registry/  shared policy pack, baseline, unmatched import, known
                                     violations (only listed ones pass; stale ones fail)
validations_test/registries/         dependencies and baselines the cases share (not cases)
```

The `validations_test/` cases are the registry's own tests of its validations, run by
`make test-validations`: a project without `registry` has neither.

### `docs`

```
templates/registry/markdown/weaver.yaml   one section per collection, and the README filter
templates/registry/markdown/readme.md.j2  the docs README, one section per collection
templates/registry/markdown/macros.j2     the table-cell helpers the collections' docs templates import
.gitattributes                       marks docs/ as generated
```

plus the doc skeletons from `assets/project/registry/`.

### `release`

```
.github/workflows/release.yml        publishes a human-prepared draft release, from the default
                                     branch only
RELEASING.md                         the release process
```

### `codegen`

No files of its own: the language's templates in `templates/registry/<target>/` are written for
the project (`templates.md`).

### `renovate` (optional)

```
.github/renovate.json5               bumps versions.env's pins, the core registry dependency in
                                     the manifest and the fixture, and the pinned actions
```

The `# renovate:` comments it reads are already in `versions.env` and the manifests; without
Renovate they do nothing. Each must stay directly above the lines its match string reads (the
pin, or for the policy pack `POLICY_REPO_URL` then `POLICY_REPO_REF`): nothing may come in
between, so put any other comment (a pairing note, say) above the `# renovate:` line. Needs the Renovate GitHub app on the repo. Dependabot can't bump these
pins (env-file values, a git commit). The file's header says how to adapt it:

- Renovate reads one config file: a repo that already has one gets the layout's
  `customManagers` and `packageRules` merged into it, and no second file. Its own `extends` and
  `labels` stay as they are: the layout's would change every Renovate pull request in the repo.
  A plain `.json` config can't hold the asset's `//` comments: carry what they say in the
  `description` of the custom manager or rule they sit in (a match string has none of its own).
- A repo that already bumps the core registry another way (a scheduled workflow) keeps that, and
  leaves out the manifest match strings, the `manifest.yaml` file pattern and the `core registry`
  rule, which would describe a bump Renovate never makes there (the manifests' `# renovate:`
  comments can stay: nothing reads them).
- A codegen project pinning `SOURCE_REGISTRY` to a release adds a `# renovate:` line above it.
  Without a registry of its own, it deletes the fixture manifest's `# renovate:` line (the
  fixture's core registry then moves with `SOURCE_REGISTRY`, by hand).
- Otherwise keep every match string and rule, even those that match nothing in this project (a
  codegen project has no registry manifest, say): one that matches nothing does nothing. Where
  the repo's config already has a rule for the same dependencies (its own GitHub Actions group,
  say), keep the repo's.
- Run Renovate at the version `versions.env` pins (`RENOVATE_VERSION`, the `renovate` section),
  never `@latest`: a new release can break a working repo (one was published that npm can't
  install). Choose the pin at setup, the first of:
  1. The version the repo already gives Renovate (a self-hosted Renovate workflow's version
     input, a `renovate` dev dependency).
  2. With the hosted Renovate app, the version it last ran: the `renovate-debug` footer of its
     most recently updated pull request names it. This prints it, and nothing when the app hasn't
     opened a pull request yet:

     ```bash
     gh pr list --repo <owner>/<repo> --state all --limit 1 --search 'author:app/renovate sort:updated-desc' --json body --jq '.[0].body // "" | capture("renovate-debug:(?<f>[A-Za-z0-9+/=]+)").f | @base64d | fromjson | .updatedInVer // .createdInVer'
     ```

  3. The newest release that installs: `npm view renovate version`, then
     `npx --yes --package=renovate@<version> -- renovate --version`; if it fails, work back
     through earlier releases until one installs (a release npm can't install may stop with only
     "A complete log of this run can be found in" and no error).

  The pin keeps its `# renovate:` line, so Renovate bumps it like the other pins. The commands
  below take the pin as `<RENOVATE_VERSION>`. Validate the config with
  `npx --yes --package=renovate@<RENOVATE_VERSION> -- renovate-config-validator --no-global <config file>`.
  Without `--no-global`, a config named by path is validated as Renovate's global config, not a
  repo's. A warning that the `re2` module can't be loaded (not found, or built for another Node
  version) is harmless: the validator falls back to JavaScript regexes.
- Check the repo's own config validator too (a workflow running `renovate-config-validator`); the
  layout adds none. Make it validate with the version the repo's Renovate runs: a self-hosted
  one's version as given, or for the hosted app the footer's, read the same way, falling back to
  the pin when there is none. Run it with `--no-global`. Have the workflow run when that
  `versions.env` changes, not only the config: the pin is what it falls back to. For the hosted
  app, the step (a private repo's job also needs `pull-requests: read`):

  ```yaml
        - name: Validate the Renovate config
          env:
            GH_TOKEN: ${{ github.token }}
            GH_REPO: ${{ github.repository }}
          run: |
            source <project dir>/versions.env
            version="$(gh pr list --state all --limit 1 --search 'author:app/renovate sort:updated-desc' --json body --jq '.[0].body // "" | capture("renovate-debug:(?<f>[A-Za-z0-9+/=]+)").f | @base64d | fromjson | .updatedInVer // .createdInVer' || true)"
            if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then version="$RENOVATE_VERSION"; fi
            echo "Validating with Renovate $version"
            npx --yes --package="renovate@${version}" -- renovate-config-validator --no-global <config file>
  ```

  An unversioned `renovate` there
  (`npx --package=renovate`) gets the newest release whose `engines` allow the job's Node, and on
  a Node newer than the latest Renovate supports that is an old one (Renovate 37 on Node 26),
  which rejects the config with "Custom Manager contains disallowed fields: managerFilePatterns";
  `@latest` takes whatever was published last. npm installs a pinned version on any Node, with
  only an engine warning. Use `fileMatch` (the same patterns, without the slashes) in place of
  `managerFilePatterns` only where a validator stays pinned to an old Renovate: the current one
  reports `fileMatch` as a needed config migration.
- A valid config can still miss a pin. Check what Renovate reads by running its extraction from
  the repo root, with the Node the repo requires, which `npx` there may enforce
  (`reference/templates.md`, "Platform integration"). It reads the repo's config and the files
  git tracks, changes nothing and looks nothing up, so it needs no token. An untracked file is
  invisible to it, so a new setup's files must be staged first (`git add`; no commit needed), or,
  where the index must stay as it is, copy the config and the pinned files into a scratch
  `git init` repo, `git add` them there and run it in that:

  ```bash
  npx --yes --package=renovate@<RENOVATE_VERSION> -- renovate --platform=local --dry-run=extract \
    --report-type=file --report-path=<scratch dir>/renovate-report.json \
    > <scratch dir>/renovate.log 2>&1
  jq -r '.repositories[].packageFiles.regex[]? | .packageFile as $file | .deps[]
    | "\($file) \(.depName) \(.currentValue)"' <scratch dir>/renovate-report.json
  ```

  Every `# renovate:` line in the project's files must show up there, under its file and
  `depName`, except the manifests' when the repo bumps the core registry another way (their
  match strings are left out, above); any other missing one is a pin no match string fits.
  Renovate supports one Node line (the `engines` of its package.json): on a newer Node it logs
  "Unsupported node environment detected" and exits non-zero, but still writes the report, so
  judge by the report.

### Collections

Each kind of convention is a collection under `assets/collections/<collection>/`: `attributes`,
`attribute-groups`, `events`, `metrics`, `spans` and `entities`. Choose at least one. Each has:

```
common/templates_test/fixture/fixture/<collection>.yaml
                                     a fixture definition, so the templates for it are exercised
docs/templates/registry/markdown/<collection>.md.j2
                                     its docs page, with the docs feature
```

The attributes fixture defines the fixture's own attributes (a string with a note, an enum, a
deprecated attribute and a long key) and exports them through its own public group,
`registry.fixture.defined`. The other fixtures reference the core registry's attributes, so any
combination of collections resolves. Each fixture imports its kind from the core registry where
it has some, so the templates' provenance filters have something to filter out.

A collection also has a section in the docs `weaver.yaml` (its page's entry, and its part of the
README filter) and in `readme.md.j2`. Codegen templates for a collection are the project's own.

`attributes` also has `registry/` files, since only a registry that defines attributes needs
them:

```
policies/check/public-attribute-groups/   local policy: every attribute the registry defines is
                                          exported by a public attribute group
policies_test/                       its OPA unit tests (100% coverage required)
validations_test/validate-registry/local-policy-rejects-unexported-attribute/
                                     proves the local policy runs
.github/actions/setup-opa/           installs pinned OPA
```

The policy's helpers are in a rego package named after the registry (`@@POLICY_PACKAGE@@`), so
they can't collide with the shared policy pack's; see `validations.md`. With `registry`,
`attributes` requires `attribute-groups`: the policy needs a group to export each attribute.

### `assets/project/`

```
Makefile                             one file, one section per feature (see below)
ci-validation.yaml                   → .github/workflows/ci-validation.yaml, one section per feature
registry/README.md, AGENTS.md, CLAUDE.md, CONTRIBUTING.md   → the project root, with `docs`
```

## Sectioned files

Six files have sections to keep or delete: the Makefile, `versions.env`, the CI and release
workflows, and the docs `weaver.yaml` and `readme.md.j2`.

- **Where a section runs:** from a `# ==== <name>` line to its `# ==== end <name>` line. In the
  Jinja file the lines are `{#- ==== <name> #}` and `{#- ==== end <name> #}`, and the Makefile's
  start lines may carry a description after the name (`# ==== common: tool pins …`).
- **What a name is:** a feature, a collection, `project`, or `private`.
- **What to keep:** `project`, `common` and `templates` always; `private` only for a private
  repo, or one whose weaver runs fetch a private registry (a dependency, the source registry);
  every other section only when its feature or collection is chosen.
- **Nesting:** sections can nest. `attributes` sections sit inside `registry` sections, so
  deleting `registry` deletes them too.

## The doc skeletons

README.md, AGENTS.md and CONTRIBUTING.md (and `release`'s RELEASING.md; CLAUDE.md has no markers
and is copied as is) are prose, not
sectioned. They carry two kinds of markers:

- **Conditional blocks**, between `<!-- skeleton: only … -->` and `<!-- skeleton: end -->`, apply
  to some projects only. Keep a block's text when its condition holds, drop it otherwise, and
  remove the markers either way. Blocks can nest (an `end` closes the innermost open block), and
  can sit inside code blocks. The conditions:
  - **stability**, exactly one of: "unstable" (the default: `0.x.0-dev` versions until the
    registry graduates to stable), "stable" (stable from the start, or graduated), or "`-dev`
    family" (every version carries `-dev` for good, `VERSION_SUFFIX := -dev`); a block naming
    two of them (`"unstable" (the default) or "stable"`) holds when either does;
  - with or without `release` (published or not), and "when `BASELINE` is set" (`auto` or a
    pinned path) or empty;
  - a collection being chosen, "a private repo", "when `KNOWN_VIOLATIONS` is set".
- **`<!-- skeleton: fill in: … -->`** is replaced by the text it asks for: what the registry is
  for, its namespaces.

When done, no `<!-- skeleton` is left. The skeletons link `model/`: adjust the paths when `MODEL`
differs. In a repo that already has these files, merge what's useful into them instead.

## The Makefile

The Makefile is one file, as in the core registry and the other OpenTelemetry registries:

| Section | Targets |
|---|---|
| `project` | `all` (the default goal) |
| `common` | `test`, `generate-all` (aggregators), `install-weaver`, `require-weaver`, `require-jq`, `clean`, `help`, and `RUN_WEAVER` |
| `templates` | `test-templates`, `update-golden` |
| `registry` | `validate-registry`, `validate-dependencies`, `test-validations`; nested `attributes`: `test-policies`, `install-opa`, `require-opa` |
| `docs` | `generate-docs` |
| `release` | `print-version`, `package` |
| `codegen` | `generate`, and the project-implemented `validate-generated`, `package-generated` |

Each section starts with its settings and adds itself to `test::`, `generate-all::` and `help::`
(double-colon rules, so each section's entries stand alone). Removing a feature means deleting its
section, nothing else. Sections depend on earlier ones (`registry` uses `FIXTURE` and `TEMPLATES`
from `templates`; `docs` and `release` use `MODEL` from `registry`), so keep them in order.

Settings a project may change, at the top of their sections:

| Setting | Section | Default | Meaning |
|---|---|---|---|
| `all:` prerequisites | project | token | e.g. `validate-registry generate-all`, or `validate-generated` |
| `ACTIONS_DIR` | common | the git root's `.github/actions` (`./.github/actions` outside git) | where the setup-* actions are; set it only when they live elsewhere (a project inside a git submodule) |
| `WEAVER_FLAGS` | common | empty | extra flags for every weaver run, e.g. `--allow-git-credentials` for private registries |
| `TEMPLATES` | templates | `templates` | the templates directory |
| `TEMPLATE_TARGETS` | templates | token | `markdown`, the codegen target, or both |
| `FIXTURE`, `GOLDEN` | templates | `templates_test/fixture`, `templates_test/golden` | |
| `MODEL` | registry | `model` | the registry directory (its `manifest.yaml` sits directly inside) |
| `MODEL_REPO_PATH` | registry | `$(MODEL)` | that directory's path within the repo, for the baseline |
| `REGISTRIES` | registry | `$(MODEL) $(FIXTURE)` | registries whose dependency trees are verified |
| `REPO_URL` | registry | from `origin` | the repo's GitHub URL (read raw, credentials stripped), for release URLs and the baseline's tags; set it to the canonical repo when `origin` isn't (a fork, or a contributor's fork as `origin`) |
| `LOCAL_POLICIES` | registry | empty; `attributes` adds the public-attribute-groups policy | local policy directories |
| `BASELINE` | registry | token | `auto` (the highest `vX.Y.Z` tag of `REPO_URL`), a registry path, or empty |
| `KNOWN_VIOLATIONS` | registry | empty | a JSON file of accepted shared-pack violations, by convention `known-violations.json` next to the Makefile (`validations.md`) |
| `DOCS_DIR` | docs | `docs` | emptied and regenerated each run |
| `VERSION_SUFFIX` | release | empty | a suffix every version must end with, e.g. `-dev` for a `-dev` family |
| `SOURCE_REGISTRY` | codegen | token | registry the code is generated from |
| `CODEGEN_TARGET`, `GENERATED_DIR` | codegen | tokens | template target; output directory, emptied each run |

Any of them can also be overridden on the command line (`make validate-registry BASELINE=`).

## The CI workflow

`ci-validation.yaml` has the same sections around its jobs. Its aggregate job (`CI_GATE_JOB`,
`required-status-check` by default) tags each `needs` entry with the sections its job belongs to
(`- test-policies # registry attributes`). Delete an entry when any of its tags isn't chosen.

- **The aggregate job:** branch protection names a check by the job's `name:`. So the aggregate
  job's name equals its ID and must be unique among the repo's workflows.
- **Names in a host repo:** a project at the repo root uses the defaults (`ci-validation.yaml`,
  `CI validation`, `required-status-check`). A project in a subdirectory of a repo with its own
  CI (an SDK module, say) prefixes all three with its directory name: e.g.
  `semconv-ci-validation.yaml`, `Semconv CI validation`, `semconv-required-status-check`.
- **Superseded workflows:** a workflow that the layout's replaces (an older validation or
  drift-check workflow, a separate dev release workflow) is deleted in the same change, and
  branch protection is told about the new aggregate job's name.
- **Local actions:** the workflows call the layout's actions as `uses: $/.github/actions/…`,
  GitHub's self-repository syntax. It resolves to the repository at the commit that is running,
  with no checkout, and needs runner 2.336.0 or newer (GitHub-hosted runners have it). zizmor
  1.30 and later report every `uses: ./…` as `help[self-repository]` in all its personas, and a
  repo whose rules block on every zizmor alert can't merge them; `$/…` has no finding. actionlint
  1.7.12 rejects `$/…` ("invalid format because ref is missing"), so tell
  the user before adopting the layout in a repo whose CI runs actionlint.
- **No path filter:** don't add `paths:` to the workflow. The aggregate job is a required check,
  and a required check that never runs blocks the pull request.

## Copying the layout

With your own tools: `cp` and `rm` for whole files, your editor for the rest; the layout ships
no scripts. A long section to delete (a codegen-only project drops some 400 Makefile lines) may
go with a throwaway script of your own that removes the lines between its markers: the diff with
the asset (step 1) shows what it removed. Read every copied file before editing it, whether `cp`
created it or replaced one you had read (the repo's old Makefile, say): an editor tool refuses
edits to a file it hasn't read since it last changed, and reading the asset doesn't count as
reading the copy.

1. For each chosen feature, including `common`, copy every file under `assets/<feature>/` to the
   same relative path in the project, hidden files included, except that `.github/` goes at the
   repo root when the project is in a subdirectory ("Projects in a subdirectory"). Keep file
   contents exact. In a new project at the repo root, a recursive copy
   (`cp -R assets/<feature>/. <project>/`) is the simplest way. Otherwise copy file by file: in
   an update, a recursive copy would overwrite the repo's files (`model/manifest.yaml` among
   them), which step 8 handles instead; a directory holding only layout files (e.g.
   `validations_test/`) can still be copied whole, but a copy over the repo's older one keeps
   files the layout no longer has: afterwards, delete those, keeping only the repo's own
   additions (a case of its own, say). Then edit the tokens, and compare each copy
   with its asset (`git diff --no-index <asset> <copy>`): only tokens, deleted sections, edits
   these steps call for (e.g. the fixture manifest's `# renovate:` line, deleted in a codegen
   project) and what SKILL.md's Rules keep of the repo's (its pins, its own additions, its
   formatting rules) may differ. Copy the Makefile and the rego files rather than retyping
   them: they are indented with tabs. `assert-no-drift` is needed only with `docs` or committed
   generated code; delete it when neither applies.
2. For each chosen collection, copy `assets/collections/<collection>/<feature>/` for each chosen
   feature it has files for (`common` always; `docs` and `registry` when chosen) the same way.
3. Write the project's `Makefile` from `assets/project/Makefile` and
   `.github/workflows/ci-validation.yaml` from `assets/project/ci-validation.yaml`.
4. In every sectioned file, keep `project`, `common` and `templates`, delete every other section
   whose name is neither a chosen feature nor a chosen collection, and delete the CI `needs`
   entries with such a tag. Only where a section was deleted: if that leaves two blank lines in
   a row, keep one; if it leaves one at the end of the file, right after a block's opening line
   (e.g. `templates:`) or right before a section's end line, remove it. Blank lines anywhere else
   are the asset's and stay.
   The README filter's sections are jq comments inside a literal block,
   and each adds its own key, so deleting any of them leaves valid jq.
5. With `docs`, write README.md, AGENTS.md, CLAUDE.md and CONTRIBUTING.md from the skeletons
   ("The doc skeletons" above).
6. Replace every `@@TOKEN@@` (below). Then search the project, hidden files included, for `@@`
   and `<!-- skeleton`: there must be no matches.
7. Run `make update-golden` once the templates are in place, and review the golden files.
8. Never overwrite an existing file blindly. Read it first. A layout file the repo already has
   (an older copy of an action, the Makefile) takes the layout's content, with the exceptions
   SKILL.md's Rules list: carry over the repo's settings and pins, and keep its own additions.
   The layout's pins, to replace with the repo's: the values in `versions.env` and the pinned
   SHAs of `uses:` lines in the workflows. Prose files (README.md and the like) are merged.

## Tokens

| Token | Where | Value |
|---|---|---|
| `SCHEMA_URL` | `model/manifest.yaml` | the registry URL plus its first version: `0.1.0-dev`, or `1.0.0` for a registry stable from the start (e.g. `https://example.com/schemas/my-registry/0.1.0-dev`) |
| `REGISTRY_STABILITY` | `model/manifest.yaml` | `development` unless the user asks for `stable` (`versioning.md`) |
| `REGISTRY_DESCRIPTION` | manifest, README, AGENTS | one line |
| `REGISTRY_URL` | README (in its `release` block) | the registry URL: `SCHEMA_URL` without its version (glossary) |
| `POLICY_PACKAGE` | the local policy (`attributes`) | the registry name in reverse-DNS order, dotted, with anything that isn't a letter, digit or `_` turned into `_` (e.g. `example.com/schemas/my-registry` → `com.example.schemas.my_registry`) |
| `PROJECT_NAME` | README, AGENTS | human title |
| `REPO_URL` | README (in its `release` block), RELEASING | `https://github.com/<owner>/<repo>`, the canonical repo; ask when the repo has no remote yet |
| `CORE_VERSION` | manifest, fixture, `validations_test/` | the core registry release depended on, no `v` (e.g. `1.44.0`) |
| `CORE_OLDER_VERSION` | `validations_test/` (`registry`) | any earlier core registry release (e.g. `1.43.0`) |
| `BASELINE` | Makefile `registry` | `auto` for a registry published from this repo as `vX.Y.Z` tags; otherwise (a `-dev` family included) empty, or a pinned registry path (SKILL.md step 1) |
| `PROJECT_DIR` | CI and release workflows | the project directory relative to the repo root (`.` at the root) |
| `DOCS_REPO_PATH` | CI (`docs`) | the docs directory relative to the repo root: `docs`, or e.g. `semconv/docs` |
| `GENERATED_REPO_PATH` | CI (`codegen`) | `GENERATED_DIR` relative to the repo root, normalized (no `..`): e.g. `packages/sdk/src/generated` |
| `CI_WORKFLOW_NAME` | CI, README, AGENTS, RELEASING | `CI validation` at the repo root; prefixed in a subdirectory of a repo with its own CI (e.g. `Semconv CI validation`), as "The CI workflow" says |
| `CI_GATE_JOB` | CI | `required-status-check` at the repo root; prefixed the same way in a subdirectory (e.g. `semconv-required-status-check`) |
| `ALL_PREREQUISITES` | Makefile `project` | what `make` alone runs, e.g. `validate-registry generate-all` |
| `TEMPLATE_TARGETS` | Makefile `templates` | `markdown`, `$(CODEGEN_TARGET)`, or `markdown $(CODEGEN_TARGET)` |
| `LANGUAGE`, `SOURCE_REGISTRY`, `CODEGEN_TARGET`, `GENERATED_DIR` | Makefile `codegen`, CI | see the codegen section's comments |

## What is required and what is convention

Weaver requires only some of the layout's choices. Keep the conventions anyway: they make every
registry look alike, and consumers write the same paths for all of them.

| Choice | Required by weaver? | Notes |
|---|---|---|
| `manifest.yaml`, exactly that name, directly in the registry directory | **yes** | `manifest.yml` is parsed as a definition file and fails; one in a subdirectory isn't found, so no dependencies load |
| definition files anywhere under the registry directory, `.yaml` or `.yml` | yes (any depth) | file and directory names are organizational only; weaver merges them all |
| the registry directory named `model/` | no | the core registry and every federated registry use it; consumers then write `…@<tag>[model]`. An existing project can keep its path with `MODEL` |
| `/schemas/` in `schema_url` | no | weaver needs only the last segment to be the version; OTEP 4815's pattern is `https://<domain>/schemas/<name>/<version>` |
| `templates/registry/<target>/` | `registry/` is weaver's documented layout | weaver falls back to `templates/<target>/` only when `registry/<target>/` is missing, undocumented; if both exist the other is silently ignored |
| `templates/` as the templates directory | no | weaver's default for `--templates`; an existing project can keep its path with `TEMPLATES` |
| `visibility: public` on the groups that export attributes | **yes**, for templates and consumers | internal groups are dropped at resolution |
| group IDs `registry.<namespace>` (or `registry.<namespace>.<area>`) | no, only unique | the core registry and federated registries use it; IDs are public API |
| `v` prefix on release tags | no | the release tooling assumes it; `registry_path` pins `@v<version>` |

## Things every project gets, and why

- **`.weaver.toml`, empty.** Weaver applies the first `.weaver.toml` it finds walking up from the
  working directory. Without one here, a stray file in a parent directory could skip policies or
  redirect dependencies (`[resolve.schema_url_overrides]`) for every make target. Its cost is a
  harmless "⚠ Experimental! - Found config" line on every weaver run.
- **`RUN_WEAVER`** (the `common` section). Every weaver run goes through it: it adds
  `WEAVER_FLAGS`, asks for JSON diagnostics, prints them unwrapped (one line per finding, the
  "definition/2 is not yet stable" warnings collapsed into one), fails on imports that match
  nothing, and applies `KNOWN_VIOLATIONS`. Weaver wraps its text output to the terminal width,
  so grepping it is unreliable, and it only warns about dead imports.
- **Install scripts shared by make and CI**, so local and CI tools are the same pinned versions.
- **One aggregate CI job for branch protection**, so adding or renaming a job never requires
  touching the protection rule.

## Projects in a subdirectory

For a project living under, say, `semconv/` in a larger repo (typical for codegen inside an SDK):

- the Makefile, `versions.env`, `.weaver.toml`, `templates/`, `templates_test/`, and with
  `registry` `model/` and `validations_test/`, go in the subdirectory;
- `.github/actions/` and `.github/workflows/` must be at the repo root. The Makefile finds the
  actions there through git (`ACTIONS_DIR`, no setting needed); set `PROJECT_DIR` to the
  project's path;
- the CI paths are repo-relative: `DOCS_REPO_PATH` (`semconv/docs`) and `GENERATED_REPO_PATH`
  (normalized, even when `GENERATED_DIR` climbs out of the project with `..`);
- with `registry`, set `MODEL_REPO_PATH := semconv/model` so the baseline registry path is right;
- `.gitattributes` patterns are relative to the file's directory, so put it next to `docs/`;
- the repo's `v*` tags are usually the host project's: set `BASELINE` accordingly (SKILL.md
  step 1), and with `release`, ask the user before the registry releases;
- prefix the CI workflow's file name, `CI_WORKFLOW_NAME` and `CI_GATE_JOB` with the project's
  directory name ("The CI workflow");
- run weaver only through the project's make targets, or from the project directory: weaver
  applies the first `.weaver.toml` walking up from where it runs, and only the project's own
  empty one keeps a parent directory's out.

## Keeping a project current

To refresh a project, compare each of its layout files with `assets/` (and its Makefile and CI
sections with `assets/project/`), bring over what changed, keep the project's settings, and run
SKILL.md step 5.
