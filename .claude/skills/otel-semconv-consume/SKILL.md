---
name: otel-semconv-consume
description: Use the OpenTelemetry core semantic conventions in a project through the constants package its language SIG publishes for other projects to depend on (Go, Java and Kotlin on opentelemetry-java, JavaScript and TypeScript, Python), with no code generation; for Kotlin Multiplatform, opentelemetry-kotlin and Swift, where the constants are part of the SDK, it points to generating them instead, asking first when the project already uses the SDK's constants. Use when a project needs attribute, metric or event names from the core semantic conventions registry, e.g. to replace hard-coded names like "http.request.method" with constants, or to add the semantic conventions dependency to an application, service, SDK or instrumentation library.
---

# Using the core semantic conventions from a published package

Several OpenTelemetry language SIGs publish the core registry's conventions as a package of
constants for other projects to depend on, generated from each release of
[semantic-conventions](https://github.com/open-telemetry/semantic-conventions). A project that
needs only the core registry depends on that package: there is nothing to generate, validate or
keep in step by hand. `reference/languages.md` has each language's package, how to add and import
it, how it splits stable from unstable conventions, and which core release it carries.

## When this is the wrong tool

Generate the code with weaver instead (the otel-semconv-codegen skill, where it is installed) when
the project needs:

- a language with no such package: any language `reference/languages.md` doesn't cover, including
  Kotlin Multiplatform, Kotlin on opentelemetry-kotlin, and Swift, whose constants are part of
  their SDK rather than a package of their own (`reference/languages.md` says why). A project
  that already uses its SDK's constants isn't moved without asking: find its hard-coded names
  (step 1.3), say that the constants it uses are the SDK's rather than a published package, and
  ask the user whether to keep using them for this change or generate its own;
- conventions from a registry other than the core one (a federated registry that extends it), or
  conventions of its own;
- a convention the latest package doesn't have yet, because it lags the core registry, and the
  project can't wait for the next release. Say how far behind it is (step 1.5) and let the user
  choose.

## 1. Gather facts

1. **Language and build tool**, and where the project declares dependencies (`go.mod`,
   `build.gradle(.kts)` or a version catalog, `pom.xml`, `package.json`, `pyproject.toml` or
   `requirements*.txt`). In a monorepo, the module that needs it. For Kotlin, which OpenTelemetry
   API it records with: on opentelemetry-java it uses the Java package; on opentelemetry-kotlin, or
   in Kotlin Multiplatform code, this is the wrong tool (above).
2. **Library or application.** A library (an instrumentation library, an SDK, anything other
   projects depend on) uses only stable conventions from the package, and copies the unstable ones
   it needs into its own code, unless the language's package promises that its unstable constants
   never change or go away (Go's does: `reference/languages.md`). An application may use the
   unstable ones from the package. This is the core registry's own guidance ([code generation,
   at semantic-conventions v1.45.0](https://github.com/open-telemetry/semantic-conventions/blob/v1.45.0/docs/non-normative/code-generation.md#stability-and-versioning):
   the version this was last checked against). A package's stable part makes the semantic
   versioning promises; the unstable part can break in any release.
3. **What the project already has:** an existing dependency on the package, or on the
   OpenTelemetry API, SDK or a BOM that pins or bundles it (`reference/languages.md` says where it
   does), and the release it resolves now (the lock file, or the build tool's dependency report,
   e.g. Gradle's `dependencyInsight`). Then the hard-coded convention names
   (`"http.request.method"`) or copies of constants to replace: search the source files, and the
   file or package that defines the names the code uses where that is elsewhere, for dotted names
   in single or double quotes (`rg -n -o -e "[\"'][a-z][a-z0-9_]*\.[a-z0-9_.-]+[\"']" <dir>`), and
   keep the core conventions: the ones the package has a constant for, and the ones it leaves out
   that the core registry still defines, deprecated ones included. The rest (the project's own
   names, platform properties) aren't core conventions. The search doesn't find undotted names
   (an event named `exception`), names built from a prefix (`"browser.web_vital." + key`), enum
   values the code sets (`"webjs"` for `telemetry.sdk.language`), or the package's own deprecated
   forms already imported (`reference/languages.md` names them where a package has any): look for
   those too.

   To check a name against the core registry, download its source at the latest core release
   (step 1.5's `gh api` command prints it) into a scratch directory and search its `model/`:

   ```bash
   curl -sSfL -o <dir>/semconv.tar.gz https://github.com/open-telemetry/semantic-conventions/archive/refs/tags/v<release>.tar.gz
   tar -xzf <dir>/semconv.tar.gz -C <dir>
   rg -n -e 'id: <name>$' -e 'key: <name>$' -e 'name: <name>$' <dir>/semantic-conventions-<release>/model
   ```

   A match counts only where it defines an attribute, a metric or an event; the files are in
   either format, which each file's `file_format:` line says (none means definition/1):
   - **definition/2:** `key:` (an attribute), or a `- name:` under `metrics:` or `events:`;
   - **definition/1:** an `- id:` under `attributes:`, a `metric_name:`, or the `name:` of a group
     with `type: event`.

   Other matches don't count: a group's own `id:` (attribute group `source`) or an entity's
   `name:` (`service`) isn't a convention a constant stands for. No counted match means it isn't
   a core convention; a match in a `deprecated/` directory or a `*deprecated.yaml` file means it
   is deprecated. A core name with no constant in the package release the project will take is
   one the package leaves out, or one newer than that release ("When this is the wrong tool": say
   so). Where the download isn't possible, read the files one at a time:
   `gh api "repos/open-telemetry/semantic-conventions/contents/model/<dir>?ref=v<release>"` lists
   a directory, and adding `-H "Accept: application/vnd.github.raw"` to a file's path prints it.
4. **Which conventions it uses**, and whether each is stable in the core registry.
   `reference/languages.md` says how each package shows it. Where the package doesn't, the
   registry does: read the file the step 1.3 lookup matched, from the matched line down to that
   definition's `stability:` (or `deprecated:`), which can come after a long brief and note.
5. **Which core release the package carries.** Look up the latest package release and the core
   release it and the resolved one carry (`reference/languages.md`, "Which core release"), and the
   core registry's latest release:
   `gh api repos/open-telemetry/semantic-conventions/releases/latest --jq .tag_name`.
   Tell the user when the package is behind, and by how much.
6. **Ask about unstable and deprecated names** before changing code, listing the hard-coded names
   and enum values steps 1.3 and 1.4 found in each group, with where they are. List only those
   step 3 would replace: not test literals that pin a name, or names where a constant can't go.
   - **Unstable names:** convert them to the package's constants (imported in an application,
     copied into one file in a library, per step 1.2), or leave them hard-coded?
   - **Deprecated names the package still has a constant for:** use the deprecated constant (the
     default: the emitted name doesn't change, and the deprecation becomes visible in the code),
     or leave them hard-coded? Where the package has a deprecated constant only in its unstable
     part (Java's `-incubating`, say), a library takes it as an unstable one: copied, per step 1.2.

   Stable names need no question, nor does a stable name whose only constant is in the package's
   unstable part (Java's metric names): an application imports it, a library copies it. With
   neither group to list, this step asks nothing. A package behind the core release a name needs
   is a separate choice ("When this is the wrong tool"), asked either way, alongside these
   questions when there are any. Step 3 follows the answers.

## 2. Add the dependency

Use the build tool's own command where it has one (`go get`, `npm install`, the project's Python
tool), so the lock file follows; otherwise edit the declaration the way the project declares its
other dependencies (a version catalog, a BOM, a version range). Take the latest release unless
the project's constraints rule it out (its minimum language or tools version, the OpenTelemetry
API or SDK version it is on, a minimum release age in its Renovate config); say which release you
chose and why. Follow the ecosystem's convention for how tightly to pin, which
`reference/languages.md` gives where the SIG states one. When the project already resolves the
latest release it can take, there is nothing to add: say so.

## 3. Use the constants

- Replace each hard-coded convention name, and enum value, with its constant: the stable ones,
  and the unstable and deprecated ones as the user chose in step 1.6. Keep the value the code
  emits unchanged: replace a name only with a constant of the same name, never with the one a
  deprecated name was renamed to, and a value only with a constant from the same attribute's enum
  (`"GET"` set on the deprecated `http.method` isn't `http.request.method`'s). Moving to the new
  names changes the telemetry the project sends and is a separate job: don't offer it. A
  deprecated form of a constant (an older class or prefix for the same name,
  `reference/languages.md`) is replaced with the current constant for that name, which emits the
  same value. If a hard-coded name has no constant (the package leaves it out, or it isn't in the
  core registry), or sits where a constant can't go (a Go struct tag, a comment), leave it and
  list it in the hand-over.
- In tests, a literal that pins a name on the wire (what the code emits, or what it reads from
  other systems) stays a literal: a constant compared with itself doesn't pin it. Other test uses
  may take the constants.
- Imports the project already has that the rules here advise against (a library's constants for
  unstable or deprecated names) are listed in the hand-over, not restructured, unless the user
  asks.
- The schema URL, where the code sets one, comes from the same package and version as the
  constants.
- In a library that copies unstable conventions (step 1.2), put the copies in one file of their
  own (e.g. `src/semconv.ts`), not scattered through the code. The file says which core
  release the copies come from, so a later bump can review them.

## 4. Keeping it current

Where the repo runs Renovate or Dependabot, their standard managers for the language bump most of
these packages; the exceptions, per language, are in `reference/languages.md`. The one that always
needs a person is Go: the core release is in the import path, so no tool moves code to a newer
one. A newer core release can rename, deprecate or remove an unstable convention, so on a bump
review the unstable ones the project uses, copied or imported.

## 5. Verify

1. The project's own checks pass: what its CI runs (build, tests, lint, generated files such as
   license notices), not only build and test. Where no test runs the changed code, run it once
   (import the module, start the code path) to show it still loads.
2. The constants resolve to the names the code emitted before: for any name you replaced, the
   value is the same string. A changed value changes the telemetry the project sends; call it out
   instead. An OpenTelemetry API or SDK bump made with the package can change what the project
   emits too (an SDK release that adds a resource attribute): check its release notes and say so.
   A library that re-exports the package (Gradle's `api(...)`) changes its own public API with
   the bump: say that too.
3. One core release per module: the imports or the dependency name one version (Go: every
   `go.opentelemetry.io/otel/semconv/v1.x.y` import in a module names the same `v1.x.y`).
4. A library's change adds no import from the package's unstable part outside tests, unless step
   1.2's exception applies; the ones it already had are in the hand-over.
5. The package comes from its registry, not copied into the repo; only the unstable conventions
   step 1.2 copies are in the project's own code.

## 6. Hand over

Say which package and release you added and the core release it carries (and how far behind the
latest core release it is), what you replaced, any hard-coded names left and why, which unstable
conventions are copied or imported and which deprecated constants are used, and how bumps will
arrive (Renovate or Dependabot, or by hand for Go and where the repo runs neither).
