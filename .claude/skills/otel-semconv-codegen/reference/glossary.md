# Glossary

Use these terms, and only these, in everything this skill writes (docs, comments, commit
messages, messages to the user), so the same thing is always called the same thing.

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
| **pre-release version** | a version with a SemVer suffix like `0.1.0-dev`, published as a GitHub prerelease | dev release, unstable release |
| **published** / **unpublished** registry | released as GitHub releases / not, e.g. an SDK's registry of its own conventions, which it generates code from | released (for the registry), internal |

## Validation and tests

| Term | Means | Don't say |
|---|---|---|
| **validate** | what `validate-generated` does: fail on invalid generated code | check (unqualified), verify |
| **test** | what the `test-*` targets do: exercise the templates | check |
| **check** | only `weaver registry check`, weaver's own command | anything else |
| **fixture** | the registry the templates render in `test-templates` | sample |
| **golden files** | the templates' expected output from the fixture | snapshot |
| **policy** | a set of rego rules weaver evaluates | rule, check |

## Generation

| Term | Means | Don't say |
|---|---|---|
| **generate** | run weaver templates to write code | build, render (except for templates themselves) |
| **template target** | a directory under `templates/registry/`, e.g. `kotlin` | template set |
| **generated code** | what `generate` writes | output, artifacts |

## The skill's own terms

| Term | Means |
|---|---|
| **layout** | the files the skill copies into a project, under its `assets/` |
| **verify** | what a skill's Verify step does: confirm the work is complete and correct (never a synonym for the `validate-*` targets) |
| **part** | what the skill or one of its options adds to a project: files, a Makefile section, CI jobs. They are `core`, `templates`, `codegen`, `no-drift` and `renovate` |
| **collection** | a kind of convention the project supports: attributes, attribute groups, events, metrics, spans, entities |
| **section** | a block between `==== <name>` and `==== end <name>` lines in the Makefile, the CI workflow or `versions.env` |
| **token** | an `@@NAME@@` placeholder in an asset |
