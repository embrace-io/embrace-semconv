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
| Java, and Kotlin on opentelemetry-java | `io.opentelemetry.semconv:opentelemetry-semconv` | yes | separate `-incubating` artifact |
| JavaScript, TypeScript | `@opentelemetry/semantic-conventions` | yes | `/incubating` entry point |
| Python | `opentelemetry-semantic-conventions` | no (beta versions) | `opentelemetry.semconv._incubating` |

**No package to depend on.** In these, the constants are part of the SDK, versioned with it,
rather than a semantic conventions package published for other projects to depend on, so a
project in one of them generates its own with weaver (SKILL.md, "When this is the wrong tool"):

- **Kotlin Multiplatform, and Kotlin on opentelemetry-kotlin:** `io.opentelemetry.kotlin:semconv`
  is opentelemetry-kotlin's own. Its version is the SDK's, and its README covers only
  regenerating it.
- **Swift:** the constants are part of the `OpenTelemetryApi` library (opentelemetry-swift-core,
  and opentelemetry-swift), not a package of their own, and they move with the SDK's releases:
  swift-core 2.6.0 carries core 1.38.0, and from 2.4.1 it needs a Swift 6 toolchain.

A project that already uses one of these: SKILL.md, "When this is the wrong tool", says to ask
the user first.

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
  `semconv.HTTPRequestMethodKey` (an `attribute.Key`) and `semconv.SchemaURL`. The keys are
  declared in the directory's `attribute_group.go` (`attribute.Key("http.request.method")`), each
  with its stability in its doc comment (`// Stability: Stable`, `// Stability: Development`).
- **Unstable:** no split. Each directory holds its core release's conventions and, as a released
  Go v1 package, keeps them, so a library may import unstable conventions from it. Deprecated
  names and some language-specific namespaces (there is no `jvm.*`) are left out: a name with no
  constant there stays hard-coded.
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

## Java and Kotlin on opentelemetry-java

For Java, and for Kotlin that records through opentelemetry-java (JVM or Android): the constants
are Java fields, used the same way from Kotlin.

- **Package:** `io.opentelemetry.semconv:opentelemetry-semconv:<version>` (stable) and
  `io.opentelemetry.semconv:opentelemetry-semconv-incubating:<version>-alpha` (all conventions,
  stable included), on Maven Central, from
  [semantic-conventions-java](https://github.com/open-telemetry/semantic-conventions-java). Both
  need `io.opentelemetry:opentelemetry-api`. A patch release of the package itself adds a fourth
  component (`1.30.0.1`).
- **Add:** with Gradle, `implementation("io.opentelemetry.semconv:opentelemetry-semconv:<version>")`
  (or the project's version catalog); with Maven, the same coordinates. An Android app supporting
  old API levels also sets the Gradle property `android.useFullClasspathForDexingTransform` for
  debug builds (the package's README, at v1.45.0). The OpenTelemetry instrumentation BOMs manage
  them, often a release behind: `io.opentelemetry.instrumentation:opentelemetry-instrumentation-bom`
  the stable artifact, `opentelemetry-instrumentation-bom-alpha` the `-incubating` one. A project on
  one resolves the BOM's release unless it declares its own version.
- **Use:** `io.opentelemetry.semconv.HttpAttributes.HTTP_REQUEST_METHOD`, an `AttributeKey`
  (`.getKey()` is the name, for an API that takes a `String`); unstable ones in
  `io.opentelemetry.semconv.incubating.*IncubatingAttributes`. Metric names are `String`s in
  `io.opentelemetry.semconv.incubating.*IncubatingMetrics` (`HTTP_SERVER_REQUEST_DURATION_NAME`).
- **Unstable:** the `-incubating` artifact has no compatibility guarantees; its README says
  library instrumentation should not depend on it, and should copy the attributes instead. The
  stable artifact holds attributes only: every metric name, stable ones included, is in
  `-incubating`, so a metric's stability comes from the core registry (SKILL.md step 1.4), and a
  library copies the metric names it needs.
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
  manager); in a workspaces monorepo, in the package that needs it (`-w <workspace>`), not the
  root. Keep the default range: the package's README says not to pin it exactly
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
  betas (`0.66b2`) released with the API and SDK, and the three pin each other exactly: 0.66b2
  pins `opentelemetry-api==1.45.2`, and SDK 1.45.2 pins both.
- **Add:** with the project's tool (`uv add`, `poetry add`, or a requirements line). Because of
  the exact pins, it moves only as a group with `opentelemetry-api` and `opentelemetry-sdk` (and
  the project's other `opentelemetry-*` packages released with them): the latest release means
  moving the whole group, which SKILL.md step 5.2's note on SDK bumps covers; otherwise take the one
  released with the API the project is on. A version's API pin:
  `curl -sSf https://pypi.org/pypi/opentelemetry-semantic-conventions/<version>/json | jq -r '.info.requires_dist[]'`
  (0.61b0 pins `opentelemetry-api==1.40.0`).
- **Use:** `from opentelemetry.semconv.attributes.http_attributes import HTTP_REQUEST_METHOD`;
  metrics under `opentelemetry.semconv.metrics`; schema URLs in
  `opentelemetry.semconv.schemas.Schemas`. The `opentelemetry.semconv.resource.ResourceAttributes`
  and `opentelemetry.semconv.trace.SpanAttributes` classes are deprecated since 1.25.0: type
  checkers flag them, but nothing warns at runtime.
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
