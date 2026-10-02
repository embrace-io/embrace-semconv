# Dependencies: consuming the core registry and federated registries

## Declaring one

A registry declares each dependency in `model/manifest.yaml` with two fields that must name the
same release:

```yaml
dependencies:
  - schema_url: https://opentelemetry.io/schemas/1.44.0
    registry_path: https://github.com/open-telemetry/semantic-conventions@v1.44.0[model]
  - schema_url: https://<domain>/schemas/<registry>/<version>
    registry_path: https://github.com/<owner>/<repo>@v<version>[model]
```

- `schema_url` is the dependency's identity: everything between the scheme and the last `/` is
  its name, the last segment its version. It must be exactly the `schema_url` in the
  dependency's own manifest at that release.
- `registry_path` is where weaver fetches it: a git URL (no `.git` needed), `@<tag>`, and the
  registry directory in `[...]`. Pin a release tag, never a branch; tags are immutable.
- Weaver fetches `registry_path` but identifies the dependency by `schema_url`, and doesn't fail
  when they disagree. `make validate-dependencies` does.

## Finding the release to pin

```bash
gh api repos/<owner>/<repo>/releases \
  --jq '[.[] | select(.draft | not)] | .[0:5] | .[] | "\(.tag_name) prerelease=\(.prerelease)"'
gh api "repos/<owner>/<repo>/contents/<registry-dir>/manifest.yaml?ref=<tag>" \
  -H "Accept: application/vnd.github.raw"
```

Don't rely on `/releases/latest`: it skips prereleases, and a registry that is still unstable
publishes nothing else (`versioning.md`). Pin the newest release without a pre-release suffix when
there is one; otherwise the newest prerelease, and tell the user that the dependency makes no
compatibility promises yet. The manifest at the tag gives the exact `schema_url` to declare and
the dependency's own dependencies. The core registry's releases are the tags of
`open-telemetry/semantic-conventions`; its `schema_url` is
`https://opentelemetry.io/schemas/<version>`. Check the release's docs or definition files for
the conventions the project needs before pinning it.

## Keeping versions aligned

Weaver resolves **one** version of each registry for the whole tree, the highest requested.
When two registries in the tree depend on the core registry at different versions, one of them
runs against a core registry it wasn't validated with; `make validate-dependencies` fails on it.
So:

- depend on the core registry at the **same** version every other dependency depends on (read
  their manifests at the pinned tags);
- when bumping a dependency, check its core registry version and move the core registry with it;
- when bumping the core registry past a dependency's core registry, wait for (or ask for) a
  release of that dependency.

When the core registry moves, the templates fixture's core registry pin moves with it, so the
templates are tested against the same core registry the registry uses. The invalid registries'
pins don't need to follow. The `renovate` feature bumps the manifest and the fixture together.

## Private registries

A dependency (or a baseline) in a private repository needs git credentials: weaver's git
operations are isolated from the machine's git configuration unless it runs with
`--allow-git-credentials`. Set `WEAVER_FLAGS := --allow-git-credentials` in the Makefile, and
give CI's jobs credentials the way the workflows' `private` sections do (a credential helper,
never a token in a URL; `validations.md`). For a dependency in another private repo, the
workflow's own token isn't enough: use a token with read access to that repo.
Consumers of a private registry need the same: access to the repo, and the flag. The published
`resolved.yaml` of a private repo's release isn't downloadable without credentials either.

## What a registry can reach

A registry sees only what its **direct** dependencies define. To `ref` a core registry attribute,
the core registry must be a direct dependency, even if another dependency already depends on the
core registry. Imports are not transitive either: a dependency's imports are not re-exported.

## Using what a dependency defines

In any `definition/2` file under `model/`:

```yaml
file_format: definition/2

# Reference attributes by key from the project's own public groups...
attribute_groups:
  - id: registry.<your-namespace>.<area>
    visibility: public
    stability: development
    brief: <one line>
    attributes:
      - ref: session.id              # from the core registry
      - ref: <dependency-attribute>  # from a federated dependency

# ...or import a dependency's public groups, or signals, whole.
imports:
  attribute_groups:
    - "<dependency-group-id>"
  events:
    - "<namespace>.*"
```

- A `ref` that resolves to nothing is a hard weaver error. An import that matches nothing is only
  a warning in weaver; the layout's make targets fail on it.
- Templates see the two differently: an imported group's attributes are in
  `.registry.attributes`; a referenced attribute only inside the group or signal that references
  it (`templates.md`, "What the templates see").
- `ref` needs no group on the dependency's side. Imports select by group ID or signal name, so a
  federated registry's public attribute groups are its import surface.
- The core registry's v1-syntax groups (`registry.session`, …) can be imported by ID, but templates
  rendering the core registry directly don't see most of them as attribute groups: see
  `templates.md`.

## The core registry only

A project that needs only the core registry generates straight from it (`SOURCE_REGISTRY` set to
the core registry's `registry_path`), and selects the keys it uses in its templates' filter
(`templates.md`, "Choosing what to generate"). A registry of its own is only for conventions it
defines, or for combining several registries (SKILL.md step 2).

## Naming your own registry

Pick the `schema_url` name once: changing any part of it (domain, `/schemas/`, registry name)
makes a different registry, not a new version, and consumers pinning the old one never see the
change. Follow OTEP 4815's pattern, `https://<domain>/schemas/<registry>/<version>`, and use a
domain the project controls. A registry that publishes all conventions whatever their stability
alongside a stable subset uses a separate name for each (e.g. `<name>-dev` and `<name>`); see
`versioning.md`.
