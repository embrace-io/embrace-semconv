# Contributing

## Proposing a new convention

Submit a PR

## Renames and removals

Semantic conventions are never removed in a new version. Instead, deprecate any
that are no longer maintained and provide documentation regarding what to use instead.

## Tooling

The `Makefile` targets expect the [weaver](https://github.com/open-telemetry/weaver) binary on
`PATH`, at the version pinned in [`versions.env`](versions.env), with network access to fetch pinned
dependency registries. The policy unit tests additionally need
[OPA](https://www.openpolicyagent.org/) at its pinned version. Run `make install-weaver` and
`make install-opa` to install them.

Before pushing, run:

```bash
make check-policies   # validate the model
make generate-all     # regenerate docs/ and commit the result
make test             # template regression test + rego policy unit tests
```

These match the CI jobs in `.github/workflows/check.yaml`.
