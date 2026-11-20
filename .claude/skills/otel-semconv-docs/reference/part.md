# The docs part

The part generates markdown docs for the conventions a registry defines, with the shared markdown
templates of [opentelemetry-weaver-packages](https://github.com/open-telemetry/opentelemetry-weaver-packages)
(`templates/docs/markdown`), and commits them. It needs the registry skill's part, and the base's
`core` and `no-drift` parts; it doesn't need the base's `templates` part, since the project writes
no docs templates of its own.

## Files

- `assets/docs/`, copied to the same paths in the project: `.gitattributes` (marks `docs/` as
  generated, so reviews collapse it; put it next to `docs/`) and
  `templates/registry/docs-import-only/` (see "Imported definitions" below).
- `assets/skeletons/`: README.md, AGENTS.md, CLAUDE.md and CONTRIBUTING.md for the project root
  ("The doc skeletons").
- Two fragments, added the way the base's "Adding a part" says: `assets/project/Makefile`, the
  `docs` section, after `registry`; and `assets/project/ci-validation.yaml`, the `validate-docs`
  job, which regenerates the docs and fails when the committed ones differ. It installs weaver
  the way the base's jobs do: with the base's fallback, use it here too. Keep its `private`
  sections for a private repo.

## The shared templates

`DOCS_TEMPLATES` fetches the templates by URL at the commit `versions.env` pins for the shared
policy pack (`POLICY_REPO_REF`), from the same repo: one pin, and so one Renovate bump, moves
both. They generate one directory per root namespace (`docs/<namespace>/README.md`, with its
attributes, and a page per kind of signal it has: `spans.md`, `metrics.md`, `events.md`,
`entities.md`) and a `docs/README.md` listing the namespaces. Their README, at the pinned commit,
lists their params; pass any in `DOCS_PARAMS` (e.g. `--param humanize_headings=true`, or
`--param exclude_deprecated=false` to document deprecated conventions).

- **Links:** pages link each other with absolute URLs under `DOCS_BASE_URL`, so they work wherever
  a page is shown. For docs read on GitHub, that's the docs directory on the default branch
  (`https://github.com/<owner>/<repo>/blob/main/docs`).
- **Template settings in `.weaver.toml`**: two of the templates' settings are read from the
  project's `.weaver.toml` alone, under `[template]`, never from `--param`:
  - namespace titles: `acronyms = ["SDK"]`, and
    `text_maps = { namespace_mapping = { cicd = "CI/CD" } }` for titles that are more than a
    case change;
  - links from a dependency's attributes to its docs, keyed by the dependency's `schema_url`
    exactly as the manifest declares it:

    ```toml
    [template.text_maps.upstream_docs]
    "https://opentelemetry.io/schemas/1.44.0" = "https://github.com/open-telemetry/semantic-conventions/blob/v1.44.0/docs/registry/attributes/{namespace}.md"
    ```

    The key carries the dependency's version: when the dependency is bumped, bump the key with
    it, or those attributes render unlinked again. Without the setting they render unlinked,
    which is accurate, just less useful.
- **Output it decides:** the pages carry a Hugo front-matter comment, stability as shields.io
  badges, and the OpenTelemetry guidance's wording. A repo moving to these templates from its own
  gets different docs; that is expected.

## Imported definitions

The shared templates document every definition in the resolved registry, the ones it only imports
from a dependency (an imported attribute group's attributes, imported signals) included, as if
the registry defined them: each such namespace gets pages of its own. So `generate-docs` first runs
`templates/registry/docs-import-only/`, a template of the project's, which lists the root
namespaces holding only imported definitions, and passes them to the shared templates as
`exclude_root_namespace`. A namespace with any definition of the registry's own is kept.
Attributes a signal of the registry references stay in that signal's table either way.

The skill's tests render the shared templates without the exclusion too, and fail once they stop
documenting imported namespaces: then the template and the exclusion can go.

## Settings

At the top of the `docs` section:

| Setting | Default | Meaning |
|---|---|---|
| `DOCS_DIR` | `docs` | emptied and regenerated each run |
| `DOCS_BASE_URL` | token | where the docs are read, no trailing slash: the base of every link between pages |
| `DOCS_TEMPLATES` | the shared templates at the policy pack's commit | the templates' URL; a repo may pin another commit, at the cost of a second pin |
| `DOCS_PARAMS` | empty | extra flags for the templates, split on spaces |

With the part, `all:` usually runs `validate-registry generate-all`.

## Tokens

| Token | Where | Value |
|---|---|---|
| `DOCS_BASE_URL` | Makefile `docs` | e.g. `https://github.com/<owner>/<repo>/blob/main/docs`; for a project in a subdirectory, its `docs` there |
| `DOCS_REPO_PATH` | CI job | the docs directory relative to the repo root: `docs`, or e.g. `semconv/docs` |
| `PROJECT_DIR` | CI job | the base's token: the project directory relative to the repo root |
| `PROJECT_NAME` | README, AGENTS | human title |
| `REGISTRY_DESCRIPTION` | README, AGENTS | the registry's one-line description, as in its manifest |
| `CI_WORKFLOW_NAME` | README, AGENTS | the base's token: the CI workflow's name |
| `REPO_URL` | README (in its `release` blocks) | `https://github.com/<owner>/<repo>`, the canonical repo; ask when the repo has no remote yet |
| `REGISTRY_URL` | README (in its `release` blocks) | the registry URL: the `schema_url` without its version (the base's glossary) |

## The doc skeletons

README.md, AGENTS.md and CONTRIBUTING.md are skeletons: fill them in the way the base skill's
`reference/layout.md` ("Skeletons") says. CLAUDE.md has no markers and is copied as is.
