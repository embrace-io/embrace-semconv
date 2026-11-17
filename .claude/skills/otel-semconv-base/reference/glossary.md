# Glossary

Use these terms, and only these, in everything the otel-semconv skills write (docs, comments,
commit messages, messages to the user), so the same thing is always called the same thing. This
file is the one home of the terms for every skill that builds on this one.

## Registries

| Term | Means | Don't say |
|---|---|---|
| **registry** | the conventions weaver resolves from a registry directory, identified by its `schema_url` | model, schema, repo (for the registry itself) |
| **registry directory** | the directory holding the registry's files, `model/` by convention; name the path only when the path matters | model (as a noun for the registry) |
| **manifest** | `manifest.yaml` in the registry directory | registry manifest, config |
| **registry name** | the `schema_url` up to its last `/`, without the scheme (e.g. `example.com/schemas/my-registry`); what the user names. The whole `schema_url` is the registry's **identity** (name plus version) | family |
| **registry URL** | the registry name with its scheme, i.e. the `schema_url` without its version (e.g. `https://example.com/schemas/my-registry`) | registry name (for the URL form) |
| **version** | the `schema_url`'s last segment, SemVer without a `v` | release (for the number) |
| **dependency** | another registry declared in the manifest | upstream, parent |
| **core registry** | the OpenTelemetry semantic conventions registry (`open-telemetry/semantic-conventions`) | core (alone), upstream, OTel registry |
| **federated registry** | a registry other than the core registry, built on it per OTEP 4815 | extension, sub-registry |

## Conventions

| Term | Means | Don't say |
|---|---|---|
| **convention** | one attribute, attribute group, event, metric, span or entity | definition (for all of them), signal (for all of them) |
| **signal** | an event, metric, span or entity | convention (when only signals are meant) |
| **definition** | a convention declared in this registry | declaration |
| **reference** | a `ref` to an attribute by key | use, include |
| **import** | an `imports` entry taking a dependency's attribute groups or signals | include, re-export |
| **public** / **internal** group | `visibility: public`, which reaches templates and consumers / `internal`, which doesn't | exported group, private |
| **export** | what a public attribute group does for each attribute it references: makes it reachable by consumers, who import by group. The registry's public groups are its export surface | publish (for attributes) |
| **stability** | `development` or `stable` on a registry or a convention | maturity, status |

## Releases

| Term | Means | Don't say |
|---|---|---|
| **release** | a published GitHub release of a registry | cut (as a noun) |
| **tag** | the release's git tag, `v<version>` | release (for the tag) |
| **draft** | a release a maintainer has prepared but not published | pending release |
| **pre-release version** | a version with a SemVer suffix like `0.1.0-dev`, published as a GitHub prerelease | dev release, unstable release |
| **baseline** | the release, or pinned registry path, `validate-registry` compares the registry with (`BASELINE`) | previous version, old registry |
| **published** / **unpublished** registry | released as GitHub releases (the `release` feature) / not, e.g. an SDK's registry of its own conventions, which it generates code from | released (for the registry), internal |

## Validation and tests

| Term | Means | Don't say |
|---|---|---|
| **validate** | what the `validate-*` targets do: fail on an invalid registry, docs or code | check (unqualified), verify |
| **test** | what the `test-*` targets do: exercise the templates, policies and validations | check |
| **check** | only `weaver registry check`, weaver's own command | anything else |
| **invalid registry** / **case** | a registry under `validations_test/` that a validation must fail on | rejected, bad, negative test |
| **fixture** | the registry the templates render in `test-templates` | sample |
| **golden files** | the templates' expected output from the fixture | snapshot |
| **policy** | a set of rego rules weaver evaluates | rule, check |
| **shared policy pack** | the pinned `opentelemetry-weaver-packages` policies | shared policies, upstream policies |
| **local policy** | a policy under the project's `policies/` | custom policy |
| **known violation** | a shared policy pack violation the registry accepts, listed in its `KNOWN_VIOLATIONS` file | exception, waiver, suppression |

## Generation

| Term | Means | Don't say |
|---|---|---|
| **generate** | run weaver templates to write docs or code | build, render (except for templates themselves) |
| **template target** | a directory under `templates/registry/`, e.g. `markdown`, `kotlin` | template set |
| **generated code** / **docs** | what `generate` / `generate-docs` writes | output, artifacts |
| **publication artifacts** | the `manifest.yaml` and `resolved.yaml` `make package` writes for a release | package, bundle |

## The skill's own terms

| Term | Means |
|---|---|
| **layout** | the files the skills copy into a project, under their `assets/` |
| **verify** | what a skill's Verify step does: confirm the work is complete and correct (never a synonym for the `validate-*` targets) |
| **part** | what one skill or one of its options adds to a project: files, a Makefile section, CI jobs. This skill's are `core`, `templates` and `no-drift` |
| **collection** | a kind of convention the project supports: attributes, attribute groups, events, metrics, spans, entities |
| **section** | a block between `==== <name>` and `==== end <name>` lines in a Makefile, workflow, pin file or template |
| **token** | an `@@NAME@@` placeholder in an asset |
| **skeleton** | a prose file a skill provides as a starting point (README.md, AGENTS.md, CONTRIBUTING.md, RELEASING.md), with `<!-- skeleton: ... -->` blocks to keep or drop |
