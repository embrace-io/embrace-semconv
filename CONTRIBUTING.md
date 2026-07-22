# Contributing

## Proposing a new convention

Submit a PR

## Renames and removals

Semantic conventions are never removed in a new version. Instead, deprecate any
that are no longer maintained and provide documentation regarding what to use instead.

## Tooling

Scripts expect the [weaver](https://github.com/open-telemetry/weaver) binary on `PATH`, at the version pinned
in [`versions.env`](versions.env), with network access to fetch pinned dependency registries.
Run `.github/actions/setup-weaver/install-weaver.sh` to install the pinned version.
