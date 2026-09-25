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
validations_test/         invalid registries that validation must fail on (`make test-validations`)
docs/                     generated markdown
Makefile                  validation / docs generation / tests / packaging (`make help`)
versions.env              pinned weaver, OPA and shared policy pack versions
.weaver.toml              empty, so no parent directory's .weaver.toml can change weaver's behavior
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
`schema_url` + `registry_path`. `make check-policies` fails if the `schema_url` doesn't name the
registry and version that `registry_path` fetches.

Weaver resolves a single version of each registry for the whole dependency graph, and
`make check-policies` fails if the graph requests any registry at more than one version. When a
dependency that itself depends on core is added (such as the client-side registry), keep the core
version in `model/manifest.yaml` in lockstep with it.

## Getting started

[Weaver](https://github.com/open-telemetry/weaver) and [OPA](https://www.openpolicyagent.org/)
are not available via package managers like Homebrew at the pinned versions, but `make
install-weaver` and `make install-opa` download the release binaries pinned in
[`versions.env`](versions.env) and install them to `~/.local/bin`. To update either, change its
version in `versions.env` and rerun the target. The tests also need
[jq](https://jqlang.org/download/) on `PATH`.

```bash
make check-policies   # validate the model: dependency resolution + shared OTel and local policies
make generate-all     # regenerate docs/ from the model
make test             # template and validation regression tests + rego policy unit tests
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

Before you start:

- Pick a release version to depend on.
  - Typically, consumers will select the latest release from the
    [releases page](https://github.com/embrace-io/embrace-semconv/releases).
- Pick a weaver version to use.
  - 0.26.1 is the minimum required.
- Ensure the version you are using contains the conventions you want to use.
  - This registry exports its attributes through one public attribute
    group, `registry.embrace.emb`, defined in [`model/emb/registry.yaml`](model/emb/registry.yaml).
  - The attributes themselves are listed in [`docs/`](docs/README.md).

There are two ways to consume it:

1. Generate source code from the conventions exported by this registry
2. Depend on exported conventions in your own registry

### Generate source code from this registry

If you need to reference this registry's conventions in source code,
run `weaver registry generate` and provide it with the appropriate parameters:

```bash
weaver registry generate \
  -r 'https://github.com/embrace-io/embrace-semconv@<version>[model]' \
  --v2 \
  --templates <your-templates-dir> <your-target> <your-output-dir>
```

- `<version>`: the release tag to generate from, including its `v` prefix, e.g. `v0.3.0`.
- `<your-templates-dir>`: the directory holding your templates, with each target's templates in
  `<your-templates-dir>/registry/<your-target>/`. See [Writing templates](#writing-templates) for
  why the `registry/` level is there.
- `<your-target>`: the name of the directory under `registry/` whose templates to render, e.g.
  `kotlin`. The name is your choice.
- `<your-output-dir>`: where the generated files are written.

For example, with the Kotlin templates from [Writing templates](#writing-templates) saved under
`templates/registry/kotlin/`:

```bash
weaver registry generate \
  -r 'https://github.com/embrace-io/embrace-semconv@v0.3.0[model]' \
  --v2 \
  --templates templates kotlin build/generated/semconv
```

See the [Writing templates](#writing-templates) section for more details about... writing templates.

### Depend on exported conventions in your own registry

If your project defines semantic conventions of its own and wants to use attributes defined in this
registry (e.g. to make your own event that includes `emb.user_session_id`), create your own
federated registry and declare this one as a dependency.

1. Declare the dependency in your registry's `manifest.yaml`, pinning both fields to the same
   release.

   Your registry is a directory of YAML files that you point weaver at with `-r`. By convention, it
   is a directory called `model/` at the root of your repo: the core OpenTelemetry semantic
   conventions registry, the other OpenTelemetry registries and this one all do that, and weaver's
   own default registry is core's `[model]` subdirectory. Weaver doesn't require the name, but
   following it means anyone depending on your registry writes the same `…@<tag>[model]`
   `registry_path` as for every other one. This README uses `model/` throughout.

   The manifest itself is strictly named and located: it must be exactly `manifest.yaml` and sit
   at the root of the registry directory. Without that file there, none of your dependencies are
   loaded.

   ```yaml
   schema_url: https://<your-domain>/schemas/<your-registry>/<your-version>
   description: <your-description>
   stability: <your-stability>
   dependencies:
     - schema_url: https://opentelemetry.io/schemas/<core-version>
       registry_path: https://github.com/open-telemetry/semantic-conventions@v<core-version>[model]
     - schema_url: https://embrace.io/schemas/embrace/<embrace-version>
       registry_path: https://github.com/embrace-io/embrace-semconv@v<embrace-version>[model]
   ```

   - `<your-domain>` and `<your-registry>`: with the `/schemas/` between them, they name your
     registry. Weaver treats everything between the scheme and the last `/` (e.g.
     `embrace.io/schemas/embrace-web`) as the name, so changing any part of it, `schemas`
     included, creates a different registry, not a new version. The `/schemas/` segment is a
     convention, not a requirement: weaver only needs the last segment to be the version, and
     `https://<your-domain>/<your-registry>/<your-version>` works too. Core, the other
     OpenTelemetry registries and this one all use
     `https://<domain>/schemas/<registry>/<version>`, the pattern
     [OTEP 4815](https://github.com/open-telemetry/opentelemetry-specification/blob/main/oteps/4815-semantic-conventions-schema-v2.md)
     describes, so following it keeps your URL recognizable next to theirs.
   - `<your-version>`: your registry's own version, e.g. `1.1.0`.
   - `<your-description>`: a one-line description of your registry.
   - `<your-stability>`: `development` or `stable`.
   - `<core-version>`: the core OpenTelemetry release, without the `v` prefix, e.g. `1.44.0`. Use
     the same version this registry depends on (see [`model/manifest.yaml`](model/manifest.yaml)).
   - `<embrace-version>`: this registry's release, without the `v` prefix, e.g. `0.3.0`.
     `registry_path` adds the `v` because that's how the release tags are named.

   For example, for the Embrace Web SDK:

   ```yaml
   schema_url: https://embrace.io/schemas/embrace-web/1.1.0
   description: Semantic conventions for the Embrace Web SDK.
   stability: development
   dependencies:
     - schema_url: https://opentelemetry.io/schemas/1.44.0
       registry_path: https://github.com/open-telemetry/semantic-conventions@v1.44.0[model]
     - schema_url: https://embrace.io/schemas/embrace/0.3.0
       registry_path: https://github.com/embrace-io/embrace-semconv@v0.3.0[model]
   ```

   `schema_url` identifies the registry and its version, while `registry_path` is where the files
   are actually fetched from. Weaver doesn't fail when the two disagree (at most it warns), so
   bumping one without the other could result in an unexpected version being pulled in (i.e. the
   one in `registry_path` will be used). This repo's `make check-policies` enforces that they agree
   for its own dependencies.

   A registry only sees what its direct dependencies define, so to also `ref` core attributes,
   declare core as a dependency too, at the same version this registry uses.

2. Reference what you need by referencing an attribute by name or importing a whole group. This
   ensures the source code generation step later on picks up the right conventions.

   These go in `definition/2` files anywhere under `model/`. Weaver reads every `.yaml`/`.yml` file
   under it, however deeply nested, and merges them into one registry. That's why a registry is
   defined by a directory rather than just its manifest. What it includes comes from the aggregated
   conventions, and file names and directories are just for organizational and readability
   purposes. The imports, attribute groups, other conventions can share a file/directory or live in
   separate ones: weaver doesn't care, so reorganizing them doesn't cause a change in the registry
   (i.e. a version change is not required).

   Reference attributes by name:

   ```yaml
   # any file under model/
   file_format: definition/2

   attribute_groups:
     - id: <your-group-id>
       visibility: public
       stability: <your-stability>
       brief: <your-brief>
       attributes:
         - ref: <attribute-key>   # e.g. from this registry
         - ref: <attribute-key>   # e.g. from core OpenTelemetry
   ```

   - `<your-group-id>`: your attribute group's ID. Weaver only needs it to be unique. Core and the
     mainframe registry name the groups that hold their attributes `registry.<namespace>` (e.g.
     `registry.session`), and this registry follows that for the group it exports
     (`registry.embrace.emb`); there's no settled convention yet for `definition/2` groups beyond
     that, so any unique ID works. Group IDs are part of your registry's public surface.
   - `visibility: public`: required for the group to reach your templates. Weaver drops `internal`
     groups (building blocks other groups can include) when it resolves the registry.
   - `<your-stability>` and `<your-brief>`: the group's stability and a one-line description.
   - `<attribute-key>`: the key of an attribute to include, from this registry (see
     [`docs/`](docs/README.md)), from core, or from your own registry. List as many as you need.

   For example, for the Embrace Web SDK's session attributes:

   ```yaml
   # model/web/registry.yaml
   file_format: definition/2

   attribute_groups:
     - id: registry.embrace.websession
       visibility: public
       stability: development
       brief: Session attributes the Embrace Web SDK records.
       attributes:
         - ref: emb.user_session_id   # from this registry
         - ref: session.id            # from core OpenTelemetry
   ```

   Or import this registry's whole group. `registry.embrace.emb` is the group this registry
   exports, so it stays as is:

   ```yaml
   # model/web/imports.yaml
   file_format: definition/2

   imports:
     attribute_groups:
       - "registry.embrace.emb"
   ```

   A `ref` that doesn't resolve to anything is a hard error, which catches typos and attributes
   removed upstream.

3. Generate source code based on your registry:

   ```bash
   weaver registry generate \
     -r model \
     --v2 \
     --templates <your-templates-dir> <your-target> <your-output-dir>
   ```

   `-r model` points at your registry directory, and the other placeholders are the same as
   [above](#generate-source-code-from-this-registry). For example, with the Kotlin templates from
   [Writing templates](#writing-templates) saved under `templates/registry/kotlin/`:

   ```bash
   weaver registry generate -r model --v2 --templates templates kotlin build/generated/semconv
   ```

### Writing templates

The templates used here are [weaver templates](https://github.com/open-telemetry/weaver/blob/main/crates/weaver_forge/README.md):
Jinja files plus a `weaver.yaml` whose filters select what each one renders. With `--v2`, the
filters and templates see weaver's v2 resolved registry.

The examples here keep templates in `templates/registry/<your-target>/`. Two parts of that are
conventions rather than requirements:

- `templates/` is weaver's default for `--templates`, and what the OpenTelemetry registries use.
  Any directory works if you pass it explicitly.
- The `registry/` level is weaver's
  [documented layout](https://github.com/open-telemetry/weaver/blob/main/crates/weaver_forge/README.md).
  It looks redundant when it holds a single target, but it can hold several (this repo's
  templates are in `registry/markdown/`). It exists to separate templates that generate from a
  semantic convention registry from other kinds weaver may add alongside it, such as the
  `templates/schema/<target>` templates its docs mention for application telemetry schemas.

  Weaver always looks for `<your-templates-dir>/registry/<your-target>/` first. Only if that
  directory doesn't exist does it fall back to `<your-templates-dir>/<your-target>/`, an
  undocumented fallback rather than a supported layout. If both exist, the `registry/` one wins
  and templates at `<your-templates-dir>/<your-target>/` are silently never read, so keep the
  `registry/` level.

The `<your-target>` directory name is yours to choose. A minimal example that writes one Kotlin
file of attribute-key constants per attribute group, placed in `templates/registry/kotlin/` and
generated with `kotlin` as the `<your-target>`:

```yaml
# weaver.yaml
templates:
  - pattern: attributes.kt.j2
    # One file per attribute group: the groups your registry defines plus any it imports.
    filter: .registry.attribute_groups // []
    application_mode: each
    file_name: "{{ ctx.id | split('.') | last | pascal_case }}Attributes.kt"
```

```jinja
{# attributes.kt.j2 #}
// Generated from {{ ctx.id }}. Do not edit.
object {{ ctx.id | split('.') | last | pascal_case }}Attributes {
{%- for attribute in ctx.attributes | sort(attribute="key") %}
    /** {{ attribute.brief | trim }} */
    const val {{ attribute.key | screaming_snake_case }} = "{{ attribute.key }}"
{%- endfor %}
}
```

With the `ref` example above, that generates `WebsessionAttributes.kt` containing
`EMB_USER_SESSION_ID` and `SESSION_ID`, plus `EmbAttributes.kt` if you also import
`registry.embrace.emb`. Pointed directly at this registry, the same templates generate
`EmbAttributes.kt`.

Every definition carries `provenance.source`: the `schema_url` of the registry it came from,
empty for your own. Filter on it to split what you define from what you depend on. This repo's
[`templates/registry/markdown/weaver.yaml`](templates/registry/markdown/weaver.yaml) does that to
document only its own attributes.

### Reference implementation

The Embrace Android SDK consumes this registry this way in its
[`embrace-android-semconv`](https://github.com/embrace-io/embrace-android-sdk/tree/main/embrace-android-semconv)
module: its manifest depends on core and on this registry, its own groups `ref` the attributes it
records, its Kotlin templates generate the constants, a Gradle task runs `weaver registry generate`,
and CI fails if the committed output drifts. You can use whatever tooling is appropriate for your
project to accomplish what the Android SDK does.
