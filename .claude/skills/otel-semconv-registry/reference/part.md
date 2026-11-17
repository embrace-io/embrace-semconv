# The registry part

The part adds a registry defined and validated in the project, on top of the base skill's `core`
(its "Adding a part"). Its files come from four places:

- `assets/registry/`, copied to the same paths in the project: `model/manifest.yaml` and the
  invalid registries under `validations_test/`.
- `assets/policies/`, the same, with `policies`: the `setup-opa` action (`.github/` at the repo
  root) that installs OPA for the policies' unit tests.
- `assets/public-groups/`, the same, with `public-groups`: the public-attribute-groups policy,
  its OPA unit tests, and the case that proves it runs.
- `assets/templates-case/`, the same, when the project also has the base's `templates` part: the
  case that proves the template fixture's imports are checked.

And three fragments, added the way the base's "Adding a part" says:

- `assets/project/Makefile`: the `registry` section, after `templates` (when the project has it)
  and before `docs`, `release` and `codegen`. It nests a `policies` section, which nests a
  `public-groups` section: delete each unless it was chosen (SKILL.md step 1).
- `assets/project/versions.env`: the shared policy pack pin, and with `policies` the OPA pin.
- `assets/project/ci-validation.yaml`: the `validate-registry`, `test-validations` and, with
  `policies`, `test-policies` jobs, and their entries in the aggregate job's `needs`. They
  install weaver the way the base's jobs do: with the base's fallback, use it here too. Keep the
  `private` sections for a private repo, or one whose weaver runs fetch a private registry.

Copy the Makefile fragment and the rego files rather than retyping them: they are indented with
tabs. Never copy `assets/registry/` over an existing registry: `model/manifest.yaml` is merged
(its `schema_url` stays the repo's), and `validations_test/` can be copied whole, after which
delete any case the assets no longer have, keeping the repo's own.

## Collections

The registry defines at least one kind of convention: `attributes`, `attribute-groups`, `events`,
`metrics`, `spans`, `entities`. None has files of its own here. With `public-groups`, also take
`attribute-groups`: its policy requires every attribute the registry defines to be exported by
one of its public attribute groups. A registry of only events, say, that references the core
registry's attributes needs neither. With the base's `templates` part, the template fixture
covers the same collections.

The public-attribute-groups policy's helpers are in a rego package named after the registry
(`@@POLICY_PACKAGE@@`), so they can't collide with the shared policy pack's; see
`validations.md`.

## Settings

At the top of the `registry` section:

| Setting | Default | Meaning |
|---|---|---|
| `MODEL` | `model` | the registry directory (its `manifest.yaml` sits directly inside) |
| `MODEL_REPO_PATH` | `$(MODEL)` | that directory's path within the repo, for the baseline |
| `REGISTRIES` | `$(MODEL) $(FIXTURE)` | registries whose dependency trees are verified; `FIXTURE` is empty without the base's `templates` part |
| `REPO_URL` | from `origin` | the repo's GitHub URL (read raw, credentials stripped), for the baseline's tags and the release URLs; set it to the canonical repo when `origin` isn't (a fork, or a contributor's fork as `origin`) |
| `LOCAL_POLICIES` | empty; `public-groups` adds the public-attribute-groups policy | local policy directories |
| `BASELINE` | token | `auto` (the highest `vX.Y.Z` tag of `REPO_URL`), a registry path, or empty (`validations.md`) |
| `KNOWN_VIOLATIONS` | empty | a JSON file of accepted shared-pack violations, by convention `known-violations.json` next to the Makefile (`validations.md`) |

With the part, `all:` usually runs `validate-registry` (with the other parts' targets, e.g.
`validate-registry generate-all`).

## Tokens

| Token | Where | Value |
|---|---|---|
| `SCHEMA_URL` | `model/manifest.yaml` | the registry URL plus its first version: `0.1.0-dev`, or `1.0.0` for a registry stable from the start (e.g. `https://example.com/schemas/my-registry/0.1.0-dev`) |
| `REGISTRY_STABILITY` | `model/manifest.yaml` | `development` unless the user asks for `stable` (`versioning.md`) |
| `REGISTRY_DESCRIPTION` | `model/manifest.yaml` | one line |
| `POLICY_PACKAGE` | the public-attribute-groups policy (`public-groups`) | the registry name in reverse-DNS order, dotted, with anything that isn't a letter, digit or `_` turned into `_` (e.g. `example.com/schemas/my-registry` → `com.example.schemas.my_registry`) |
| `CORE_VERSION` | manifest, `validations_test/` | the core registry release depended on, no `v` (e.g. `1.44.0`); the base's fixture uses the same |
| `CORE_OLDER_VERSION` | `validations_test/` | any earlier core registry release (e.g. `1.43.0`) |
| `BASELINE` | Makefile `registry` | `auto` for a registry published from this repo as `vX.Y.Z` tags; otherwise (a `-dev` family included) empty, or a pinned registry path (SKILL.md step 1) |

## What is required and what is convention

| Choice | Required by weaver? | Notes |
|---|---|---|
| definition files anywhere under the registry directory, `.yaml` or `.yml` | yes (any depth) | file and directory names are organizational only; weaver merges them all |
| the registry directory named `model/` | no | the core registry and every federated registry use it; consumers then write `…@<tag>[model]`. An existing project can keep its path with `MODEL` |
| `/schemas/` in `schema_url` | no | weaver needs only the last segment to be the version; OTEP 4815's pattern is `https://<domain>/schemas/<name>/<version>` |
| `visibility: public` on the groups that export attributes | **yes**, for templates and consumers that import by group | internal groups are dropped at resolution |
| group IDs `registry.<namespace>` (or `registry.<namespace>.<area>`) | no, only unique | the core registry and federated registries use it; IDs are public API |
| `v` prefix on release tags | no | the release tooling assumes it; `registry_path` pins `@v<version>` |

## Projects in a subdirectory

Besides what the base says: `model/` and `validations_test/` go in the subdirectory with the
Makefile; set `MODEL_REPO_PATH := <subdirectory>/model` so the baseline registry path is right;
and the repo's `v*` tags are usually the host project's, so set `BASELINE` accordingly (SKILL.md
step 1), and ask the user before the registry releases.
