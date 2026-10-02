# Versioning and releases

## Identity and version

A registry's identity and version both come from the `schema_url` in `model/manifest.yaml`.
Weaver splits it at the last `/`: everything before (minus the scheme) is the registry's name,
the last segment its version, a SemVer version without a `v`. There is no `name:` field (weaver
ignores one). Only the version segment ever changes: changing anything before it makes a
different registry, and consumers pinning the old name never see the new one.

`make print-version` prints the version and fails unless it is SemVer, so a `schema_url` the
tooling can't parse never reaches a package or a tag.

## New registries start unstable by default

Unless the user explicitly asks for a stable registry, a new one starts with:

- version **`0.1.0-dev`**, a pre-release. Pre-release versions are published as GitHub
  prereleases, skipped by `/releases/latest`, and never used as the backwards-compatibility
  baseline, so nothing the registry publishes is promised to stay;
- **`stability: development`** in `model/manifest.yaml`;
- **`stability: development`** on every convention it defines.

While unstable, release `0.2.0-dev`, `0.3.0-dev` and so on. Removals and renames are allowed; say
so in the release notes, since consumers get no other warning.

To graduate, once the user is ready to promise compatibility for some or all conventions:

1. Mark those conventions `stability: stable`. The shared pack's stability policy rejects a stable
   signal that references a less stable attribute (unless the reference is `opt_in`), so stabilize
   attributes before or with the signals using them.
2. Set the manifest's `stability: stable`.
3. Release a version without a pre-release suffix (`1.0.0`, or a `0.x.0` if they want the
   validation without SemVer's 1.0 promise). From then on, `make validate-registry` compares every
   change with the latest such release.
4. Don't return to `-dev` versions under the same name afterwards: weaver resolves the highest
   version, and `1.1.0-dev` sorts below `1.1.0`. To keep publishing unstable conventions alongside
   stable ones, use a separate `-dev` family (below).

A registry the user wants stable from the start skips the graduation: `stability: stable` in the
manifest, stable conventions (following step 1's rule on references), and version `1.0.0` (a
`0.1.0` start is also valid, if the user wants the validation without SemVer's 1.0 promise). Its
first release becomes the baseline, so every later change is compatibility-checked; make sure
the user knows removals then need a new registry name or a deprecation cycle. A stable registry
that is never published has no release to compare with: set `BASELINE` to a pinned registry path
(`validations.md`) and move it forward as versions ship, or it gets no compatibility validation.

An existing registry keeps its version, whatever it is: an unsuffixed `0.1.0` whose conventions
are all `development` is fine. Don't rename it into a `-dev` version.

## Releases

Registries publish as GitHub releases tagged `v<version>`, with the OTEP 4815 publication
artifacts attached: the publication manifest (`manifest.yaml`, `file_format: manifest/2.0`) and
the resolved registry (`resolved.yaml`, `file_format: resolved/2.0`), both from `make package`.
The manifest's `resolved_registry_uri` points at the release's `resolved.yaml`.

The layout's release process (`RELEASING.md`, `.github/workflows/release.yml`):

1. Bump the version in `schema_url` and merge.
2. A maintainer prepares a **draft** release in the web UI: type `v<version>` in the tag selector,
   click `Create a new tag` and confirm it is created on publish (it doesn't exist yet; the
   workflow creates it), then `Generate release notes` and curate them to what changed under
   `model/`. A draft saved without clicking `Create a new tag` has no tag, and the workflow can't
   find it; its error lists drafts by title to make that visible.
3. Run the `Release` workflow from the default branch. It refuses any other branch, derives the
   tag from the manifest, refuses if the tag exists, no matching draft is waiting, or the version
   lacks `VERSION_SUFFIX`, validates the registry (including backwards compatibility with the
   last release), packages, uploads the artifacts to the draft and publishes it at the
   workflow's commit.

The draft is the human gate: the workflow never creates a release on its own. The whole process
also works from the command line (`RELEASING.md` gives the gh commands).

Release only when the publication artifacts would change: a convention added, removed or
changed, or a dependency bumped. Reorganizing `model/` (moving conventions between files,
renaming files, moving them into subdirectories) leaves `resolved.yaml` byte-identical, since it
records no source paths, and needs no release; nor do tooling, template, docs and CI changes. To
tell, compare `make package`'s `resolved.yaml`, built before the version bump, with the last
release's (`RELEASING.md` has the command).

## Pre-releases and `-dev` families

A version with a SemVer pre-release suffix (`0.4.0-dev`, `1.0.0-rc.1`) is published as a GitHub
**prerelease**: labelled as such, and skipped by `/releases/latest`. Pre-release tags are never
used as the backwards-compatibility baseline.

Some registries publish every convention, whatever its stability, under a separate name from a
stable subset, e.g. `…/schemas/client-side-dev/0.1.0-dev` alongside `…/schemas/client-side/0.1.0`.
These are two registries: each name is its own identity, and the suffix belongs on both halves of
the URL. A `-dev` family released only as pre-releases never gets a baseline, which matches its
promise: its conventions may change or disappear between versions. Set its `BASELINE` empty:
with `auto`, a stable counterpart released from the same repo would become its baseline. Keep
suffixed and unsuffixed versions out of the same name, or the SemVer ordering dependency
resolution relies on breaks: set
`VERSION_SUFFIX := -dev` in a `-dev` family's Makefile, so `print-version` and the release
workflow refuse a version without the suffix.

The layout releases one registry per repo: the release workflow tags `v<version>`, and
`BASELINE=auto` reads every `v*` tag as this registry's. A stable counterpart that doesn't exist
yet, or lives in another repo, changes nothing in a `-dev` family's setup; the README's fill-in
for it names the planned registry. When the user plans to release both from the same repo, tell
them at setup and in the hand over: the second registry needs a repo of its own, or tags of its
own that the layout doesn't provide (a tag scheme the release workflow, `print-version` and the
baseline would all have to follow), so it is a change to make when that registry is created.

## Rules

- Releases and tags are immutable. Fix a bad release with a newer patch version, never a re-tag.
- Removing or renaming an attribute, signal or group ID is a breaking change. Deprecate instead;
  `validate-registry` rejects removals against the last release.
