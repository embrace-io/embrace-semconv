---
name: otel-semconv-codegen
description: Generate language-specific source code (constants, typed attribute keys) from an OpenTelemetry semantic conventions registry with Weaver and custom templates - from the core registry, from a published federated registry (all of it or some of its keys), or from a registry of the project's own - with make targets that generate, validate and package the code for its platform, a template regression test, and a CI job that fails on stale or invalid generated code. Builds on the otel-semconv-base skill. Use when a project needs semantic convention constants generated for a language, when the published package for the core registry doesn't fit, or to update an existing weaver codegen setup.
---

# Code generation from a semantic conventions registry

This skill adds code generation to a project set up with the otel-semconv-base skill: a Makefile
section that runs weaver with the project's templates, the two targets only the platform can
implement (validate and package the code), and a CI job. Read the base skill's
`reference/layout.md` ("Adding a part") and this skill's `reference/part.md` before changing
anything, and use the terms in the base skill's `reference/glossary.md`.

| Reference | Read it for |
|---|---|
| `reference/part.md` | the part's files, where they go, settings and tokens |
| `reference/sources.md` | choosing and pinning the registry the code is generated from |
| `reference/templates.md` | what weaver templates see, writing them for any language, the codegen contract |

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
   all of that registry or some of its keys.
2. **The language**, where the generated code goes (a directory holding only generated code; in an
   update, look for hand-written files already in it, which each need a template of their own),
   and whether it is committed.
3. **Which kinds of conventions** the code covers (attributes, metrics, …): the collections the
   base's template test needs, at least one. Never add one nobody asked for.
4. **How the platform validates and packages code**: its compiler or type-checker, test runner,
   package format, and whether a build tool already runs weaver (`reference/templates.md`,
   "Platform integration"). Check the host's own toolchain pins (Node `devEngines`, the JDK)
   against what's installed.
5. **The base**: whether the project already has the base skill's `core` and `templates` parts
   (and `no-drift` for committed code). If not, set them up first with that skill, as part of this
   change.

## 2. Add the part

1. Set up or check the base parts (step 1.5).
2. Add `assets/project/Makefile` as the Makefile's `codegen` section and
   `assets/project/ci-validation.yaml`'s job to the CI workflow, the way the base's "Adding a
   part" says, and replace their tokens (`reference/part.md`). Set the base's `TEMPLATE_TARGETS`
   to include `$(CODEGEN_TARGET)`, and `all:` to run `validate-generated`.
3. Write `templates/registry/<CODEGEN_TARGET>/` for the language, covering only the chosen
   collections (`reference/templates.md`).
4. Replace the `validate-generated` and `package-generated` stubs with the platform's own tools
   ("The codegen contract"), and add the toolchain's setup steps to the CI job.
5. Run `make update-golden` and read every golden file: they are the expected output from here
   on. Golden files of a codegen target are source files of that language: keep them out of the
   host project's build and lint, or make them pass both.
6. Tell the project's developers how to regenerate, in the host project's own docs.

## 3. Verify

Don't call the work done until every item below that applies has passed, and say which ones you
ran. Run them from the project directory.

1. The base skill's Verify items, for the parts it set up.
2. `make help` lists `generate`, `validate-generated` and `package-generated`.
3. `make test-templates` passes, and the golden files hold output for every chosen collection.
4. `make validate-generated` and `make package-generated` pass; then read some of the generated
   code yourself.
5. `validate-generated` fails on bad output: make the template emit code that can't compile, see
   it fail, and revert ("The codegen contract").
6. In an update: the generated code is unchanged unless the update was meant to change it.
   Regenerate and compare with what was committed (`git diff`, plus `git status` for new files),
   and account for every difference.
7. The CI workflow has the `validate-generated` job and its `needs` entry, and installs weaver
   the same way in every job. Once the user has pushed, watch the first run and fix what fails.

## 4. Hand over

Tell the user what was created or changed, what each make target does, which Verify items ran and
their results, the platform decisions you made in `validate-generated` and `package-generated`,
and what is left for a human: committing the generated code, if it is committed; a code review of
the templates' output; bumping `SOURCE_REGISTRY` when a new release is wanted.

## Rules

The base skill's Rules apply to this part's files too. And:

- Never pin `SOURCE_REGISTRY` to a branch: a release tag, or `$(MODEL)`.
- Keep deprecated conventions in the generated code, marked deprecated, unless nobody compiles
  against the code yet (`reference/templates.md`, "Writing the Jinja").
