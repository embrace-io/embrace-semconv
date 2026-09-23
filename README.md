# Embrace Semantic Conventions

A federated OpenTelemetry semantic convention registry for the Embrace's `emb` namespace,
to be shared between the various SDKs and backend to ensure a common set of key names. 

This registry follows the federated model established by [OTEP 4815](https://github.com/open-telemetry/opentelemetry-specification/blob/main/oteps/4815-semantic-conventions-schema-v2.md)
and extends the general OpenTelemetry semantic conventions with the Embrace-specific `emb.*`
conventions. Individual SDK platforms can create their own registry or consume this
directly by generating language-specific files so the semantic conventions can be
consumed programmatically.

It contains YAMLs that define the semantic conventions, and scripts to generate associated
markdown files, but does not generate language-specific binaries that are directly consumable in
instrumentation projects.

## Repository layout

```
model/                    semantic convention definitions (the source of truth)
  manifest.yaml           registry name, schema_url, and pinned dependencies
  emb/registry.yaml       emb.* attribute definitions
  emb/events.yaml         emb.* event definitions
templates/                weaver Jinja2 templates for docs generation
docs/                     generated markdown
Makefile                  validation / docs generation / packaging (`make help`)
versions.env              pinned weaver and shared policy pack versions
```

## Getting started

[Weaver](https://github.com/open-telemetry/weaver) is not available via package managers like
Homebrew, but `make install-weaver` downloads the release binary pinned in
[`versions.env`](versions.env) and installs it to `~/.local/bin`. To update it, change
`WEAVER_VERSION` in `versions.env` and rerun the target.

```bash
make check-policies   # validate the model: dependency resolution + shared OTel and local policies
make generate-all     # regenerate docs/ from the model
make package          # produce publication manifest and resolved registry under .build/package/
make help             # list every target
```

CI runs the same targets.

The markdown under `docs/` is generated output that is committed to the repo. If you change
anything under `model/` or `templates/` (or bump the pinned weaver version), rerun
`make generate-all` and commit the regenerated files together with your change — CI
fails any PR whose committed docs don't match what the model and templates generate.

See [RELEASING.md](RELEASING.md) for how versions are cut and published.

## Consuming this registry

There are two ways to consume this registry:

1. Generate language-specific artifacts directly — run `weaver registry generate` pointed at this
   registry with your own templates:

   ```bash
   weaver registry generate \
     -r 'https://github.com/embrace-io/embrace-semconv@<tag>[model]' \
     --templates <templates-dir> <target> <output-dir>
   ```

2. Extend it from your own registry — declare it as a dependency in your `manifest.yaml`, then
   reference the attributes and events it (and its ancestors) define:

   ```yaml
   dependencies:
     - name: embrace
       registry_path: https://github.com/embrace-io/embrace-semconv@<tag>[model]
   ```
