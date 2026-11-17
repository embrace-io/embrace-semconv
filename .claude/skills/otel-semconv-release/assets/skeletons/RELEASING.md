# Releasing

Releases are made from the default branch as GitHub releases with the OTEP 4815 publication
artifacts attached: the publication manifest (`manifest.yaml`) and the resolved registry
(`resolved.yaml`), both produced by `make package`.

The single source of truth for the release version is the version segment of the `schema_url` in
the registry's [`manifest.yaml`](model/manifest.yaml): `…/<registry>/<version>` releases as tag
`v<version>`. Everything else that requires the version derives it with `make print-version`.

## When to release

Only when the registry has changed in a way that changes the publication artifacts: a convention
added, removed or changed, or a dependency bumped. Reorganizing the registry's files without
changing any convention (moving conventions from one file to another, renaming files, moving them
into a subdirectory) produces identical artifacts and doesn't need a release, and neither do
changes to the Makefile, templates, generated docs or CI.

To tell, run `make package` on the default branch before bumping the version, and compare its
resolved registry with the last release's. No output means there is nothing to release:

```bash
gh release download v<previous-version> -p resolved.yaml -O - | diff - .build/package/resolved.yaml
```

The first release has nothing to compare with: release once the registry holds what it should.

## How to release

1. Bump the version segment of `schema_url` in the manifest and merge that to the default branch,
   e.g. `0.1.0-dev` → `0.2.0-dev`. For the first release, skip this step: the manifest already
   holds the first version.
<!-- skeleton: only for stability "unstable" (the default) or "stable" -->
   A version without a suffix bumps the same way, e.g. `1.0.0` → `1.1.0`.
<!-- skeleton: end -->
2. Prepare a [draft release](@@REPO_URL@@/releases/new):
   - Tag: type `v<version>` matching the manifest's version (the version from step 1) into the tag
     selector, click `Create a new tag`, and confirm in the pop-up that the tag should be created
     on publish. This doesn't create the tag yet, which is what the workflow expects: it is
     created when the workflow publishes the release in step 4. The tag selector now shows the
     new tag and `Previous tag` shows `Auto`. Leave the target branch and the pre-release box as
     they are: the workflow sets both.
   - Title: `v<version>`.
   - Description: click `Generate release notes` (enabled only once the tag is set) to pre-fill
     it with the pull requests merged since the last release. Remove those that don't change the
     published artifacts, as the notes should cover only what changed in the published registry.
     `git log --oneline v<previous-version>..origin/<default-branch> -- <registry directory>`
     lists the commits that touched the registry. On the first release, or when changes went in
     without pull requests, the generated notes are only a changelog link: write the notes
     yourself.
   - Save the release as draft. Do not publish!
   - Optional: confirm that a release draft exists with the right tag. From a checkout of this
     repo, this should print `v<version>`:

     ```bash
     gh release list --json tagName,isDraft --jq '.[] | select(.isDraft) | .tagName'
     ```
3. Check that the `@@CI_WORKFLOW_NAME@@` workflow passed on the commit you're releasing (the
   default branch's head): the Release workflow re-runs only `make validate-registry`, not the
   tests or the docs comparison. `gh run list --workflow "@@CI_WORKFLOW_NAME@@" --commit <sha>`
   shows it, given the full 40-character sha (`git rev-parse origin/<default-branch>`): a short
   one matches nothing, silently.
4. Run the [`Release` workflow](@@REPO_URL@@/actions/workflows/release.yml) from the Actions tab
   (`workflow_dispatch`), with the default branch under `Use workflow from`. It will:
   - Refuse to run on any other branch.
   - Derive the tag from the manifest. The release will fail if the git tag already exists, if no
     matching draft is waiting (step 2), or if the version doesn't end with the Makefile's
     `VERSION_SUFFIX`, when it sets one.
   - Validate the registry (i.e. running `make validate-registry`): its dependencies, schema and
     policies, and, when there is a baseline, backwards compatibility with it (with
     `BASELINE=auto`, only once a release without a pre-release suffix exists).
   - Package the publication artifacts (i.e. running `make package`), and refuse to publish a
     manifest whose `resolved_registry_uri` isn't exactly this release's `resolved.yaml`.
   - Attach `manifest.yaml` and `resolved.yaml` to the draft and publish it, creating the
     `v<version>` tag at the workflow's commit.

The same from the command line, for steps 2 and 4 (from a checkout of this repo, or with
`-R <owner>/<repo>` on each `gh` command):

```bash
gh release create v<version> --draft --title v<version> --notes-file <notes.md>
gh workflow run release.yml --ref <default-branch>   # recent gh prints the run's URL (its ID last)
gh run list --workflow release.yml --limit 1         # otherwise: the ID, once the run shows up
gh run watch <run-id> --exit-status
```

`--generate-notes` in place of `--notes-file` pre-fills the notes as `Generate release notes`
does; curate them in the draft before step 4.

A draft made this way has no tag yet either, so gh prints its URL as `…/releases/tag/untagged-…`:
that is expected.

To be clear: the workflow never creates a release of its own end to end. It only edits, adds to,
and publishes the draft a human created in step 2. The involvement of an actual person beyond
clicking a button is intentional.

<!-- skeleton: only for a private repo -->
This repository is private, so its releases' assets, `resolved.yaml` included, can only be
downloaded with access to it: consumers need that access, and weaver needs
`--allow-git-credentials` to fetch the registry with their git credentials.
<!-- skeleton: end -->

A version with a SemVer pre-release suffix (e.g. `0.1.0-dev`) is published as a GitHub
prerelease, which `/releases/latest` skips, and it is never used as the baseline
`make validate-registry` compares against: the registry promises no compatibility while its
versions carry the suffix.
<!-- skeleton: only for stability "unstable" (the default) or "stable" -->
Any other version is published as a regular GitHub release, the newest of which is what
`/releases/latest` points at, and, with `BASELINE=auto`, becomes the baseline for later changes.
<!-- skeleton: end -->

<!-- skeleton: only for stability "unstable" (the default) -->
This registry starts at `0.1.0-dev` with `stability: development`. It graduates by marking the
conventions it promises `stability: stable`, setting the manifest's `stability: stable`, and
releasing its first version without a suffix; after that it doesn't return to `-dev` versions.
<!-- skeleton: end -->
<!-- skeleton: only for stability "-dev family" (VERSION_SUFFIX := -dev) -->
This registry is a `-dev` family: every version carries the `-dev` suffix and is a prerelease,
and `make print-version` refuses a version without it. Its stable conventions belong to a
separate registry, published apart from this one.
<!-- skeleton: end -->

## Rules

- Once published, releases and tags should be considered immutable and should not be rolled back.
  The way to fix a bad release is by releasing a newer patch version. The only way through is
  forward. Document that fact and move on.
- Releases generally should only change the version segment of `schema_url`. Everything before it
  is the registry's identity, and changing that has broad implications which have to be managed
  closely. See [Versioning](README.md#versioning) for details.
