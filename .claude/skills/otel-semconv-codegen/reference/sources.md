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
- **A registry of the project's own**, when the project defines conventions, or combines several
  registries' conventions in one generated package: `SOURCE_REGISTRY` is the path of its registry
  directory (e.g. `model`). This skill generates from a registry the project already has; it
  doesn't set one up or validate it.

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

To see which keys a published federated registry's release defines (to choose the keys to
generate), download the resolved registry its release publishes, whose `attribute_catalog` lists
every attribute by key:

```bash
gh release download v<version> --repo <owner>/<repo> --pattern resolved.yaml --dir <scratch dir>
rg -n -e '^- key:' <scratch dir>/resolved.yaml
```

For a release with no `resolved.yaml` among its assets (`gh release download` then fails with "no
assets to download"), and for every core registry release, resolve the registry with weaver, from
the project directory so its `.weaver.toml` applies (adding `--allow-git-credentials` for a
private one, "A private source registry"), and list the keys. Weaver 0.28.0 calls
`registry resolve` deprecated but still runs it:

```bash
weaver registry resolve -r "<SOURCE_REGISTRY>" --v2 -f json -o <scratch dir>/resolved.json
jq -r '.registry.attributes[].key' <scratch dir>/resolved.json
```

## The fixture's core registry

The template test's fixture depends on the core registry (`templates_test/fixture/manifest.yaml`,
`CORE_VERSION`). Keep it at the core registry release the source registry depends on, so the
templates are tested against the same core registry the code comes from, and move it when that
release moves:

- the core registry itself: its release, the one `SOURCE_REGISTRY` pins;
- a published federated registry: the core registry in its manifest at the pinned tag;
- a registry of the project's own: the core registry in its manifest.

The fixture manifest's `# renovate:` line lets Renovate bump the fixture's core registry, and the
`core registry` rule (`renovate.md`) groups every pin named `open-telemetry/semantic-conventions`
into one pull request. So the line stays only where that group also moves the release the
fixture follows: `SOURCE_REGISTRY` is the core registry and carries its annotation (that
`depName`), or the project's own manifest annotates its core registry dependency the same way
(add the annotation, with the user's agreement). Otherwise delete the line, Renovate mustn't move
the fixture alone, and move the fixture by hand when the release it follows moves: with
`SOURCE_REGISTRY`, for a federated source registry; with the dependency the own registry's
manifest moves, for an own registry with no direct core registry dependency.

A repo that bumps the core registry another way (a scheduled workflow, or by hand) leaves the
core registry's rule out of its Renovate config (`renovate.md`). It bumps a `SOURCE_REGISTRY`
that is the core registry that same way too: that `SOURCE_REGISTRY` gets no `# renovate:` line,
the fixture's line is deleted, and the fixture moves with it. Without the `renovate` part the
fixture's line does nothing, and stays.

## A private source registry

A registry in a private repository, the source registry or one it depends on, needs git
credentials: weaver's git operations are isolated from the machine's git configuration unless it
runs with `--allow-git-credentials`. Keep the `private` sections (`layout.md`, "Sectioned files"):
the Makefile's sets `--allow-git-credentials` in `WEAVER_FLAGS`, and the CI job's give git the
workflow's token through gh's credential helper, never in a URL. For a registry in another
private repo, the workflow's own token isn't enough: use a token with read access to that repo.
