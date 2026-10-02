# Validations

Every validation the layout runs, what it catches, and the invalid registry under
`validations_test/` that proves it still does. A validation that stops working usually starts
passing, which looks the same as nothing being wrong; the cases turn that into a failure.

## What runs where

| Make target | Catches | Proven by `validations_test/…` |
|---|---|---|
| `validate-dependencies` | no registry is in the resolved tree at more than one version | `validate-dependencies/dependency-wants-{older,newer}-version` |
| | every declared `schema_url` is what its `registry_path` fetches | `validate-dependencies/schema-url-names-another-{registry,version}` |
| `validate-registry` | schema + reference resolution (weaver) | (weaver's own errors) |
| | the local public-attribute-groups policy runs (with `attributes`) | `validate-registry/local-policy-rejects-unexported-attribute` |
| | the shared policy pack runs | `validate-registry/shared-policies-reject-attribute-without-namespace` |
| | known violations accept only what they list, and none that no longer occurs | `validate-registry/known-violations-accept-only-listed`, `known-violation-no-longer-occurs` |
| | backwards compatibility against the baseline | `validate-registry/attribute-removed-since-baseline` |
| | every import matches something | `validate-registry/import-matches-nothing` |
| `test-templates` | every template target's output from the fixture matches the golden files; fixture imports match | `test-templates/import-matches-nothing` |
| `test-policies` (with `attributes`) | OPA unit tests pass and run every line of rego | (the coverage gate itself) |
| `generate-docs` + CI | committed docs match a regeneration | (the `validate-docs` CI job) |
| `validate-generated` | the generated code is valid for its platform | (platform-specific) |
| `test-validations` (with `registry`) | every case above fails with its expected error | |

`validate-registry` runs `validate-dependencies` first. The cases and `test-validations` come
with `registry`: a codegen project without a registry of its own has neither, and its checks are
`test-templates` and `validate-generated`.

## Why each exists

**Dependency trees.** Weaver resolves one version of each registry for the whole tree, and uses
the highest. It warns only when the version it drops is the one the root requested, and never
fails. So a registry can silently run against a core registry version it was never validated
with. Weaver also keys each dependency by the declared `schema_url` without checking it against
the fetched registry's own manifest: a typo in the path (`cool-schemas` for `schemas`) goes
unnoticed, and so do the version conflicts it hides; a mismatched version gets at most a warning.
`validate-dependencies` reads the `dependencies:` list of the resolved registry that
`weaver registry package` writes, which names every registry in the tree by its own `schema_url`.

**Policies that load but never run.** A rego file whose `package` names no stage weaver runs
loads fine and never evaluates, and `validate-registry` passes. The OPA unit tests catch a typo
in the policy's package line alone (the tests reference `deny` in the right package), but not a
policy and its tests both moved to the wrong package, and not a weaver change to the policy's
input. Each policy set therefore gets an invalid registry only it rejects.

**Backwards compatibility.** The shared pack's `backwards-compatibility` policies run in the
`comparison_after_resolution` stage, which weaver only reaches with `--baseline-registry`.
Removals are rejected (attributes, events, metrics, spans, entities, attribute groups) whatever
their stability, `development` included, and so are incompatible changes to stable conventions.
A registry whose removals are meant to stay allowed has no baseline. The baseline comes from
`BASELINE`:

- **`auto`** uses the highest `vX.Y.Z` tag of `REPO_URL` (read with `git ls-remote`), so each
  change is compared with the last release. Pre-release tags are never baselines, so a `-dev`
  family is never compared (its conventions may change between versions by design). Before the
  first release the comparison is skipped with a message. Use `auto` only when the repo's `v*`
  tags are this registry's releases.
- **A registry path** (`https://github.com/<owner>/<repo>@<tag-or-commit>[<dir>]`) pins the
  baseline explicitly. It's right for an unpublished registry, or one in a repo whose `v*` tags
  belong to something else (an SDK's), and it's how a stable registry that is never published
  still gets compatibility validation. For a registry inside an SDK, pin the latest SDK release
  tag that contains the registry directory, and move the pin forward after each SDK release
  (note that chore next to the setting). The pinned registry must resolve with the pinned weaver
  (SKILL.md step 1 has the fallback when it doesn't).
- **Empty** skips the comparison.

With `auto`, `validate-registry` fails if it can't list `REPO_URL`'s tags, rather than silently
skipping the comparison. The causes and fixes:

- **A private repo.** `git ls-remote` needs credentials, locally and in CI. The layout's
  checkouts use `persist-credentials: false`, so keep the workflows' `private` sections: they run
  `gh auth setup-git`, which makes git ask gh for credentials, and give `GH_TOKEN` only to the
  steps that fetch. Weaver fetches the baseline itself, and needs
  `WEAVER_FLAGS := --allow-git-credentials` to use the same credentials. Never put a token in a
  git URL or an `insteadOf` rule: tools that read the remote's URL then see the token, and
  `make package` would publish it (the Makefile and the release workflow refuse that, as a
  backstop).
- **`origin` isn't the canonical repo** (a fork, or a contributor's fork as `origin`). `REPO_URL`
  comes from `origin`: set it to the canonical repo, or the fork's tags become the baseline and
  the release URLs point at the fork.
- **A repo not yet on GitHub.** Run `make validate-registry BASELINE=` until the first push.

**Unmatched imports.** An import that matches nothing is only a weaver warning, and the registry
silently lacks what it meant to include (so generated code lacks the constants). `RUN_WEAVER`
fails on it, for the registry and for the template fixture.

**Coverage of the rego.** `opa test` passes when it finds no tests at all. The second run
requires 100% coverage of `policies/` and `policies_test/`, which fails for a missing or unloaded
test file as well as an untested rule, and prints the uncovered lines. It compares the number
itself: with `--threshold`, opa writes no report when the threshold is missed.

## Policies

- **The shared pack** (`opentelemetry-weaver-packages`, `policies/check`, pinned by commit in
  `versions.env`) is where rules common to all registries live: naming conventions, stability,
  backwards compatibility. The core registry uses it too. Bump the pin deliberately (with the
  `renovate` feature, Renovate proposes each bump as a pull request) and run
  `make test-validations`: the shared-pack case fails if a bump stops the pack from running.
- **The local public-attribute-groups policy** is part of the layout: every attribute a registry
  defines must be exported by one of its public attribute groups, since consumers import by
  group.
- **Registry-specific policies** go in their own directory under `policies/check/`, listed in
  `LOCAL_POLICIES`, with unit tests in `policies_test/` and an invalid registry under
  `validations_test/validate-registry/`.
- **Don't run dependencies' own policies.** Weaver has no way for a registry to export policies
  (its manifest has no field for them), and pulling them in by hand goes wrong: they were written
  for the dependency's own definitions, so run against yours they impose its editorial rules on
  you; every policy for a stage shares one rego package, so helpers with the same name collide
  and evaluation fails; and nothing keeps the policy pin in step with the dependency's version. A
  rule worth sharing belongs in the shared pack.
- **Keep helper rules in a package of the registry's own**, for the same shared-package reason:
  only `deny` goes in the stage's package. Name it reverse-DNS from the registry name, then the
  policy (the layout's is `@@POLICY_PACKAGE@@.public_attribute_groups`, e.g.
  `com.example.schemas.acme.public_attribute_groups` for `example.com/schemas/acme`), and call the
  helpers fully qualified (`data.<package>.is_local(...)`): weaver's rego engine doesn't resolve
  functions through `import` aliases.

## Known violations

The shared pack's rules are right, and a new registry follows them. An existing registry may
not: keys without a namespace (`status`, `url`), keys with hyphens (`end-time`), an attribute
that is also a namespace (`emb.state` next to `emb.state.value`). Those keys are its public
contract: renaming them to get a pass breaks every consumer. `KNOWN_VIOLATIONS` names a JSON file
of the violations the registry accepts (by convention `known-violations.json`, next to the
Makefile), and `validate-registry` then:

- passes when every failure is a listed violation;
- still fails on any violation not listed, so new keys are held to the rules;
- fails on a listed violation that no longer occurs, so the list only shrinks.

Each entry is the violation's `id` and `context` exactly as weaver reports them, plus a `reason`
for the reader:

```json
[
  {
    "id": "naming_convention_attr_has_namespace",
    "context": {"attribute": "status"},
    "reason": "Legacy key, predates the naming rules; replacement planned."
  }
]
```

To write it, run `make validate-registry` once with no list, and take each violation from
`.build/validate-registry.json` straight after, before another make target runs: every
validate-registry run rewrites that file, including the ones `make test-validations` makes on its
cases.

```bash
jq '[.[] | select(.error.type? == "policy_violation" and .error.violation.level == "violation")
     | .error.violation | {id, context, reason: "TODO"}]' .build/validate-registry.json
```

Review the result: every entry is a decision to accept a violation, so give each a real reason,
and list only violations of the shared pack's naming and stability rules on existing
conventions. A local policy's findings get fixed, not listed.

**The migration that clears them.** The pack exempts deprecated attributes, so for each listed
key: define a replacement that follows the rules, mark the legacy key `deprecated` (with
`renamed_to` the replacement), have producers send both until consumers move, and remove the
entry. Generated code keeps the legacy constant, marked deprecated, so consumers still compile.

**`renamed_to` a dependency's attribute needs an import.** The pack's
`deprecation_attribute_renamed_to_invalid` rule looks for the replacement only among the resolved
registry's attributes. A key deprecated in favor of, say, the core registry's `user_agent.name`
fails that rule unless the registry imports a group that holds the replacement
(`imports: attribute_groups: [registry.user_agent]`; verified with weaver 0.26.1). The import
also puts the group's attributes into what codegen templates see, so they must filter them out
by provenance unless the project wants them (`templates.md`). Without an import, use
`reason: uncategorized` with a `note` naming the replacement.

## Weaver's `--future`

Weaver's `--future` flag "enables the most recent validation rules". In weaver 0.26.1 it turns
every warning into an error, including the "definition/2 is not yet stable" warning it emits for
every `definition/2` file, the core registry's included, so every `definition/2` registry fails
under it. The layout doesn't use it. Revisit when a weaver release makes `definition/2` stable;
until then, fix the warnings it would promote (e.g. a signal without `requirement_level`) as
they appear.

## Adding a validation

1. Put the validation in the make target that owns it (or a new target in the right Makefile
   section), in `assets/project/Makefile` first if it belongs in the layout.
2. Add a case: `validations_test/<make target>/<case>/`, a registry that is invalid in exactly the
   way the validation catches, plus `expected-error.txt` holding text the error must contain.
   Prefer text the validation itself prints over weaver's wording.
3. If the case needs a baseline, put the baseline registry under `validations_test/registries/`
   and name it in the case's `baseline.txt`. Never inside the case directory: weaver would read it
   as part of the case. A case that needs known violations has its own `known-violations.json`.
4. Run `make test-validations`. It passes `MODEL`, `FIXTURE`, `REGISTRIES`, `BASELINE` and
   `KNOWN_VIOLATIONS` to the target, so the case is the registry the target reads.
