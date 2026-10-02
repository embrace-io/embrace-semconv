---
name: otel-semconv-setup
description: Set up or update an OpenTelemetry semantic conventions project with Weaver in a standardized, validated layout. Covers creating a federated registry (OTEP 4815) that extends the core registry or other registries; generating language-specific source code from the core registry alone, from any federated registry (all of it or some of its keys), or from a registry of the project's own conventions, with custom templates; and bringing an existing semconv repo up to the layout (definition/2, validations, release workflow, docs, new registry dependencies). Use when creating a semantic conventions registry, generating code from semantic conventions, adding a registry dependency, or modernizing a weaver-based repo.
---

# OpenTelemetry semantic conventions setup

This skill applies one **canonical layout** for weaver-based semantic convention projects. Its
files are under `assets/`, and you copy them into the project with your own file tools: nothing
beyond what the project needs anyway (weaver, make, jq, git, and OPA when the registry defines
attributes) is required. Everything the project does is a make target, so it works the same for
any language and in CI. The layout is portable: it names no registry besides the core registry.

Read `reference/layout.md` before changing anything, and use the terms in
`reference/glossary.md` in everything you write. The other references are for when a step needs
them:

| Reference | Read it for |
|---|---|
| `reference/layout.md` | every file, how to copy the layout, tokens, settings, required vs convention |
| `reference/glossary.md` | the terms to use, and the ones not to |
| `reference/validations.md` | what each validation catches, known violations, how `validations_test/` proves it |
| `reference/dependencies.md` | declaring and consuming registries: the core registry, federated ones, private ones |
| `reference/templates.md` | what weaver templates see, writing them for any language, the codegen contract |
| `reference/versioning.md` | `schema_url` identity, stability, releases, `-dev` families, baselines |
| `reference/upgrading.md` | updating an existing repo: v1 → `definition/2`, adopting the layout piecemeal |

## Features and collections

The layout is split into **features**. Each is a section of the Makefile and of the CI workflow,
plus the files under `assets/<feature>/`. Two exceptions: `templates` has no directory (its
files are in `assets/common/`), and `codegen` has no files (the project writes its templates).

| Feature | Adds | For |
|---|---|---|
| `common`, `templates` (always) | tool pins, the weaver runner, the template fixture and golden test | every project |
| `registry` | `model/`, validate-registry and validate-dependencies, their invalid registries and `test-validations` | a registry defined in this project, published or not |
| `docs` | the docs templates' shared files, generate-docs, committed `docs/`, the doc skeletons | a registry that documents its conventions |
| `release` | print-version, package, `release.yml`, `RELEASING.md` | a registry published as GitHub releases |
| `codegen` | generate, validate-generated, package-generated | language-specific source generation |
| `renovate` (optional) | `.github/renovate.json5` | a repo that uses Renovate to bump pins and the core registry |

Each kind of convention the project supports is a **collection**: `attributes`,
`attribute-groups`, `events`, `metrics`, `spans`, `entities`. A collection adds a fixture file
and, with `docs`, a docs template and its sections in the docs `weaver.yaml` and README template.
With `registry`, `attributes` also adds the local policy that every attribute is exported by a
public attribute group (`glossary.md`), its tests and OPA, so a registry defining attributes also
needs `attribute-groups`. A registry of only events, say, that references the core registry's
attributes needs neither. Choose at least one collection: a registry has to define something,
and generated code has to contain something. Adding one later is a small, self-contained change
(`reference/upgrading.md`).

## 1. Gather facts first

Ask the user, or look up, rather than assuming:

1. **What they want**: a new registry, a codegen setup, or an update of an existing repo (and
   which parts of an update). Section 2 maps each to features. For codegen, ask whether the
   project defines conventions of its own. Code generated from conventions another registry
   defines (constants for an SDK, say) is a consumer: it doesn't define or validate a registry of
   its own, whether it wants all of that registry or some of its keys.
2. **The repo and where the project lives in it**: the repo root or a subdirectory (an SDK
   module, say), which changes a few settings (`reference/layout.md`, "Projects in a
   subdirectory"). Also: is the repo private (`gh api repos/<owner>/<repo> --jq .private`), and
   is `origin` the canonical repo? It isn't when the repo is a fork, or when `origin` is a
   contributor's fork of the canonical repo (the usual contributor setup). Both change how the
   baseline, the release URLs and the dependencies are fetched (`reference/validations.md`). A
   repo with no remote yet has no tags and no URL: ask the user where it will live, and treat it
   as having no tags until it is pushed.
3. **For a registry**: its registry name (e.g. `example.com/schemas/my-registry`), chosen once
   and never changed, a one-line description, and whether it will be **published** as GitHub
   releases. **By default a new registry starts unstable**: version `0.1.0-dev`, `stability:
   development`, and `stability: development` on every convention it defines. If the user
   explicitly wants it stable from the start, do that instead: `stability: stable`, version
   `1.0.0`, and stable conventions; a stable signal references a less stable attribute only at
   `opt_in` (`reference/versioning.md` explains the trade-off). A stable registry that is never
   published gets no backwards-compatibility validation unless `BASELINE` names a pinned ref:
   say so. In an update, an existing `-dev` version is a `-dev` family
   (`reference/versioning.md`) when the repo says so: a stable counterpart registry exists or is
   planned, or its release tooling refuses versions without the suffix. Otherwise it is unstable.
   Separately, the **default stability for new conventions**, which the docs state: the repo's
   own when its docs say one, or the user's; otherwise `development`, in a stable registry too
   (a stable registry can add conventions at `development` and stabilize them later).
4. **Which collections**: ask which kinds of conventions the registry will define (or, for
   codegen, which kinds the generated code covers), and require at least one. With `registry`,
   add `attribute-groups` whenever `attributes` is chosen. In an update, scan instead:
   `definition/2` files list them under top-level `attributes:`, `attribute_groups:`, `events:`,
   `metrics:`, `spans:` and `entities:`; v1 files as groups of `type: attribute_group`, `event`,
   `metric`, `span` or `resource`. The rule (the only statement of it; `upgrading.md` defers
   here): keep the collections the registry defines, and remove the repo's templates for kinds
   it doesn't define. The exceptions keep what the repo already supports: a registry that
   defines nothing yet, or a user who asks to keep that support. Never add a collection nobody
   asked for, apart from `attribute-groups` with `attributes`.
5. **Existing tags**, for any registry: `git ls-remote --tags <repo-url> 'v*'`. `BASELINE=auto`
   compares with the highest `vX.Y.Z` tag, and the release workflow tags `v<version>`. Use
   `auto` only when the registry is published from this repo and its `v*` tags are the
   registry's own. A `-dev` family never has a baseline: set it empty (with `auto`, a stable
   counterpart released from the same repo would become its baseline; one planned there:
   `reference/versioning.md`, "Pre-releases and `-dev` families"). If the repo tags `v*` for
   anything else (an SDK's releases, another registry), or the registry is unpublished, set
   `BASELINE` to a pinned registry path when there is one to pin: for a registry inside an SDK,
   the latest SDK release tag that contains the registry directory
   (`<repo-url>@<tag>[<registry dir>]`, moved forward after each release; list all tags with
   `git ls-remote --tags <repo-url>`, as an SDK's may have no `v`). The baseline must resolve
   with the pinned weaver: first read the manifest at that tag
   (`git show <tag>:<registry dir>/manifest.yaml`, or `gh api` on the repo's contents at that ref
   when the clone lacks the tag): weaver rejects it unless it and every one of its dependencies
   has a `schema_url` (a dependency with only `name:` fails). If it doesn't, pin the default
   branch's commit that the change is based on (`git merge-base HEAD origin/<default-branch>`)
   until the next release tag has them: a later commit may define conventions the branch
   doesn't have yet, which the comparison reports as removed. Otherwise
   set it empty and tell the user nothing checks compatibility (for a stable registry: until a
   pushed commit can be pinned, `reference/versioning.md`). Before adding
   `release` to such a repo, stop and ask the user how to tell the registry's releases apart (the
   layout has no tag prefix scheme).
6. **Dependencies**: which registries it builds on and at which release. The core registry
   almost always; see `reference/dependencies.md` for finding releases, keeping versions aligned,
   and private registries.
7. **For codegen**: the language, where generated code goes (a directory holding only generated
   code; in an update, look for hand-written files already in it, which each need a template of
   their own), whether it is committed, the source registry, how the platform validates and
   packages code (its compiler, test runner, package format), and whether a build tool already
   runs weaver (`reference/templates.md`, "Platform integration").
8. **Tools**: `weaver --version` must be the pinned version (`assets/common/versions.env`);
   `make install-weaver` installs it. OPA is needed only with the `attributes` collection and
   `registry`; jq always. Look for newer pins, and ask before bumping them:
   `gh api repos/open-telemetry/weaver/releases --jq '.[0].tag_name'`,
   `git ls-remote https://github.com/open-telemetry/opentelemetry-weaver-packages.git HEAD`,
   `gh api repos/open-policy-agent/opa/releases --jq '.[0].tag_name'`, and with `renovate` the
   version the repo's Renovate runs (`reference/layout.md`, "`renovate`"). In an update the repo's
   pins stay as they are unless the user agrees (the layout's files carry the layout's pins:
   keep the repo's values when copying them, and take the layout's only for pins the repo
   doesn't have, except `RENOVATE_VERSION`, chosen as `layout.md`'s `renovate` section says).
   With Renovate, bumps arrive as pull requests from then on. For codegen, also
   check the host's own toolchain pins (e.g. Node `devEngines`, the JDK) against what's
   installed (`reference/templates.md`, "Platform integration").

## 2. Choose the features

| The user wants | Features besides `common` and `templates` |
|---|---|
| A new federated registry, published | `registry`, `docs`, `release` |
| A registry that isn't published, for conventions the project defines (documented or not) | `registry`, and `docs` if it is documented |
| Code generated from one existing registry (the core registry, or a published one), all of it or some of its keys | `codegen` |
| Code generated from a registry of the project's own: conventions it defines, or several registries' conventions combined | `registry`, `codegen` |
| To update an existing repo | whatever it has or should have (see `reference/upgrading.md`) |

Add `renovate` when the repo uses Renovate, or the user wants the pins bumped automatically.

A consumer gets `codegen` alone: `SOURCE_REGISTRY` pins the registry release, and the templates'
filter selects what to generate from it (`reference/templates.md`, "Choosing what to generate"),
so wanting only some keys is no reason for a registry of its own. `registry` + `codegen` is for a
project that defines conventions, or generates from more than one registry at once (a template
sees only what the source registry defines, imports or references); it brings the registry's own
validations. In an update, keep the registry a repo already has.

## 3. Copy the layout

Follow "Copying the layout" in `reference/layout.md`: copy each chosen feature's files from
`assets/<feature>/` (for `templates`, those in `assets/common/`) and each chosen collection's
from `assets/collections/<collection>/`, write the Makefile and CI workflow from
`assets/project/`, keep only the sections of the chosen features and collections, and replace
every `@@TOKEN@@`. Many layout files are dotfiles (`.github/`, `.weaver.toml`, `.gitignore`,
`.gitattributes`): list assets with hidden files shown. Read every file that exists before
replacing it: a layout file takes the layout's content, keeping what the Rules keep of the
repo's, and a prose file is merged (that is most of an update). In an update or a subdirectory
project, copy file by file, not whole trees (`layout.md` says why), except a directory that holds
only layout files, such as `validations_test/`.

## 4. Fill in what the layout can't know

- **Registry**: add `definition/2` files under the registry directory for the project's
  conventions, at the registry's stability (`development` by default), and every dependency to
  its `manifest.yaml` (`reference/dependencies.md`). Every signal (event, metric, span, entity)
  sets its own `requirement_level`, which is `recommended` or `opt_in` (weaver rejects
  `required` there); each attribute reference in a signal takes `required`, `recommended`,
  `opt_in` or `conditionally_required: <when>`. A span also needs `name: {note: …}`. A stable
  signal references a less stable attribute only at `opt_in`. With `attributes`, export every
  attribute through a public attribute group: the local policy requires it.
- **Existing conventions the shared pack rejects** (legacy keys, in an update): never rename a
  published key to get a pass. List the violations in `KNOWN_VIOLATIONS`, and tell the user
  about the migration path that clears them (`reference/validations.md`, "Known violations").
  One is fixed instead: a key deprecated with `renamed_to` a dependency's attribute needs an
  import of a group holding that attribute (`reference/validations.md`), so add the import
  before the first `make validate-registry`.
- **Codegen**: write `templates/registry/<target>/` for the language, covering only the chosen
  collections (`reference/templates.md`), and implement `validate-generated` and
  `package-generated` in the Makefile's codegen section with the platform's own tools. Add the
  toolchain's setup steps to the `validate-generated` CI job, using `actions/*` or local actions.
  Tell the project's developers how to regenerate, in the host project's own docs.
- **Templates test**: once the templates are in place, run `make update-golden` and review every
  golden file: they are the expected output from here on. The layout ships no golden files, since
  they depend on the chosen collections. Golden files of a codegen target are source files of
  that language: keep them out of the host project's build and lint, or make them pass both.
- **Docs** (with `docs`): write README.md, AGENTS.md, CLAUDE.md and CONTRIBUTING.md from the
  skeletons in `assets/project/registry/` (and, with `release`, finish RELEASING.md the same
  way): keep each `<!-- skeleton: only … -->` block whose condition holds, drop the others,
  replace each
  `<!-- skeleton: fill in: … -->` with what it asks for (what the registry is for, its
  namespaces), and remove every marker (`layout.md`, "The doc skeletons"). Where the repo already
  has one of these files, merge instead: keep its text, add what the kept blocks say that it
  lacks, and correct what they contradict.
- **Settings**: set those `reference/layout.md` lists for the project (subdirectory paths,
  `BASELINE`, `KNOWN_VIOLATIONS`, `WEAVER_FLAGS`, `VERSION_SUFFIX`, and `REPO_URL` when `origin`
  isn't the canonical repo, or when contributors work from forks: the Makefile is shared, and a
  fork as `origin` would otherwise put the fork's URL in their local packages).
- **A private repo**, or one that fetches a private registry: keep the workflows' `private`
  sections (they give git the workflow's token through gh's credential helper, never in a URL,
  in every step that fetches), and set
  `WEAVER_FLAGS := --allow-git-credentials` when weaver fetches a private registry (a
  dependency, or the baseline). Never write a token into a git URL or `insteadOf` rule.

## 5. Verify

Don't call the work done until every item below that applies has passed, and say which ones you
ran. Run them from the project directory.

**The files**

1. Nothing left to fill in: searching the project's files (hidden files included, ignored build
   output not, e.g. `rg --hidden --glob '!.git'`) for `@@` and for `<!-- skeleton` finds nothing.
   A project in a subdirectory also searches the repo root's `.github/`, where its workflows and
   actions live, and a `GENERATED_DIR` outside the project. Then run the repo's formatter or
   linter in check mode over the copied files, where it has one, and check them against its
   `.editorconfig`: fix the whitespace the Rules
   keep as the repo's (the layout's `known-violations.json` cases end with a newline, say), and
   say in the hand-over what else it flags in a layout file, which stays as the layout has it.
2. Every sectioned file the project has (the Makefile, `versions.env`, the workflows, the docs
   `weaver.yaml` and `readme.md.j2`) has balanced `==== <name>` / `==== end <name>` lines (the
   Makefile's may carry `: <description>` after the name), and only the always-kept sections
   plus those of the chosen features and collections (and `private`, for a private repo). A
   section nested inside a deleted one is gone with it, even when its own name was chosen.
3. Only the chosen collections' files were copied: the fixture has one file per chosen
   collection, and the docs templates one per chosen collection.
4. `make help` lists the targets of every chosen feature.
5. The docs describe only what the project has: e.g. without `attributes`, a search of the docs
   for `polic`, `OPA` and `opa` matches only the shared policy pack; without `release`, nothing
   describes how this registry is released; the signal kinds mentioned are only those chosen.

**The targets**

6. With `registry`: `make validate-registry`, and with `attributes` also `make test-policies`.
7. With `docs`: `make generate-docs`, then review `docs/`.
8. With `codegen`: `make validate-generated` and `make package-generated`, then read some of the
   generated code yourself.
9. `make test-templates`, and with `registry` also `make test-validations` (every case prints
   `ok:`, proving each validation still fails on the invalid registry it exists for).
10. With `release`: `make print-version` prints the manifest's version, and `make package`
    succeeds.

**In an update, also**

11. Every validation and test the repo had before the update still passes, or fails only where
    the update was meant to change it.
12. Generated docs and code are unchanged unless the update was meant to change them: regenerate
    and compare with what was committed (`git diff`, plus `git status` for new files), and account
    for every difference. With `release`, compare `make package`'s output with the copy made
    before the update (`upgrading.md`, "Inventory first"): no output from
    `git diff --no-index <before> .build/package` means the update needs no release. So does a
    difference only in `manifest.yaml`'s `resolved_registry_uri` when the old tooling read a
    fork's `origin` and the update set `REPO_URL` to the canonical repo: releases are built in
    the canonical repo, where `origin` is that repo, so the published manifests already name it.

**CI**

13. The CI workflow keeps exactly the chosen sections and `needs` entries. Check the workflows
    with zizmor only when the repo uses it (a workflow of its own runs it, or its rulesets'
    `code_scanning` rule names it); otherwise skip it. Run it the way the repo's CI does (the same
    persona). When zizmor isn't installed, ask the user whether to run it through uv
    (`uv tool run zizmor --offline --persona <persona> .github` from the repo root installs
    nothing; `--offline` leaves out the audits that need a GitHub token, which CI runs), and run
    it only if they agree and uv is installed: no other way of getting zizmor (pip, pipx, a
    scratch environment). Say in the hand-over whether it ran. A private repo on GitHub Free has
    no rulesets (the API returns 403, "Upgrade to GitHub Pro or make this repository public"), so
    nothing gates it. Either
    way, the first CI run (item 14) is the check that the workflows run. With `renovate`,
    validate the config and check that Renovate extracts every `# renovate:` pin
    (`reference/layout.md`, "`renovate`").
14. Local runs can't show CI-only problems (a missing toolchain step, a wrong working directory).
    Once the user has pushed the change, watch the first run (`gh run watch`) and fix what fails.

## 6. Hand over

Tell the user what was created or changed, what each make target does, which step 5 items ran
and their results, and what is left for a human: requiring the CI aggregate job
(`CI_GATE_JOB`, `required-status-check` by default) in branch protection, which a private repo
has only on a paid GitHub plan (on GitHub Free, say so instead); with `release`, making
the first release (`RELEASING.md`); committing generated docs or code; for an unstable registry,
graduating to stable when they're ready; any known violations and their migration; and any
platform decisions you made in
`validate-generated` / `package-generated`.

## Rules

- Never replace a file in the user's repo without reading it first: layout files as below,
  prose files merged.
- Name neither this skill nor "the layout" in what you write into the repo (docs, comments,
  commit-ready text), even when the user's request does: its readers can't follow either.
- Keep the layout's files identical to `assets/`: the Makefile's targets, the actions, the
  workflows' steps, the policy, the fixture and the invalid registries. Project choices go in the
  settings at the top of each Makefile section and in the tokens. A layout file the repo already
  has takes the layout's content, except for what stays the repo's:
  - its pins: the values in `versions.env` and the pinned action SHAs (bump them only with the
    user's agreement);
  - its own additions: extra CI steps and jobs, extra targets outside the layout's sections,
    `# renovate:` annotations, comments pairing a pin with another copy of it, the description
    of an action other repos use;
  - the prose of the docs templates (e.g. the intro paragraph of `readme.md.j2`);
  - the repo's formatting rules for the file types it formats (`.editorconfig`, a formatter
    config), as whitespace: a JSON file without a final newline, say. A layout line longer than
    the repo allows stays as it is.

  When the layout itself must change, change it in this skill and say so.
- Use the glossary's terms, and never the ones it rules out.
- Never add third-party GitHub Actions: the layout uses `actions/*` and local actions only, which
  also satisfies organizations that allowlist actions. Replace a repo's third-party setup action
  with its `actions/*` equivalent where one exists.
- Don't pull policies from dependency repos into `validate-registry` (`reference/validations.md`
  explains why); shared rules come from the pinned shared policy pack.
- Never rename a key, signal name or group ID that consumers use to get a validation to pass.
