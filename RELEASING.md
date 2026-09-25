# Releasing

Releases are cut from `main` as GitHub releases with the OTEP 4815 publication artifacts attached:
the publication manifest (`manifest.yaml`) and the resolved registry (`resolved.yaml`), both
produced by `make package`.

The single source of truth for the release version is the version segment of the `schema_url` in
[`model/manifest.yaml`](model/manifest.yaml), e.g. `…/embrace/0.1.0` releases as tag `v0.1.0`.
Everything else that requires the version derives it by parsing that file.

## When to release

Only when `model/` has changed since the last tag. The model is everything consumers get through
`…@<tag>[model]`; changes to the Makefile, templates, generated docs or CI don't need a release.

## How to release

1. Bump the version segment of `schema_url` in `model/manifest.yaml` and merge that to `main`
   - e.g. `0.2.0` → `0.3.0`.
2. Prepare a [draft release](https://github.com/embrace-io/embrace-semconv/releases/new):
   - Tag: type `v<version>` matching the bumped `schema_url` (e.g. `v0.3.0`) into the tag
     selector, click `Create a new tag`, and confirm in the pop-up that the tag should be created
     on publish. This doesn't create the tag yet, which is what the workflow expects: it is
     created when the workflow publishes the release in step #3. The tag selector now shows the
     new tag and `Previous tag` shows `Auto`.
   - Description: click `Generate release notes` (enabled only once the tag is set) to pre-fill
     the input with a list of PRs merged since the last release. Remove PRs that don't actually
     change the published artifacts, as the notes should cover only what changed in the published
     registry, i.e. under `model/`. Use
     `git log --oneline v<previous-version>..origin/main -- model` to list the commits that
     touched the model if you need help curating this list.
   - Save the release as draft. Do not publish!
   - Optional: check that a release draft exists with the right tag. This should print `v<version>`:

     ```bash
     gh api repos/embrace-io/embrace-semconv/releases --jq '.[] | select(.draft) | .tag_name'
     ```
3. Run the [`Release` workflow](https://github.com/embrace-io/embrace-semconv/actions/workflows/release.yml)
   from the Actions tab (`workflow_dispatch`). It will:
   - Derive the tag from the manifest. The release will fail if the git tag already exists, or if
     no matching draft is waiting. The latter should be created in step #2.
   - Validate the registry (i.e. running `make validate-registry`): its dependencies, schema, and
     the shared and local policies.
   - Package the publication artifacts (i.e. running `make package`).
   - Attach `manifest.yaml` and `resolved.yaml` to the draft and publish it, creating the
     `v<version>` tag at the workflow's commit.

To be clear: the workflow never creates a release of its own end to end. It only edits, adds to,
and publishes the draft a human created in step #2. The involvement of an actual person beyond
clicking a button is intentional.

Releases are published as regular GitHub releases, so the newest one is what
`/releases/latest` points at.

## Rules

- Once published, releases and tags should be considered immutable and should not be rolled back.
  The way to fix a bad release is by releasing a newer patch version. The only way through is
  forward. Document that fact and move on.
- Releases generally should only change the version segment of `schema_url`. Everything before it
  is the registry's identity, and changing that has broad implications which have to be managed
  closely. See [Versioning](README.md#versioning) for details.
