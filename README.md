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
scripts/                  validation / resolution / docs generation
```

## Getting started

[Weaver](https://github.com/open-telemetry/weaver) is not available via package managers like
Homebrew, but you can install it by running `scripts/install-weaver.sh`, which downloads the release
binary pinned in [`versions.env`](versions.env) and installs it to `~/.local/bin` (pass a different
directory as the first argument if preferred). To update it, change `WEAVER_VERSION` in
`versions.env` and rerun the script. The same file pins the upstream semantic-conventions tag and the
shared policy pack used by `scripts/check.sh`.

```bash
scripts/check.sh          # validate the model: dependency resolution + shared OTel policies
scripts/generate-docs.sh  # regenerate docs/ from the model
scripts/package.sh        # produce publication manifest and resolved registry under build/package/
```

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
