# @@PROJECT_NAME@@

@@REGISTRY_DESCRIPTION@@

This registry follows the federated model established by [OTEP 4815](https://github.com/open-telemetry/opentelemetry-specification/blob/main/oteps/4815-semantic-conventions-schema-v2.md)
and extends the core registry ([OpenTelemetry semantic conventions](https://github.com/open-telemetry/semantic-conventions)).

It contains YAMLs that define the semantic conventions for the namespaces it owns and the
associated Markdown files for those conventions.
<!-- skeleton: only with `release` -->
It publishes version-stamped releases representing the public-facing surface of the manifest, but
it does not generate or publish language-specific binaries that make the hosted conventions
consumable in instrumentation.
<!-- skeleton: end -->
<!-- skeleton: only without `release` -->
It isn't published as releases. <!-- skeleton: fill in: who uses it, and how; another registry
can depend on it by pinning a commit (`registry_path: <repo-url>@<commit>[model]`, with the
`schema_url` of the manifest at that commit) -->
<!-- skeleton: end -->

## What it defines

<!-- skeleton: fill in: the namespaces this registry owns and what each covers (e.g. "`acme.*`:
attributes and events of the Acme mobile SDK"), each linked to its pages under `docs/`; for a
registry that defines nothing yet, say so, and what it is meant to cover -->

## Structure

Semantic conventions owned by this registry are defined in YAML files under `/model`. Using
templates defined in `/templates`, Weaver-based tooling crawls through all the files in that
directory and creates the appropriate documentation in `/docs`.

```
model/                    semantic convention definitions (the source of truth)
  manifest.yaml           registry identity and version (schema_url) and pinned dependencies
templates/                weaver Jinja2 templates for docs generation
templates_test/           fixture registry + golden output for the template regression test
<!-- skeleton: only with the attributes collection -->
policies/                 local rego policies run by `make validate-registry`
policies_test/            OPA unit tests for those policies
<!-- skeleton: end -->
validations_test/         invalid registries that validation must fail on (`make test-validations`)
docs/                     generated markdown
Makefile                  validation / docs generation / tests (`make help`)
versions.env              pinned tool and shared policy pack versions
.weaver.toml              empty, so no parent directory's .weaver.toml can change weaver's behavior
```

## Versioning

The registry's identity and its version both come from the `schema_url` in
`/model/manifest.yaml`: everything before the last `/` names the registry and the last segment is
its version. Only that last segment ever moves. Changing any part before it does not produce a new
version of this registry, it produces a different registry, and consumers pinning the old one never
see the change.

<!-- skeleton: only for stability "unstable" (the default) -->
The registry is under development until its first release without a pre-release suffix: its
versions are `0.x.0-dev` prereleases, its conventions are `stability: development`, and any of
them may change or be removed in the next version. Once it has a release without a suffix,
`make validate-registry` compares the registry with that release and fails on breaking changes:
removing an attribute or signal, or changing a stable one incompatibly. Deprecate instead of
removing.
<!-- skeleton: end -->
<!-- skeleton: only for stability "stable" -->
The registry is stable (`stability: stable` in its manifest). Removing an attribute or signal,
or changing a stable one incompatibly, is a breaking change: deprecate instead of removing.
<!-- skeleton: only with a signal collection (events, metrics, spans, entities) -->
Stable signals reference less stable attributes only at `opt_in`.
<!-- skeleton: end -->
<!-- skeleton: only when BASELINE is set (auto, or a pinned registry path) -->
`make validate-registry` compares every change with the baseline and fails on breaking changes.
<!-- skeleton: end -->
<!-- skeleton: only when BASELINE is empty -->
Nothing compares changes with an earlier version yet (`BASELINE` is empty), so reviewers must
catch breaking changes.
<!-- skeleton: end -->
<!-- skeleton: end -->
<!-- skeleton: only for stability "-dev family" (VERSION_SUFFIX := -dev) -->
The registry publishes every convention, whatever its stability, and promises no compatibility:
every version carries the `-dev` suffix and is a prerelease, so any convention may change or be
removed in the next version. Its stable conventions belong to
<!-- skeleton: fill in: the stable registry's name, linked, or "(planned)" if it isn't yet -->.
<!-- skeleton: end -->

<!-- skeleton: only with `release` -->
A release is published by the `Release` workflow from a draft that a maintainer prepares by hand.
See [RELEASING.md](RELEASING.md) for how a version is released.
<!-- skeleton: end -->

## Dependencies

Every dependency is pinned to a release tag in `model/manifest.yaml`, declared as `schema_url` +
`registry_path`. `make validate-registry` fails if a `schema_url` doesn't name the registry and
version that its `registry_path` fetches.

Weaver resolves a single version of each registry for the whole dependency graph, and
`make validate-registry` fails if the graph requests any registry at more than one version. When
a dependency that itself depends on the core registry is added, keep the core registry version in
`model/manifest.yaml` in lockstep with it.

## Getting started

The tools are pinned in [`versions.env`](versions.env). `make install-weaver` downloads the
pinned [Weaver](https://github.com/open-telemetry/weaver) release to `~/.local/bin`, since
package managers like Homebrew don't carry that version. To update it, change its version in
`versions.env` and rerun the target. The make targets also need
[jq](https://jqlang.org/download/) on `PATH`.
<!-- skeleton: only with the attributes collection -->
The policy tests also need [OPA](https://www.openpolicyagent.org/), which `make install-opa`
installs the same way.
<!-- skeleton: end -->

```bash
make validate-registry   # validate the registry: dependencies + schema + policies
make generate-all        # regenerate docs/ from the registry
make test                # template and validation regression tests
<!-- skeleton: only with the attributes collection -->
                         # (and the local policy's unit tests)
<!-- skeleton: end -->
<!-- skeleton: only with `release` -->
make package             # produce publication manifest and resolved registry under .build/package/
<!-- skeleton: end -->
make help                # list every target
```

CI runs the same validations and tests in the `@@CI_WORKFLOW_NAME@@` workflow, one job per
validation or test. Most jobs are named after the make target they run; `validate-docs` runs
`make generate-docs` and compares the result with the committed docs.

The markdown under `docs/` is generated output that is committed to the repo. If you change
anything under `model/` or `templates/` (or bump the pinned weaver version), rerun
`make generate-all` and commit the regenerated files together with your change — CI's
`validate-docs` job fails any PR whose committed docs don't match what the registry and templates
generate.

If you change a template on purpose, `make update-golden` refreshes `templates_test/golden/`;
review that diff before committing it.

<!-- skeleton: only with `release` -->
## Consuming this registry

Before you start:

<!-- skeleton: only for stability "unstable" (the default) or "stable" -->
- Pick a release version to depend on from the [releases page](@@REPO_URL@@/releases): the
  newest release without a pre-release suffix when there is one. `/releases/latest` skips
  prereleases, so while the registry only publishes `-dev` versions, pick the newest prerelease,
  and expect its conventions to change.
<!-- skeleton: end -->
<!-- skeleton: only for stability "-dev family" (VERSION_SUFFIX := -dev) -->
- Pick a release version to depend on from the [releases page](@@REPO_URL@@/releases): the
  newest prerelease, since every version is one (`/releases/latest` skips them all), and expect
  its conventions to change.
<!-- skeleton: end -->
- Use the weaver version pinned in [`versions.env`](versions.env), or later.
- Check that the release contains the conventions you want to use. They are listed in
  [`docs/`](docs/README.md).
<!-- skeleton: only with the attribute-groups collection -->
- Its public attribute groups, which a registry can import whole, are listed in
  `docs/attribute-groups.md` (generated once the registry has a group).
<!-- skeleton: end -->
<!-- skeleton: only for a private repo -->
- This repository is private: you need read access to it, and weaver needs
  `--allow-git-credentials` to fetch it with your git credentials.
<!-- skeleton: end -->

There are two ways to consume it:

1. Generate source code from the conventions this registry exports
2. Depend on its conventions in your own registry

### Generate source code from this registry

If you need to reference this registry's conventions in source code, run
`weaver registry generate` and provide it with the appropriate parameters:

```bash
weaver registry generate \
  -r '@@REPO_URL@@@<version>[model]' \
  --v2 \
  --templates <your-templates-dir> <your-target> <your-output-dir>
```
<!-- skeleton: only for a private repo -->

Add `--allow-git-credentials`, since this repository is private.
<!-- skeleton: end -->

- `<version>`: the release tag to generate from: `v` followed by the release's version.
- `<your-templates-dir>`: the directory holding your templates, with each target's templates in
  `<your-templates-dir>/registry/<your-target>/`.
- `<your-target>`: the name of the directory under `registry/` whose templates to render, e.g.
  `kotlin`. The name is your choice.
- `<your-output-dir>`: where the generated files are written.

### Depend on its conventions in your own registry

If your project defines semantic conventions of its own and wants to use conventions defined in
this registry, create your own federated registry and declare this one as a dependency, pinning
both fields to the same release:

```yaml
dependencies:
  - schema_url: @@REGISTRY_URL@@/<version>
    registry_path: @@REPO_URL@@@v<version>[model]
```

`<version>` is the release without the `v` prefix; `registry_path` adds the `v` because that's how
the release tags are named. `schema_url` identifies the registry and its version, while
`registry_path` is where the files are actually fetched from. Weaver doesn't fail when the two
disagree (at most it warns), so bump them together.

A registry only sees what its direct dependencies define, so to also `ref` the core registry's
attributes, declare the core registry as a dependency too, at the same version this registry
uses (see [`model/manifest.yaml`](model/manifest.yaml)). Then `ref` the attributes you need
from your own public attribute groups, or import one of this registry's groups whole.
<!-- skeleton: end -->
