# The release part

The part publishes a registry as GitHub releases tagged `v<version>`, with the OTEP 4815
publication artifacts attached: the publication manifest (`manifest.yaml`,
`file_format: manifest/2.0`) and the resolved registry (`resolved.yaml`,
`file_format: resolved/2.0`), both from `make package`. The manifest's `resolved_registry_uri`
points at the release's `resolved.yaml`. It needs the registry skill's part (and so the base's
`core`).

## Files

- `assets/release/.github/workflows/release.yml`: the Release workflow, at the repo root. It
  installs weaver the way the base's jobs do, with `cache: false` since it publishes: with the
  base's fallback, use it here too. Keep its `private` sections for a private repo.
- `assets/skeletons/RELEASING.md`: the release process, for the project root; fill it in the way
  the base skill's `reference/layout.md` ("Skeletons") says.
- `assets/project/Makefile`: the `release` section (`print-version`, `package`), after `registry`
  (and `docs`) and before `codegen`, added the way the base's "Adding a part" says.

## The release process

`RELEASING.md` is the process the project follows; in short:

1. Bump the version in `schema_url` and merge.
2. A maintainer prepares a **draft** release in the web UI: type `v<version>` in the tag selector,
   click `Create a new tag` and confirm it is created on publish (it doesn't exist yet; the
   workflow creates it), then `Generate release notes` and curate them to what changed under
   `model/`. A draft saved without clicking `Create a new tag` has no tag, and the workflow can't
   find it; its error lists drafts by title to make that visible.
3. Run the `Release` workflow from the default branch. It refuses any other branch, derives the tag
   from the manifest, refuses if the tag exists, no matching draft is waiting, or the version
   lacks `VERSION_SUFFIX`, validates the registry (including backwards compatibility with the
   baseline), packages, uploads the artifacts to the draft and publishes it at the workflow's
   commit.

The draft is the human gate: the workflow never creates a release on its own. Its lookups treat
only GitHub's "not found" as an answer, so a lookup that fails for another reason stops the
release instead of being read as "no tag" or "no draft". A version with a pre-release suffix is
published as a GitHub prerelease.

Release only when the publication artifacts would change: a convention added, removed or changed,
or a dependency bumped. Reorganizing `model/` (moving conventions between files, renaming files,
moving them into subdirectories) leaves `resolved.yaml` byte-identical, since it records no
source paths, and needs no release; nor do tooling, template, docs and CI changes.

One registry is released per repo: the workflow tags `v<version>`, and the registry skill's
`BASELINE=auto` reads every `v*` tag as this registry's. In a repo whose `v*` tags are something
else's (an SDK's), ask the user how to tell the registry's releases apart before adding this part:
nothing here provides a tag prefix scheme.

## Settings

| Setting | Section | Default | Meaning |
|---|---|---|---|
| `VERSION_SUFFIX` | release | empty | a suffix every version must end with, e.g. `-dev` for a `-dev` family (the registry skill's `versioning.md`) |

`package` takes the release URLs from the registry part's `REPO_URL`: set it to the canonical repo
when `origin` isn't, or the published manifest names a fork.

## Tokens

| Token | Where | Value |
|---|---|---|
| `PROJECT_DIR` | release workflow | the base's token: the project directory relative to the repo root |
| `REPO_URL` | RELEASING | `https://github.com/<owner>/<repo>`, the canonical repo; ask when the repo has no remote yet |
| `CI_WORKFLOW_NAME` | RELEASING | the base's token: the CI workflow's name |
