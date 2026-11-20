# Versioning

## Identity and version

A registry's identity and version both come from the `schema_url` in `model/manifest.yaml`.
Weaver splits it at the last `/`: everything before (minus the scheme) is the registry's name,
the last segment its version, a SemVer version without a `v`. There is no `name:` field (weaver
ignores one). Only the version segment ever changes: changing anything before it makes a
different registry, and consumers pinning the old name never see the new one.

Publishing versions as GitHub releases is the otel-semconv-release skill's part; its
`make print-version` refuses a `schema_url` the tooling can't parse.

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
   validation without SemVer's 1.0 promise). From then on, with `BASELINE=auto`,
   `make validate-registry` compares every change with the latest such release.
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
resolution relies on breaks; the release part's `VERSION_SUFFIX := -dev` makes the release
tooling refuse a version without the suffix.

One registry is released per repo: the release workflow tags `v<version>`, and `BASELINE=auto`
reads every `v*` tag as this registry's. A stable counterpart that doesn't exist yet, or lives in
another repo, changes nothing in a `-dev` family's setup. When the user plans to release both
from the same repo, tell them at setup and in the hand over: the second registry needs a repo of
its own, or a tag scheme of its own that nothing here provides, so it is a change to make when
that registry is created.

## Rules

- Releases and tags are immutable. Fix a bad release with a newer patch version, never a re-tag.
- Removing or renaming an attribute, signal or group ID is a breaking change. Deprecate instead;
  `validate-registry` rejects removals against the baseline.
