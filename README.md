# Embrace Semantic Conventions

A federated OpenTelemetry semantic convention registry for the Embrace's `emb` namespace,
to be shared between the various SDKs and backend to ensure a common set of key names.

This registry follows the federated model established by [OTEP 4815](https://github.com/open-telemetry/opentelemetry-specification/blob/main/oteps/4815-semantic-conventions-schema-v2.md)
and extends the core [OpenTelemetry semantic conventions](https://github.com/open-telemetry/semantic-conventions)
with the Embrace-specific `emb.*` conventions. It will also extend the
[client-side semantic conventions](https://github.com/open-telemetry/semantic-conventions-client-side),
which cover conventions common to mobile, browser, desktop and other end-user applications, once
that registry publishes a release.

Individual SDK platforms can create their own registry or consume this directly by generating
language-specific files so the semantic conventions can be consumed programmatically.

It contains YAMLs that define the semantic conventions for the namespaces it owns and the
associated Markdown files for those conventions. It publishes version-stamped releases
representing the public-facing surface of the manifest, but it does not generate or publish
language-specific binaries that make the hosted conventions consumable in instrumentation.

## Structure

Semantic conventions owned by this registry are defined in YAML files under `/model`. Using
templates defined in `/templates`, Weaver-based tooling crawls through all the files in that
directory and creates the appropriate documentation in `/docs`.

```
model/                    semantic convention definitions (the source of truth)
  manifest.yaml           registry identity and version (schema_url) and pinned dependencies
  emb/registry.yaml       emb.* attribute definitions and the attribute group that exports them
templates/                weaver Jinja2 templates for docs generation
templates_test/           fixture registry + golden output for the template regression test
policies/                 local rego policies run by `make check-policies`
policies_test/            OPA unit tests for those policies
docs/                     generated markdown
Makefile                  validation / docs generation / tests / packaging (`make help`)
versions.env              pinned weaver, OPA and shared policy pack versions
```

## Versioning

The registry's identity and its version both come from the `schema_url` in
`/model/manifest.yaml`: everything before the last `/` names the registry and the last segment is
its version. Only that last segment ever moves. Changing any part before it does not produce a new
version of this registry, it produces a different registry, and consumers pinning the old one never
see the change.

A release is published by the `Release` workflow from a draft that a maintainer prepares by hand.
See [RELEASING.md](RELEASING.md) for how a version is cut.

## Dependencies

The core OpenTelemetry registry is pinned to a release tag in `model/manifest.yaml`, declared as
`schema_url` + `registry_path`. `make check-policies` fails if the two name different releases.

Weaver resolves a single version of each registry for the whole dependency graph. When a
dependency that itself depends on core is added (such as the client-side registry), keep the core
version in `model/manifest.yaml` in lockstep with it.

## Getting started

[Weaver](https://github.com/open-telemetry/weaver) and [OPA](https://www.openpolicyagent.org/)
are not available via package managers like Homebrew at the pinned versions, but `make
install-weaver` and `make install-opa` download the release binaries pinned in
[`versions.env`](versions.env) and install them to `~/.local/bin`. To update either, change its
version in `versions.env` and rerun the target.

```bash
make check-policies   # validate the model: dependency resolution + shared OTel and local policies
make generate-all     # regenerate docs/ from the model
make test             # template regression test + rego policy unit tests
make package          # produce publication manifest and resolved registry under .build/package/
make help             # list every target
```

CI runs the same targets.

The markdown under `docs/` is generated output that is committed to the repo. If you change
anything under `model/` or `templates/` (or bump the pinned weaver version), rerun
`make generate-all` and commit the regenerated files together with your change — CI
fails any PR whose committed docs don't match what the model and templates generate.

If you change a template on purpose, `make update-golden` refreshes `templates_test/golden/`;
review that diff before committing it.

## Consuming this registry

There are two ways to consume this registry:

1. Generate language-specific artifacts directly — run `weaver registry generate` pointed at this
   registry with your own templates:

   ```bash
   weaver registry generate \
     -r 'https://github.com/embrace-io/embrace-semconv@<tag>[model]' \
     --v2 \
     --templates <templates-dir> <target> <output-dir>
   ```

2. Extend it from your own registry. Pin both fields to the same release in your manifest, then
   reference the attributes it defines:

   ```yaml
   dependencies:
     - schema_url: https://embrace.io/schemas/embrace/<version>
       registry_path: https://github.com/embrace-io/embrace-semconv@v<version>[model]
   ```

   `schema_url` identifies the registry and its version, while `registry_path` is where the files
   are actually fetched from. Weaver does not check that the two agree while resolving a
   dependency, so bumping one without the other could result in an unexpected version being pulled
   in (i.e. the one in `registry_path` will be used). This repo's `make check-policies` enforces
   that for its own dependencies.

   A registry only sees what its direct dependencies define, so to also `ref` core attributes,
   declare core as a dependency too, at the same version this registry uses.
