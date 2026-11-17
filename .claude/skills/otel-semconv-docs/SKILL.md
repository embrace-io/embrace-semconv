---
name: otel-semconv-docs
description: Generate and commit markdown documentation for an OpenTelemetry semantic conventions registry with Weaver and the shared markdown templates of opentelemetry-weaver-packages (pinned with the shared policy pack), with a CI job that fails on stale docs, and the registry repo's README, AGENTS, CLAUDE and CONTRIBUTING files from skeletons. Builds on the otel-semconv-base and otel-semconv-registry skills. Use when a registry needs docs, or to move a registry's docs from templates of its own to the shared ones.
---

# Docs for a semantic conventions registry

This skill adds generated docs to a project with a registry (the otel-semconv-registry skill, on
the otel-semconv-base skill). The docs come from the shared markdown templates of
opentelemetry-weaver-packages, fetched by URL at the commit the shared policy pack is pinned to:
the project keeps no docs templates of its own. Read the base skill's `reference/layout.md`
("Adding a part") and this skill's `reference/part.md` before changing anything, and use the terms
in the base skill's `reference/glossary.md`.

## 1. Gather facts first

1. **The registry**: the project must have the registry skill's part (and so the base's `core`);
   set it up first with that skill if not, as part of this change. The base's `no-drift` part is
   needed too.
2. **Where the docs are read**, for `DOCS_BASE_URL`: for docs read on GitHub, the docs directory on
   the default branch. Ask when the repo has no remote yet.
3. **What's there already**: docs templates of the repo's own, committed docs, a docs workflow,
   and README.md, AGENTS.md, CONTRIBUTING.md or CLAUDE.md. In an update, the repo's own docs
   templates are replaced by the shared ones (`reference/part.md`); the docs then change, which
   is expected: say so.
4. **Template settings**: namespaces whose titles need more than a capital (acronyms like `SDK`,
   names like `CI/CD`), and whether the docs should link dependencies' attributes to their docs
   (`reference/part.md`, "Template settings in `.weaver.toml`").
5. **For the skeletons**: the facts the registry skill gathered (stability, published or not,
   collections, `BASELINE`, known violations, private), the project's name, and the namespaces it
   owns.

## 2. Add the part

1. Copy `assets/docs/` (`.gitattributes` next to `docs/`), and add the Makefile section and the
   CI job the way the base's "Adding a part" says, replacing their tokens
   (`reference/part.md`). Set `all:` to run `validate-registry generate-all`.
2. In an update, delete the repo's own docs templates and anything that only they used (their
   golden files and template test target, unless other templates still need them), and the old
   docs workflow, which `validate-docs` replaces.
3. Add the template settings to `.weaver.toml`, under `[template]`, if any (step 1.4).
4. Write README.md, AGENTS.md, CLAUDE.md and CONTRIBUTING.md from `assets/skeletons/`
   (the base skill's `reference/layout.md`, "Skeletons"): keep each block whose condition holds,
   drop the others, fill in what each `fill in` asks for, and remove every marker. Where the repo
   already has one of these files, merge instead.
5. Run `make generate-docs` and read the result.

## 3. Verify

Don't call the work done until every item below that applies has passed, and say which ones you
ran. Run them from the project directory.

1. The base and registry skills' Verify items, for the parts they set up.
2. Nothing left to fill in: no `<!-- skeleton` anywhere in the project (hidden files included).
3. `make generate-docs` passes, and `docs/` has a page for each namespace the registry defines and
   none for a namespace it only imports; the links point under `DOCS_BASE_URL`.
4. The docs describe only what the project has: e.g. without `attributes`, a search of the docs for
   `polic`, `OPA` and `opa` matches only the shared policy pack; without the release skill's part,
   nothing describes how this registry is released; the signal kinds mentioned are only those the
   registry defines.
5. The CI workflow has the `validate-docs` job and its `needs` entry. Once the user has pushed,
   watch the first run and fix what fails.

## 4. Hand over

Tell the user what was created or changed, which Verify items ran and their results, that the docs
come from the shared templates (and, in an update, how they differ from the old ones), and what is
left for a human: committing the generated docs.

## Rules

The base skill's Rules apply to this part's files too. And:

- Never hand-edit `docs/`: change the registry, a template setting or a param, and regenerate.
- Don't copy the shared templates into the repo: they're fetched at the pinned commit.
