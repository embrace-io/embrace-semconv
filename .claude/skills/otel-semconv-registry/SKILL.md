---
name: otel-semconv-registry
description: Create or update an OpenTelemetry semantic conventions registry validated with Weaver - a federated registry (OTEP 4815) that extends the core registry or other registries, in definition/2 files - with make targets that validate its dependency tree, schema, the shared OpenTelemetry policy pack, optional local policies (with unit tests) and backwards compatibility against a baseline, known violations for legacy keys, invalid registries that prove each validation still fails, and CI jobs for all of it. Builds on the otel-semconv-base skill. Use when creating a semantic conventions registry, adding a registry dependency, defining new conventions in one, or validating an existing weaver registry.
---

# A semantic conventions registry

This skill adds a registry to a project set up with the otel-semconv-base skill: the registry
directory (`model/`), the make targets that validate it, the invalid registries that prove those
validations still fail, and their CI jobs. Docs, releases, generated code and Renovate are other
skills' parts, added on top. Read the base skill's `reference/layout.md` ("Adding a part") and
this skill's `reference/part.md` before changing anything, and use the terms in the base skill's
`reference/glossary.md`.

| Reference | Read it for |
|---|---|
| `reference/part.md` | the part's files, where they go, collections, settings, tokens |
| `reference/validations.md` | what each validation catches, the baseline, known violations, policies |
| `reference/dependencies.md` | declaring registries the registry builds on: the core registry, federated ones, private ones |
| `reference/versioning.md` | `schema_url` identity, stability, `-dev` families |

## When this is the wrong tool

A project that only uses another registry's conventions doesn't need a registry of its own: it
uses its language's published package for the core registry (the otel-semconv-consume skill), or
generates code straight from the registry it uses (the otel-semconv-codegen skill), all of it or
some of its keys. A registry of its own is for conventions it defines, or for combining several
registries' conventions in one place.

## 1. Gather facts first

Ask the user, or look up, rather than assuming:

1. **The repo and where the project lives in it** (the base skill's step 1), whether the repo is
   private, and whether `origin` is the canonical repo. It isn't when the repo is a fork, or when
   `origin` is a contributor's fork of the canonical repo. Both change how the baseline and the
   dependencies are fetched (`reference/validations.md`). A repo with no remote yet has no tags
   and no URL: ask the user where it will live, and treat it as having no tags until it is pushed.
2. **The registry**: its registry name (e.g. `example.com/schemas/my-registry`), chosen once and
   never changed, a one-line description, and whether it will be published as GitHub releases.
   **By default a new registry starts unstable**: version `0.1.0-dev`, `stability: development`,
   and `stability: development` on every convention it defines. If the user explicitly wants it
   stable from the start, do that instead: `stability: stable`, version `1.0.0`, and stable
   conventions; a stable signal references a less stable attribute only at `opt_in`
   (`reference/versioning.md` explains the trade-off). A stable registry that is never published
   gets no backwards-compatibility validation unless `BASELINE` names a pinned ref: say so. In an
   update, an existing `-dev` version is a `-dev` family (`reference/versioning.md`) when the repo
   says so: a stable counterpart registry exists or is planned, or its release tooling refuses
   versions without the suffix. Otherwise it is unstable. Separately, the **default stability for
   new conventions**: the repo's own when its docs say one, or the user's; otherwise
   `development`, in a stable registry too.
3. **Which collections**: ask which kinds of conventions the registry will define, and require at
   least one. In an update, scan instead: `definition/2` files list them under top-level
   `attributes:`, `attribute_groups:`, `events:`, `metrics:`, `spans:` and `entities:`. Keep the
   collections the registry defines. Never add a collection nobody asked for, apart from
   `attribute-groups` with `public-groups`.
4. **Local policies** (`reference/validations.md`, "Policies"), both off unless chosen:
   `public-groups`, when the registry defines attributes and its consumers import them by
   attribute group: a policy then requires every attribute it defines to be exported by one of
   its public attribute groups. Ask; don't assume it. Registries whose consumers take attributes
   from the registry itself, as the OpenTelemetry registries' do, leave it out. And `policies`,
   the unit tests for local rego policies, with `public-groups` or when the registry has policies
   of its own. In an update, keep what the repo has: its own policy directories stay in
   `LOCAL_POLICIES`, and `public-groups` is added only when the user agrees.
5. **Existing tags**: `git ls-remote --tags <repo-url> 'v*'`. `BASELINE=auto` compares with the
   highest `vX.Y.Z` tag. Use `auto` only when the registry is published from this repo and its
   `v*` tags are the registry's own. A `-dev` family never has a baseline: set it empty. If the
   repo tags `v*` for anything else (an SDK's releases, another registry), or the registry is
   unpublished, set `BASELINE` to a pinned registry path when there is one to pin: for a registry
   inside an SDK, the latest SDK release tag that contains the registry directory
   (`<repo-url>@<tag>[<registry dir>]`, moved forward after each release; list all tags with
   `git ls-remote --tags <repo-url>`, as an SDK's may have no `v`). The baseline must resolve with
   the pinned weaver: first read the manifest at that tag
   (`git show <tag>:<registry dir>/manifest.yaml`, or `gh api` on the repo's contents at that ref
   when the clone lacks the tag): weaver rejects it
   unless it and every one of its dependencies has a `schema_url` (a dependency with only `name:`
   fails). If it doesn't, pin the default branch's commit that the change is based on
   (`git merge-base HEAD origin/<default-branch>`) until the next release tag has them. Otherwise
   set it empty and tell the user nothing checks compatibility.
6. **Dependencies**: which registries it builds on and at which release. The core registry
   almost always; see `reference/dependencies.md` for finding releases, keeping versions aligned,
   and private registries.
7. **Tools**: OPA with `policies` (`make install-opa` installs the pinned version), besides the
   base's weaver and jq. The shared policy pack pin: look for a newer commit
   (`git ls-remote https://github.com/open-telemetry/opentelemetry-weaver-packages.git HEAD`) and
   ask before bumping; in an update the repo's pins stay as they are unless the user agrees.
8. **The base**: whether the project already has the base skill's `core` part. If not, set it up
   first with that skill, as part of this change.

## 2. Add the part

Follow `reference/part.md`: copy `assets/registry/`, with `policies` `assets/policies/`, with
`public-groups` `assets/public-groups/`, and with the base's `templates` part
`assets/templates-case/`; add the Makefile section, the pins and the CI jobs the way the base's
"Adding a part" says, keeping only the chosen sections (`policies`, `public-groups`, and
`private` for a private repo); replace every `@@TOKEN@@`. Read every file that exists before
replacing it. In an update, copy file by file.

## 3. Fill in what the part can't know

- **Conventions**: add `definition/2` files under the registry directory for the project's
  conventions, at the registry's stability (`development` by default), and every dependency to its
  `manifest.yaml` (`reference/dependencies.md`). Every signal (event, metric, span, entity) sets its
  own `requirement_level`, which is `recommended` or `opt_in` (weaver rejects `required` there);
  each attribute reference in a signal takes `required`, `recommended`, `opt_in` or
  `conditionally_required: <when>`. A span also needs `name: {note: …}`. A stable signal references
  a less stable attribute only at `opt_in`. With `public-groups`, export every attribute through a
  public attribute group: the policy requires it.
- **The registry's own policies** (with `policies`, in an update): each directory in
  `LOCAL_POLICIES`, with unit tests in `policies_test/` that cover every line, and an invalid
  registry under `validations_test/validate-registry/` that only it rejects
  (`reference/validations.md`). A repo policy without tests gets them as part of the update.
- **Existing conventions the shared pack rejects** (legacy keys, in an update): never rename a
  published key to get a pass. List the violations in `KNOWN_VIOLATIONS`, and tell the user about
  the migration path that clears them (`reference/validations.md`, "Known violations"). One is
  fixed instead: a key deprecated with `renamed_to` a dependency's attribute needs an import of a
  group holding that attribute (`reference/validations.md`), so add the import before the first
  `make validate-registry`.
- **Settings**: those `reference/part.md` lists for the project (subdirectory paths, `BASELINE`,
  `KNOWN_VIOLATIONS`, and `REPO_URL` when `origin` isn't the canonical repo, or when contributors
  work from forks). With a private dependency or baseline, the base's
  `WEAVER_FLAGS := --allow-git-credentials`. Never write a token into a git URL or `insteadOf` rule.

## 4. Verify

Don't call the work done until every item below that applies has passed, and say which ones you
ran. Run them from the project directory.

1. The base skill's Verify items, for the parts it set up.
2. `make help` lists `validate-registry`, `validate-dependencies` and `test-validations`, and
   with `policies` `test-policies` and `install-opa`.
3. `make validate-registry` passes, and with `policies` `make test-policies`.
4. `make test-validations`: every case prints `ok:`, proving each validation still fails on the
   invalid registry it exists for.
5. In an update: every validation and test the repo had before still passes, or fails only where
   the update was meant to change it.
6. The CI workflow has the part's jobs and `needs` entries, and installs weaver the same way in
   every job. Once the user has pushed, watch the first run and fix what fails.

## 5. Hand over

Tell the user what was created or changed, what each make target does, which Verify items ran and
their results, and what is left for a human: for an unstable registry, graduating to stable when
they're ready; any known violations and their migration; the baseline's pin, when it is a pinned
path that must move forward after each release.

## Rules

The base skill's Rules apply to this part's files too. And:

- Don't pull policies from dependency repos into `validate-registry` (`reference/validations.md`
  explains why); shared rules come from the pinned shared policy pack.
- Never rename a key, signal name or group ID that consumers use to get a validation to pass.
