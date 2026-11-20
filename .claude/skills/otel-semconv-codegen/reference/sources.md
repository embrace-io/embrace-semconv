# The source registry

`SOURCE_REGISTRY` is the registry the code is generated from. It is one of:

- **The core registry alone**, pinned to a release:
  `https://github.com/open-telemetry/semantic-conventions@v<version>[model]`. Before setting this
  up, check whether the language SIG publishes a package of them for other projects to depend on
  that does the job: when it covers the conventions the project needs, depending on it needs no
  codegen at all (the otel-semconv-consume skill, whose `reference/languages.md` lists those
  languages). Generate instead when there is no such package for the language, when the package
  lags the core registry release the project needs, or when the project wants its own shape of
  code.
- **A published federated registry**, pinned to a release:
  `https://github.com/<owner>/<repo>@v<version>[model]`. Its templates see only what it defines,
  imports or references; a consumer that wants some of its keys selects them in the templates'
  filter (`templates.md`, "Choosing what to generate"), not with a registry of its own.
- **A registry of the project's own** (`$(MODEL)`), when the project defines conventions, or
  combines several registries' conventions in one generated package: set the registry up first,
  then point `SOURCE_REGISTRY` at it.

## Finding the release to pin

```bash
gh api repos/<owner>/<repo>/releases \
  --jq '[.[] | select(.draft | not)] | .[0:5] | .[] | "\(.tag_name) prerelease=\(.prerelease)"'
gh api "repos/<owner>/<repo>/contents/<registry-dir>/manifest.yaml?ref=<tag>" \
  -H "Accept: application/vnd.github.raw"
```

Don't rely on `/releases/latest`: it skips prereleases, and a registry that is still unstable
publishes nothing else. Pin the newest release without a pre-release suffix when there is one;
otherwise the newest prerelease, and tell the user the registry makes no compatibility promises
yet. The manifest at the tag gives the registry's own dependencies; the core registry's releases
are the tags of `open-telemetry/semantic-conventions`. Check the release's docs or definition
files for the conventions the project needs before pinning it. Pin a release tag, never a
branch: tags are immutable, and the generated code changes only when the pin does.

## The fixture's core registry

The template test's fixture depends on the core registry (`templates_test/fixture/manifest.yaml`).
Keep it at the core registry release the source registry depends on (the core registry itself, or
the one in a federated registry's manifest at the pinned tag), and move it when `SOURCE_REGISTRY`
moves, so the templates are tested against the same core registry the code comes from. A project
without a registry of its own deletes the fixture manifest's `# renovate:` line: Renovate mustn't
move it apart from `SOURCE_REGISTRY`.

## A private source registry

A registry in a private repository needs git credentials: weaver's git operations are isolated
from the machine's git configuration unless it runs with `--allow-git-credentials`. Set
`WEAVER_FLAGS := --allow-git-credentials` in the Makefile, and keep the CI job's `private`
sections, which give git the workflow's token through gh's credential helper, never in a URL. For
a registry in another private repo, the workflow's own token isn't enough: use a token with read
access to that repo.
