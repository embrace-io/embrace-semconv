# Contributing

## Proposing a new convention

Submit a PR that adds the definitions under `model/` and the regenerated `docs/`. New conventions
are `stability: <!-- skeleton: fill in: the default stability for new conventions -->`
unless decided otherwise.
<!-- skeleton: only for stability "stable" -->
<!-- skeleton: only with a signal collection (events, metrics, spans, entities) -->
A stable signal may reference a less stable attribute only at `opt_in`.
<!-- skeleton: end -->
<!-- skeleton: end -->

## Renames and removals

<!-- skeleton: only for stability "-dev family" -->
Conventions may change or be removed between versions: every version is a `-dev` prerelease.
Say so in the release notes, since consumers get no other warning.
<!-- skeleton: end -->
<!-- skeleton: only for stability "unstable" (the default) -->
Until the registry's first release without a pre-release suffix, conventions may change or be
removed between versions. After it, they are never removed in a new version: deprecate any that
are no longer maintained and document what to use instead.
<!-- skeleton: end -->
<!-- skeleton: only for stability "stable" -->
Semantic conventions are never removed in a new version. Instead, deprecate any that are no
longer maintained and document what to use instead.
<!-- skeleton: end -->
<!-- skeleton: only for stability "unstable" (the default) or "stable" -->
<!-- skeleton: only when BASELINE is set -->
`make validate-registry` fails on removals and incompatible changes to stable conventions, compared
with the baseline (`BASELINE` in the `Makefile`), once there is one.
<!-- skeleton: end -->
<!-- skeleton: only when BASELINE is empty -->
Nothing compares changes with an earlier version (`BASELINE` is empty), so reviewers must catch
removals and incompatible changes.
<!-- skeleton: end -->
<!-- skeleton: end -->

## Tooling

The `Makefile` targets expect the [weaver](https://github.com/open-telemetry/weaver) binary on
`PATH`, at the version pinned in [`versions.env`](versions.env), with network access to fetch pinned
dependency registries, and [jq](https://jqlang.org/download/). `make install-weaver` installs
weaver.
<!-- skeleton: only with `public-groups` -->
The policy unit tests also need [OPA](https://www.openpolicyagent.org/) at its pinned version:
`make install-opa`.
<!-- skeleton: end -->
<!-- skeleton: only for a private repo -->
This repository is private, and `make validate-registry` reads it over HTTPS: git needs HTTPS
credentials for it, e.g. from `gh auth setup-git`.
<!-- skeleton: end -->

Before pushing, run:

```bash
make validate-registry   # validate the registry
make generate-all        # regenerate docs/ and commit the result
make test                # the validation tests
<!-- skeleton: only with `public-groups` -->
                         # (and the local policy's unit tests)
<!-- skeleton: end -->
```

These match the CI jobs in `.github/workflows/ci-validation.yaml`.
