# Templates and codegen

Weaver templates are Jinja files plus a `weaver.yaml` whose `jq` filters select what each one
renders. A project keeps them in `templates/registry/<target>/`, one directory per target
(`markdown` for docs, a language name for codegen). Always render with `--v2`: filters and
templates then see weaver's v2 resolved registry.

Weaver's template docs: https://github.com/open-telemetry/weaver/blob/main/crates/weaver_forge/README.md

## What the templates see

The context's top-level keys are `registry`, `dependencies`, `dependency_graph`, `refinements`
and `schema_url`. Under `registry`, each collection may be absent (use `// []`):

- `.registry.attributes`: the attributes the registry **defines**, plus the attributes of every
  attribute group it **imports** from a dependency. Fields: `key`, `brief`, `type` (a string, or
  a mapping with `members` for enums), `stability`; `note`, `examples` and `deprecated` when set;
  `provenance.source`. `type` is one of weaver's type names (`string`, `int`, `double`,
  `boolean`, `any`, their arrays such as `string[]`, and `template[...]` forms of each), or a
  mapping with `members` for an enum. `examples` is a list, or a single value (a string, number
  or boolean). An enum member always has `id` and `value`; the value is a string (the member's
  `id` when its definition omits it), an integer, a double or a boolean. Its `brief`, `stability`
  and `deprecated` are set only when its definition sets them.
- `.registry.attribute_groups`: the registry's own public groups (internal ones are folded into
  the public groups that include them, then dropped), each with `id`, `brief`, `stability` and
  `attributes` (an empty list for a group with none); `note` when set. Imported groups are
  **not** listed here: their attributes are flattened into `.registry.attributes` instead.
- `.registry.events`, `.registry.metrics`, `.registry.spans`, `.registry.entities`: signals,
  identified by `name` (events, metrics) or `type` (spans, entities), each with `brief` and
  `stability`; a metric also has `instrument` and `unit`, a span `kind` and a `name`, an entity
  `identity`. A span's `name.note` and `name.templates` are set only when its definition sets
  them. A signal's own `requirement_level`, `note` and `attributes` are set only when its
  definition sets them (weaver accepts a signal without a `requirement_level`, with a warning);
  each of its attributes carries a `requirement_level`, `recommended` when the reference sets
  none.
- Weaver rejects a definition missing any field listed above without a qualifier, so a template
  may use those directly; test the others (`{% if attribute.note %}`, `| default([])`) before
  using them (verified with weaver 0.28.0).
- `provenance.source` on every definition is the `schema_url` of the registry it came from, and
  absent (null) for the registry's own. Docs filter on it to cover only local definitions.

**A dependency's attribute that the registry only references** (`- ref: session.id` in one of
its groups or signals) is **not** in `.registry.attributes`: it appears only inline, in the
`attributes` of the group or signal that references it (verified with weaver 0.28.0). So a
codegen template that iterates `.registry.attributes` silently leaves out every referenced
dependency attribute. Codegen from a registry of the project's own collects attributes from
where they actually are:

```yaml
# weaver.yaml filter: every attribute the registry defines or references, once each; nothing
# that only an import brings in (verified with weaver 0.28.0 on the template test's fixture)
filter: >
  (((.registry.attributes // []) | map(select(.provenance.source | not)))
   + ([(.registry.attribute_groups // [])[] | .attributes[]])
   + ([(.registry.events // [], .registry.metrics // [], .registry.spans // [],
        .registry.entities // [])[] | select(.provenance.source | not)
       | .attributes // [] | .[]]))
  | unique_by(.key)
```

Group attributes carry the attribute's own fields plus a `requirement_level` that is always
`recommended` (verified with weaver 0.28.0 on the template test's fixture); signal attributes
carry the
signal's own `requirement_level`, and may carry a brief the signal refined. `unique_by` keeps
the first copy of each key, so the concatenation above goes definition first: a
registry-defined attribute keeps its own brief,
and a referenced dependency attribute takes its first group's copy before any signal's. Don't
rely on `requirement_level` in an attribute template.

The two provenance filters keep out what imports bring in: every attribute of an imported group,
and the attributes of imported signals. Without them, an import added only to satisfy a policy
(a key deprecated with `renamed_to` a dependency's attribute needs one) adds public constants. Drop the first when the project wants
the imported groups' attributes too, and the second when its templates render imported signals
("Testing templates"): that code needs their attributes.

Import rather than reference when the project wants everything a dependency's group holds;
reference when it wants a few attributes.

## Choosing what to generate

Generating straight from a registry (`SOURCE_REGISTRY`) covers everything it defines. For only
some of its keys, select them in the template's filter: list the keys, or take a namespace, which
also picks up the keys a later release adds to it (verified with weaver 0.28.0 on the template
test's fixture; its jq has no `IN`, so a list is matched with `any`):

```yaml
# templates/registry/<target>/weaver.yaml: one file of the listed keys
templates:
  - pattern: attributes.<ext>.j2
    filter: >
      [{ id: "selected",
         attributes: ((.registry.attributes // [])
           | map(select(.provenance.source | not))
           | map(select(.key as $key
               | (["<key>", "<key>"] | any(. == $key))
                 or ($key | startswith("fixture."))))) }]
    application_mode: each
    file_name: "{{ ctx.id | camel_case }}Attributes.<ext>"
```

For a namespace, the last `map` is
`map(select(.key | startswith("<namespace>.") or startswith("fixture.")))`. Either way the
`fixture.*` part is for the templates test: the fixture's keys are `fixture.*`, the golden files
come out empty without it and the test proves nothing, and it selects nothing in the source
registry.

## Choosing how to split output

- **One file per public attribute group**: `filter: .registry.attribute_groups // []` with
  `application_mode: each`. Right for registries whose public groups are the
  export surface and a consumer's own groups say exactly what it uses. It works with the
  `attributes` collection alone: that fixture exports its attributes through
  `registry.fixture.defined` (the `attribute-groups` fixture adds `registry.fixture`). A filter
  that selects groups by ID must match those too, or the golden files come out empty and the
  templates test proves nothing: replace an existing ID-prefix filter (`startswith("acme.")`)
  with the provenance filter, `map(select(.provenance.source | not))`. Name the file from the
  whole ID (e.g. `{{ ctx.id | replace('registry.', '') | replace('.', '_') | camel_case }}`
  plus `Attributes.ts`), and check
  the golden files' names: a `file_name` expression that comes out empty renders silently.
- **One file per namespace**: group the attributes by the first segment of `key`, as the markdown
  templates do. Right for **the core registry**, most of which is still v1 syntax: rendered
  directly, the core registry exposes only a handful of public attribute groups to `--v2`
  templates, yet hundreds of attributes (weaver 0.28.0 with core registry 1.44.0: 4 groups, 940
  attributes in 90 namespaces).

```yaml
# templates/registry/<target>/weaver.yaml, one file per namespace
templates:
  - pattern: attributes.<ext>.j2
    filter: >
      (.registry.attributes // [])
      | map(select(.provenance.source | not))
      | group_by(.key | split(".") | .[0])
      | map({ namespace: (.[0].key | split(".") | .[0]), attributes: . })
    application_mode: each
    file_name: "{{ ctx.namespace | snake_case }}_attributes.<ext>"
```

A file that doesn't depend on the registry but has to live among the generated code (an
annotation class, a package marker) is rendered by its own template with
`application_mode: single` (and `filter: "{}"` when it uses nothing from the registry), so
`GENERATED_DIR` still holds only generated files.

## Writing the Jinja

- Case filters for identifiers: `pascal_case`, `camel_case`, `snake_case`,
  `screaming_snake_case`, `kebab_case` (e.g. `session.previous_id` → `SessionPreviousId`,
  `sessionPreviousId`, `session_previous_id`, `SESSION_PREVIOUS_ID`, `session-previous-id`).
  Pick what the language's style guide expects.
- **Line breaks at both ends.** Start a template with a comment ending `-#}` (`{# name.j2 -#}`),
  or the file starts with a blank line. Weaver drops a template's last line break, so a file
  that must end with a newline ends with `{{- "\n" -}}`, or
  with an extra blank line.
- **Escape every string for the language.** Briefs contain quotes, backticks, backslashes and
  comment terminators; a brief from the core registry that starts and ends with `"` breaks a
  Python `"""` docstring, and `*/` ends a KDoc or JSDoc comment. Use `replace` filters suited to
  the target's string and comment syntax.
- **Keep deprecated attributes**, with the language's deprecation marker (`@Deprecated`,
  `@deprecated`, `DeprecationWarning`): consumers compile against them, and dropping a constant
  when its attribute is deprecated breaks their builds. After case conversion a deprecated key
  can collide with its replacement (`process.context_switch_type` and
  `process.context_switch.type` both become `PROCESS_CONTEXT_SWITCH_TYPE`): name one apart
  rather than dropping it. Leave deprecated attributes out only of code nobody compiles against
  yet. In a build that treats warnings as errors, code using a deprecated constant then fails
  to compile until it moves to the replacement: say so to the user.
- **Map each type explicitly, and fall back safely.** Test for every kind of value the template
  handles (`is string`, `is boolean`, `is integer`, `is float`) and give each its platform type;
  for anything else, emit the safest type (a string) with a warning comment in the generated
  code, so a kind of value nobody planned for shows up in review instead of as wrong code. An
  enum member's value, in Kotlin:

  ```jinja
  {%- set name = member.id | screaming_snake_case %}
  {%- if member.value is string %}
  const val {{ name }}: String = "{{ member.value | replace("\\", "\\\\") | replace("\"", "\\\"") | replace("$", "\\$") }}"
  {%- elif member.value is boolean %}
  const val {{ name }}: Boolean = {{ member.value }}
  {%- elif member.value is integer %}
  const val {{ name }}: Long = {{ member.value }}L
  {%- elif member.value is float %}
  const val {{ name }}: Double = {{ member.value }}
  {%- else %}
  // WARNING: enum member value of an unexpected type, generated as a String.
  const val {{ name }}: String = "{{ member.value }}"
  {%- endif %}
  ```

  The same applies to an attribute's `type` when the generated code is typed by it.
- Sort output (`sort(attribute="key")`) so regeneration is deterministic and
  `assert-no-drift` stays quiet.
- **Match the project's conventions for generated code**: header comment, package or module
  declaration, and formatting. Emit code its formatter and linter already accept, rather than
  formatting it afterwards: CI compares committed code with a fresh `make generate` before
  `validate-generated` runs, and a validate target must not change files. `validate-generated`
  then runs the formatter or linter in check mode; a linter that can only auto-correct (writes
  files) stays out of it, and the generated directory is usually excluded from it anyway. A host
  formatter finds its config by the working directory: run it from inside the repo (the make
  targets do), or point it at the config explicitly.

Minimal examples, all verified with weaver 0.28.0:

```jinja
{# attributes.kt.j2 -#}
// Generated from {{ ctx.id }}. Do not edit.
object {{ ctx.id | split('.') | last | pascal_case }}Attributes {
{%- for attribute in ctx.attributes | sort(attribute="key") %}
    /** {{ attribute.brief | trim | replace('*/', '*&#47;') }} */
    const val {{ attribute.key | screaming_snake_case }} = "{{ attribute.key }}"
{%- endfor %}
}
```

```jinja
{# attributes.py.j2 -#}
"""Attribute keys in the `{{ ctx.namespace }}` namespace. Generated; do not edit."""
{% for attribute in ctx.attributes | sort(attribute="key") %}
{{ attribute.key | screaming_snake_case }} = "{{ attribute.key }}"
"""{{ attribute.brief | trim | replace('\\', '\\\\') | replace('"', '\\"') }}"""
{% endfor %}
```

```jinja
{# attributes.ts.j2 (weaver.yaml: file_name "{{ ctx.namespace | camel_case }}Attributes.ts") -#}
// Attribute keys in the `{{ ctx.namespace }}` namespace. Generated; do not edit.
{%- for attribute in ctx.attributes | sort(attribute="key") %}

/**
 * {{ attribute.brief | trim | replace("\n", " ") | replace("*/", "*&#47;") }}
{%- if attribute.deprecated %}
 * @deprecated {{ (attribute.deprecated.note or "Deprecated.") | trim | replace("\n", " ") | replace("*/", "*&#47;") }}
{%- endif %}
 */
export const KEY_{{ attribute.key | screaming_snake_case }} = '{{ attribute.key }}';
{%- endfor %}
{{- "\n" -}}
```

The examples ignore line length. The fixture's long key shows whether the project's formatter
accepts the output: where it doesn't, break long lines in the template the way the formatter
would.

## Starting from a SIG's templates

No shared codegen templates exist: `opentelemetry-weaver-packages` publishes only docs templates.
Each language SIG that publishes the core registry's constants, in a package for them or as part
of its SDK, generates them with weaver templates of its own, written for its own package's layout
and names. For one of these languages, read the SIG's templates before writing new ones, and
borrow what fits (type mapping, escaping, deprecation markers), then adapt the rest to the
project; don't point weaver at them directly. The folders, at the releases these were last
checked against:

| Language | Templates |
|---|---|
| Go | [`semconv/templates/registry/go`](https://github.com/open-telemetry/opentelemetry-go/tree/v1.47.0/semconv/templates/registry/go) in opentelemetry-go v1.47.0 |
| Java | [`buildscripts/templates/registry/java`](https://github.com/open-telemetry/semantic-conventions-java/tree/v1.45.0/buildscripts/templates/registry/java) (and `incubating_java`) in semantic-conventions-java v1.45.0 |
| Kotlin (plain `String` constants, for any OpenTelemetry API) | [`semconv/templates/registry/kotlin`](https://github.com/open-telemetry/opentelemetry-kotlin/tree/v0.10.0/semconv/templates/registry/kotlin) in opentelemetry-kotlin v0.10.0 |
| JavaScript, TypeScript | [`scripts/semconv/templates/registry/ts-stable`](https://github.com/open-telemetry/opentelemetry-js/tree/semconv/v1.45.0/scripts/semconv/templates/registry/ts-stable) (and `ts-experimental`) in opentelemetry-js semconv/v1.45.0 |
| Python | [`scripts/semconv/templates/registry`](https://github.com/open-telemetry/opentelemetry-python/tree/v1.45.2/scripts/semconv/templates/registry) in opentelemetry-python v1.45.2 |
| Rust | [`opentelemetry-semantic-conventions/scripts/templates/registry/rust`](https://github.com/open-telemetry/opentelemetry-rust/tree/opentelemetry-semantic-conventions-0.33.1/opentelemetry-semantic-conventions/scripts/templates/registry/rust) in opentelemetry-rust's semantic-conventions 0.33.1 |
| C++ | [`buildscripts/semantic-convention/templates/registry`](https://github.com/open-telemetry/opentelemetry-cpp/tree/v1.30.0/buildscripts/semantic-convention/templates/registry) in opentelemetry-cpp v1.30.0 |
| Swift | [`Scripts/semantic-convention/templates/registry`](https://github.com/open-telemetry/opentelemetry-swift-core/tree/2.6.0/Scripts/semantic-convention/templates/registry) in opentelemetry-swift-core 2.6.0 |

They are written for the core registry: for a registry of the project's own, use the filters
above ("What the templates see") rather than theirs.

## Testing templates

Every target in `TEMPLATE_TARGETS` is rendered from `templates_test/fixture/` by
`make test-templates` and compared with `templates_test/golden/<target>/`. After writing or
changing templates, run `make update-golden` and read every golden file: they are the expected
output from then on. A golden file that is empty, or missing a collection the templates cover,
means a filter matched nothing in the fixture. The fixture has:

- the fixture's own attributes in a public group: a string with a note, an enum, a deprecated
  attribute and a long key;
- an import of a core registry group (`registry.user_agent`) nothing else references, so a
  filter that forgets provenance shows up as `user_agent.*` output;
- internal and public groups over the core registry's attributes;
- one definition per collection the project supports.

So each template's filters and branches are exercised. Weaver never lists imported groups under
`.registry.attribute_groups` (their attributes go to `.registry.attributes`), so a provenance
filter on groups has nothing to filter; keep it anyway, it costs nothing. Templates that
deliberately render imported signals (code for the core registry's events a project uses, say)
show the fixture's imported ones in their golden files too: that is expected. They also need the
attribute filter changed ("What the templates see").

Write codegen templates only for the kinds of conventions the project needs (SKILL.md step 1),
and give each collection they cover a fixture file (the base skill's collections), so every
template is tested.

**Golden files are source code.** A codegen target's golden files are files of that language
(`.kt`, `.ts`, `.py`). If the host project's build, type-checker or linter scans the whole repo,
exclude `templates_test/golden/` from it, or keep the golden files clean for it too (and lint
them in `validate-generated`).

## The codegen contract

The Makefile's codegen section provides `generate`; the project implements the two targets only
the platform can, in place of the section's failing stubs:

- **`validate-generated`** (depends on `generate`) must fail when the generated code is invalid
  for the platform. At minimum compile or type-check it; better, also run a small test that
  asserts a known constant's value: a changed string usually still compiles (unless the host's
  types use the literal keys), so the test is what reliably catches a wrong key (in TypeScript, a
  `satisfies '<key>'` assertion does it at type-check time, with no test runner). Prove once that
  it fails on bad output: make the template emit code that can't compile (e.g. append `-broken`
  to every constant's name, which no language accepts in an identifier), run
  `make validate-generated`, see it fail, then revert. With a value test,
  also append `.broken` inside every emitted key string, and see the test fail. Editing a
  generated file doesn't work for this:
  `validate-generated` regenerates first.
  Examples:
  - Kotlin JVM module: `./gradlew :<module>:compileKotlin`;
  - Android module (variant tasks only): `./gradlew :<module>:compileReleaseKotlin
    :<module>:testDebugUnitTest`;
  - TypeScript: `tsc --noEmit`, or the package's own type-check script;
  - Go: `go build ./... && go vet ./...`;
  - Swift: `swift build`;
  - Python: `python3 -m compileall` plus an import.

  It runs in CI, so it must work from a clean checkout with the toolchain the CI job sets up.
- **`package-generated`** (depends on `validate-generated`) builds what consumers install, into
  `.build/package-generated/`: a jar/aar, an npm tarball (`npm pack`), a wheel, a Swift package
  archive. On platforms consumed from source (Go modules), make it prove the module builds from a
  clean checkout and say so in the Makefile comment. When the code ships inside a package the
  project already builds and publishes, build that package, or print why there is nothing extra
  to build: don't invent an artifact.

Decide with the user whether generated code is committed. If it is, keep the CI job's
`assert-no-drift` step so a stale commit fails; if not, drop that step.

## Platform integration

- **A build tool that already runs weaver** (a Gradle task, an npm script). The generated
  code's status decides who generates it:
  - **Committed code:** `make generate` is the only generator. Remove the build tool's
    generation step, so the two can't disagree; the build only compiles and tests the code.
  - **Code generated at build time** (not committed): the build tool stays the generator, since
    every build needs the code. Point `GENERATED_DIR` under `.build/`, keep the make targets for
    the validations, and have `validate-generated` build through the build tool and fail if its
    output differs from `make generate`'s. The build tool's weaver pin must match
    `versions.env`: note the pairing next to both, and with Renovate, give the build tool's pin
    the same `depName` (`open-telemetry/weaver`), so Renovate's weaver group moves it with the
    others in one pull request. It must also run weaver with `--v2`, as `make generate` does, so
    templates written for v1's resolved shape (`attribute.name`, v1-era jq helpers) are ported
    first, and run it from the project directory, so the project's `.weaver.toml` applies. Declare
    `.weaver.toml` an input of the generating task too (Gradle: an `@InputFile` property), so a
    change to it reruns the task rather than reusing a cached output.
- **Toolchain setup in CI.** Add it to the `validate-generated` job with `actions/setup-*` (no
  other third-party actions). A step that must run somewhere other than the project directory (e.g.
  `npm ci` at a monorepo's root) sets its own `working-directory:`.
- **Package managers that enforce engine versions** (npm's `devEngines`, `engine-strict`) can
  refuse `npm run`, `npx` or `npm exec` on a mismatched local toolchain when the `package.json`
  npm resolves declares them (run from inside a workspace, that is the workspace root's;
  `--prefix <workspace>` resolves the workspace's own): call the tool's binary from
  `node_modules/.bin/` in the Makefile, and pin the same toolchain version in CI. When the
  install itself refuses (`npm ci` on the wrong Node), switch to the pinned version (or ask the
  user to) rather than forcing it, by putting its `bin` directory first on `PATH` for the whole
  command: running only `npm` from the pinned install isn't enough, since a task runner it
  starts (turbo, say) spawns whichever `npm` is first on `PATH`, which refuses again.
- **Tell the developers.** A codegen project has no docs of its own: add a short section to the
  host project's README or contributing guide saying where the semconv project is, what is
  generated from which registry, and that `make generate` (with weaver from
  `make install-weaver`) regenerates it.
