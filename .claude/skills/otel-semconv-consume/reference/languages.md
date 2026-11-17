# The published packages, by language

Each section gives the package, how to add and import it, how it separates stable from unstable
conventions, how to find which core release its latest version carries, and what to know about
bumps. The examples use `http.request.method`, which is stable.

In each "Which core release" block, the first line prints the latest release; a second line, where
there is one, takes that release as `<tag>` and prints the core release it carries. Where the
package's version is the core release, there is no second line. Every block is run by the skill's
tests, so each one is known to work.

| Language | Package | Version = core release? | Unstable conventions |
|---|---|---|---|
| Go | `go.opentelemetry.io/otel/semconv/v<core release>` | in the import path | no split; every release's package is frozen |
| Java, Kotlin | `io.opentelemetry.semconv:opentelemetry-semconv` | yes | separate `-incubating` artifact |
| JavaScript, TypeScript | `@opentelemetry/semantic-conventions` | yes | `/incubating` entry point |
| Python | `opentelemetry-semantic-conventions` | no (beta versions) | `opentelemetry.semconv._incubating` |
| Rust | `opentelemetry-semantic-conventions` | no (0.x crate) | Cargo feature `semconv_experimental` |
| PHP | `open-telemetry/sem-conv` | yes | `OpenTelemetry\SemConv\Incubating` |
| Ruby | `opentelemetry-semantic_conventions` | yes | `OpenTelemetry::SemConv::Incubating` |
| C++ | headers in `opentelemetry-cpp` | no (the SDK's release) | `semconv/incubating/` headers |
| Swift | inside `OpenTelemetryApi` (`opentelemetry-swift-core`) | no (the SDK's release) | no split |
| Erlang, Elixir | `opentelemetry_semantic_conventions` | yes | `incubating` headers and modules |
| .NET | none | | |

## Go

- **Package:** `go.opentelemetry.io/otel/semconv/v<core release>`, one directory per core release,
  in the module `go.opentelemetry.io/otel` (the API's module, so it moves with the API).
  Subpackages (`httpconv`, `dbconv`, …) hold typed metric instruments.
- **Add:** `go get go.opentelemetry.io/otel@<version>`, import the package, then `go mod tidy`.
  A new otel release can raise the minimum Go version: v1.47.0 needs Go 1.26.0, and `go get`
  raises the module's `go` line to match. When the project can't move its Go version, take the
  newest release whose `go` line it meets:
  `curl -sSf https://proxy.golang.org/go.opentelemetry.io/otel/@v/<version>.mod` shows it.
- **Use:** `import semconv "go.opentelemetry.io/otel/semconv/v1.43.0"`, then
  `semconv.HTTPRequestMethodKey` (an `attribute.Key`) and `semconv.SchemaURL`.
- **Unstable:** no split. Each directory holds every convention of its core release and, as a
  released Go v1 package, keeps them, so a library may import unstable conventions from it.
- **Which core release:** the newest `v1.x.y` directory under `semconv/` at the module's release
  tag. Some releases have none (no `v1.29.0`, say), and the newest core release can be on the
  default branch before any otel release carries it.

  <!-- lookup: go -->
  ```bash
  curl -sSf https://proxy.golang.org/go.opentelemetry.io/otel/@latest | jq -r .Version
  gh api "repos/open-telemetry/opentelemetry-go/contents/semconv?ref=<tag>" --jq '[.[].name | select(startswith("v1."))] | sort_by(ltrimstr("v") | split(".") | map(tonumber)) | last'
  ```

- **Bumps:** Renovate and Dependabot bump the module. Nothing moves the import path: moving to a
  newer core release means changing every import of the old version in the module at once, and
  reading `MIGRATION.md` in the new version's directory. Several versions can coexist in a build,
  but keep one per module.

## Java and Kotlin

- **Package:** `io.opentelemetry.semconv:opentelemetry-semconv:<version>` (stable) and
  `io.opentelemetry.semconv:opentelemetry-semconv-incubating:<version>-alpha` (all conventions,
  stable included), on Maven Central, from
  [semantic-conventions-java](https://github.com/open-telemetry/semantic-conventions-java). Both
  need `io.opentelemetry:opentelemetry-api`. A patch release of the package itself adds a fourth
  component (`1.30.0.1`).
- **Add:** with Gradle, `implementation("io.opentelemetry.semconv:opentelemetry-semconv:<version>")`
  (or the project's version catalog); with Maven, the same coordinates. An Android app supporting
  old API levels also sets the Gradle property `android.useFullClasspathForDexingTransform` for
  debug builds (the package's README, at v1.45.0).
- **Use:** `io.opentelemetry.semconv.HttpAttributes.HTTP_REQUEST_METHOD`; unstable ones in
  `io.opentelemetry.semconv.incubating.*IncubatingAttributes`.
- **Unstable:** the `-incubating` artifact has no compatibility guarantees; its README says
  library instrumentation should not depend on it, and should copy the attributes instead.
- **Which core release:** the package's version.

  <!-- lookup: java -->
  ```bash
  curl -sSf https://repo1.maven.org/maven2/io/opentelemetry/semconv/opentelemetry-semconv/maven-metadata.xml | grep '<release>'
  ```

- **Bumps:** Renovate and Dependabot bump both artifacts. Keep them on the same release: the
  incubating one is the stable version plus `-alpha`.

## JavaScript and TypeScript

- **Package:** `@opentelemetry/semantic-conventions` on npm, from
  [opentelemetry-js](https://github.com/open-telemetry/opentelemetry-js/tree/main/semantic-conventions).
- **Add:** `npm install --save @opentelemetry/semantic-conventions` (or the project's package
  manager). Keep the default range: the package's README says not to pin it exactly
  (`--save-exact`), which leaves several copies in an application's `node_modules`.
- **Use:** `import { ATTR_HTTP_REQUEST_METHOD } from '@opentelemetry/semantic-conventions'`. Names
  are `ATTR_*`, `*_VALUE_*` (enum values), `METRIC_*` and `EVENT_*`; the older `SEMATTRS_*` and
  `SemanticAttributes` forms are deprecated.
- **Unstable:** the `@opentelemetry/semantic-conventions/incubating` entry point, which can break
  in a minor release. The README says instrumentation libraries copy what they need from it
  (e.g. into `src/semconv.ts`) rather than import it at runtime.
- **Which core release:** the package's version.

  <!-- lookup: js -->
  ```bash
  curl -sSf https://registry.npmjs.org/@opentelemetry/semantic-conventions/latest | jq -r .version
  ```

- **Bumps:** Renovate and Dependabot, with no extra configuration.

## Python

- **Package:** `opentelemetry-semantic-conventions` on PyPI, from
  [opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python). Its versions are
  betas (`0.66b2`) released with the API and SDK, and it pins the API exactly
  (`opentelemetry-api == 1.45.2` at v1.45.2), as the SDK pins it.
- **Add:** with the project's tool (`uv add`, `poetry add`, or a requirements line). The version
  has to match the project's `opentelemetry-api` and `opentelemetry-sdk`: take the one released
  with them, not the newest on its own.
- **Use:** `from opentelemetry.semconv.attributes.http_attributes import HTTP_REQUEST_METHOD`;
  metrics under `opentelemetry.semconv.metrics`; schema URLs in
  `opentelemetry.semconv.schemas.Schemas`.
- **Unstable:** `opentelemetry.semconv._incubating`, private by Python's underscore convention.
- **Which core release:** the newest schema `opentelemetry.semconv.schemas` lists, at the
  opentelemetry-python release.

  <!-- lookup: python -->
  ```bash
  gh api repos/open-telemetry/opentelemetry-python/releases/latest --jq .tag_name
  gh api "repos/open-telemetry/opentelemetry-python/contents/opentelemetry-semantic-conventions/src/opentelemetry/semconv/schemas.py?ref=<tag>" --jq '.content | @base64d | split("\n") | map(select(test("^    V1_"))) | last'
  ```

- **Bumps:** bump it together with `opentelemetry-api` and `opentelemetry-sdk` (one Renovate
  group, or Dependabot's `groups`): bumped alone, the exact pins conflict.

## Rust

- **Package:** the `opentelemetry-semantic-conventions` crate, from
  [opentelemetry-rust](https://github.com/open-telemetry/opentelemetry-rust). Its 0.x version
  follows the `opentelemetry` crate's, not the core release.
- **Add:** `cargo add opentelemetry-semantic-conventions`; with unstable conventions,
  `cargo add opentelemetry-semantic-conventions --features semconv_experimental`.
- **Use:** `opentelemetry_semantic_conventions::attribute::HTTP_REQUEST_METHOD` (modules
  `attribute`, `metric`, `resource`, `trace`), and `SCHEMA_URL`.
- **Unstable:** behind the `semconv_experimental` feature, off by default.
- **Which core release:** the crate's `SCHEMA_URL`, at the crate's release tag
  (`opentelemetry-semantic-conventions-<version>`).

  <!-- lookup: rust -->
  ```bash
  curl -sSf -A generic-client https://crates.io/api/v1/crates/opentelemetry-semantic-conventions | jq -r .crate.max_stable_version
  gh api "repos/open-telemetry/opentelemetry-rust/contents/opentelemetry-semantic-conventions/src/lib.rs?ref=opentelemetry-semantic-conventions-<tag>" --jq '.content | @base64d | split("\n") | map(select(contains("SCHEMA_URL"))) | last'
  ```

- **Bumps:** Renovate and Dependabot. Each 0.x minor counts as breaking to Cargo, so bump it with
  the `opentelemetry` crates.

## PHP

- **Package:** `open-telemetry/sem-conv` on Packagist, a read-only split of
  [opentelemetry-php](https://github.com/open-telemetry/opentelemetry-php/tree/main/src/SemConv).
- **Add:** `composer require open-telemetry/sem-conv`.
- **Use:** `OpenTelemetry\SemConv\Attributes\HttpAttributes::HTTP_REQUEST_METHOD`; metrics in
  `OpenTelemetry\SemConv\Metrics`; schema URLs from `OpenTelemetry\SemConv\Version`.
- **Unstable:** `OpenTelemetry\SemConv\Incubating`, stable and experimental conventions together.
  The README says deprecated conventions are removed in the next release, with no compatibility
  guarantee.
- **Which core release:** the package's version. Not every core release gets one.

  <!-- lookup: php -->
  ```bash
  curl -sSf https://repo.packagist.org/p2/open-telemetry/sem-conv.json | jq -r '.packages["open-telemetry/sem-conv"][0].version'
  ```

- **Bumps:** Renovate and Dependabot.

## Ruby

- **Package:** the `opentelemetry-semantic_conventions` gem, from
  [opentelemetry-ruby](https://github.com/open-telemetry/opentelemetry-ruby/tree/main/semantic_conventions).
  Its version is the core release, and it doesn't follow semantic versioning.
- **Add:** `bundle add opentelemetry-semantic_conventions`.
- **Use:** `require 'opentelemetry-semantic_conventions'`, then
  `OpenTelemetry::SemConv::HTTP::HTTP_REQUEST_METHOD`. The `OpenTelemetry::SemanticConventions`
  namespace is the frozen pre-1.36.0 form.
- **Unstable:** `OpenTelemetry::SemConv::Incubating`. The README says incubating constants are
  never removed (a stabilized one is also copied to the stable namespace), so a library may use
  them.
- **Which core release:** the gem's version.

  <!-- lookup: ruby -->
  ```bash
  curl -sSf https://rubygems.org/api/v1/versions/opentelemetry-semantic_conventions/latest.json | jq -r .version
  ```

- **Bumps:** Renovate and Dependabot.

## C++

- **Package:** headers under `api/include/opentelemetry/semconv/` in
  [opentelemetry-cpp](https://github.com/open-telemetry/opentelemetry-cpp), so it comes with the
  API and moves with its releases. There is no separate package.
- **Add:** through however the project already gets opentelemetry-cpp (CMake, vcpkg, conan, a
  submodule).
- **Use:** `#include "opentelemetry/semconv/http_attributes.h"`, then
  `opentelemetry::semconv::http::kHttpRequestMethod`; `semconv::kSchemaUrl` from `schema_url.h`.
- **Unstable:** headers under `semconv/incubating/`.
- **Which core release:** `kSchemaUrl` at the opentelemetry-cpp release.

  <!-- lookup: cpp -->
  ```bash
  gh api repos/open-telemetry/opentelemetry-cpp/releases/latest --jq .tag_name
  gh api "repos/open-telemetry/opentelemetry-cpp/contents/api/include/opentelemetry/semconv/schema_url.h?ref=<tag>" --jq '.content | @base64d | split("\n") | map(select(contains("kSchemaUrl"))) | .[0]'
  ```

- **Bumps:** only as part of the opentelemetry-cpp version, however the project pins it.

## Swift

- **Package:** inside the `OpenTelemetryApi` product of
  [opentelemetry-swift-core](https://github.com/open-telemetry/opentelemetry-swift-core) (not the
  `opentelemetry-swift` repo), so it moves with the API's releases.
- **Add:** `.package(url: "https://github.com/open-telemetry/opentelemetry-swift-core", from:
  "<version>")`, with `.product(name: "OpenTelemetryApi", package: "opentelemetry-swift-core")`.
- **Use:** `SemanticConventions.Http.requestMethod` (an enum case; `.rawValue` is the name).
- **Unstable:** no split.
- **Which core release:** `SEMCONV_VERSION` in its generation script, at the release tag. It lags
  the core registry by several releases.

  <!-- lookup: swift -->
  ```bash
  gh api repos/open-telemetry/opentelemetry-swift-core/releases/latest --jq .tag_name
  gh api "repos/open-telemetry/opentelemetry-swift-core/contents/Scripts/semantic-convention/generate.sh?ref=<tag>" --jq '.content | @base64d | split("\n") | map(select(startswith("SEMCONV_VERSION="))) | .[0]'
  ```

- **Bumps:** Renovate's and Dependabot's Swift support bump the package; the conventions change
  only when the SIG regenerates them.

## Erlang and Elixir

- **Package:** `opentelemetry_semantic_conventions` on Hex, from
  [opentelemetry-erlang](https://github.com/open-telemetry/opentelemetry-erlang/tree/main/apps/opentelemetry_semantic_conventions).
- **Add:** `{:opentelemetry_semantic_conventions, "~> <version>"}` in `mix.exs`, or
  `{opentelemetry_semantic_conventions, "<version>"}` in `rebar.config`.
- **Use:** Erlang, `-include_lib("opentelemetry_semantic_conventions/include/attributes/http_attributes.hrl").`
  then `?HTTP_REQUEST_METHOD`; Elixir, `OpenTelemetry.SemConv.HTTPAttributes.http_request_method()`.
- **Unstable:** `include/incubating/` headers and `OpenTelemetry.SemConv.Incubating.*` modules.
- **Which core release:** the package's version. It is far behind the core registry: check
  before relying on it.

  <!-- lookup: erlang -->
  ```bash
  curl -sSf https://hex.pm/api/packages/opentelemetry_semantic_conventions | jq -r .latest_stable_version
  ```

- **Bumps:** Renovate and Dependabot, when there is a release to bump to.

## .NET

No package: opentelemetry-dotnet keeps its semantic conventions internal, and the NuGet package
`OpenTelemetry.SemanticConventions` has only an old release candidate (`1.0.0-rc9.9`). Packages
with similar names from other publishers aren't OpenTelemetry's. Generate the constants with
weaver instead.
