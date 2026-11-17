---
name: otel-semconv-consume
description: Use the OpenTelemetry core semantic conventions in a project through the constants package its language SIG publishes (Go, Java and Kotlin, JavaScript and TypeScript, Python, Rust, PHP, Ruby, C++, Swift, Erlang and Elixir), with no code generation. Use when a project needs attribute, metric or event names from the core semantic conventions registry, e.g. to replace hard-coded names like "http.request.method" with constants, or to add the semantic conventions dependency to an application, service, SDK or instrumentation library.
---

# Using the core semantic conventions from a published package

Most OpenTelemetry language SIGs publish the core registry's conventions as a package of constants,
generated from each release of [semantic-conventions](https://github.com/open-telemetry/semantic-conventions).
A project that needs only the core registry depends on that package: there is nothing to generate,
validate or keep in step by hand. `reference/languages.md` has each language's package, how to add
and import it, how it splits stable from unstable conventions, and which core release it carries.

## When this is the wrong tool

Generate the code with weaver instead (outside this skill) when the project needs:

- conventions from a registry other than the core one (a federated registry that extends it), or
  conventions of its own;
- a language with no published package (.NET: `reference/languages.md`);
- a convention the latest package doesn't have yet, because it lags the core registry, and the
  project can't wait for the next release. Say how far behind it is (step 1.5) and let the user
  choose.

## 1. Gather facts

1. **Language and build tool**, and where the project declares dependencies (`go.mod`,
   `build.gradle(.kts)` or a version catalog, `pom.xml`, `package.json`, `pyproject.toml` or
   `requirements*.txt`, `Cargo.toml`, `composer.json`, `Gemfile`, `mix.exs` or `rebar.config`,
   `Package.swift`, CMake with vcpkg or conan). In a monorepo, the module that needs it.
2. **Library or application.** A library (an instrumentation library, an SDK, anything other
   projects depend on) uses only stable conventions from the package, and copies the unstable ones
   it needs into its own code, unless the language's package promises that its unstable constants
   never change or go away (Go and Ruby do: `reference/languages.md`). An application may use the
   unstable ones from the package. This is the core registry's own guidance ([code generation,
   at semantic-conventions v1.45.0](https://github.com/open-telemetry/semantic-conventions/blob/v1.45.0/docs/non-normative/code-generation.md#stability-and-versioning):
   the version this was last checked against). A package's stable part makes the semantic
   versioning promises; the unstable part can break in any release.
3. **What the project already has:** an existing dependency on the package, or on the
   OpenTelemetry API or SDK that pins or bundles it (`reference/languages.md` says where it does),
   and hard-coded convention names (`"http.request.method"`) or copies of constants to replace.
4. **Which conventions it uses**, and whether each is stable: a constant in the package's stable
   part is stable; one only in the unstable part isn't.
5. **Which core release the package carries.** Look up the latest package release and the core
   release it carries (`reference/languages.md`, "Which core release"), and the core registry's
   latest release: `gh api repos/open-telemetry/semantic-conventions/releases/latest --jq .tag_name`.
   Tell the user when the package is behind, and by how much.

## 2. Add the dependency

Use the build tool's own command where it has one (`go get`, `npm install`, `cargo add`,
`composer require`, `bundle add`, the project's Python tool), so the lock file follows; otherwise
edit the declaration the way the project declares its other dependencies (a version catalog, a
BOM, a version range). Take the latest release unless the project's constraints rule it out (its
minimum language version, the OpenTelemetry API or SDK version it is on); say which release you
chose and why. Follow the ecosystem's convention for how tightly to pin, which
`reference/languages.md` gives where the SIG states one.

## 3. Use the constants

- Replace each hard-coded convention name with its constant. Keep the value the code emits
  unchanged: if a hard-coded name has no constant (it is deprecated, renamed, or not in the core
  registry), leave it and list it in the hand-over.
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

1. The project builds and its tests pass, with its own commands.
2. The constants resolve to the names the code emitted before: for any name you replaced, the
   value is the same string. A changed value changes the telemetry the project sends; call it out
   instead.
3. One core release per module: the imports or the dependency name one version (Go: every
   `go.opentelemetry.io/otel/semconv/v1.x.y` import in a module names the same `v1.x.y`).
4. A library imports nothing from the package's unstable part outside tests, unless step 1.2's
   exception applies.
5. The package comes from its registry, not copied into the repo; only the unstable conventions
   step 1.2 copies are in the project's own code.

## 6. Hand over

Say which package and release you added and the core release it carries (and how far behind the
latest core release it is), what you replaced, any hard-coded names left and why, which unstable
conventions are copied or imported, and how bumps will arrive (Renovate or Dependabot, or by hand
for Go).
