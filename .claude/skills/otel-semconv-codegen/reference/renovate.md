# The renovate part

```
.github/renovate.json5               bumps versions.env's pins, the Makefile's SOURCE_REGISTRY
                                     release, the core registry dependency in manifests, and the
                                     pinned actions (weaver's CLI and its setup action in one pull
                                     request)
```

Plus `versions.env`'s `renovate` section, with `RENOVATE_VERSION`. It is optional: set it up when
the user wants the pins bumped automatically, or the repo already runs Renovate.

The `# renovate:` comments it reads are in the other parts' files: `versions.env` (weaver, and
Renovate itself), the fixture manifest (the core registry), and the line `SOURCE_REGISTRY` gets
(below). Without Renovate they do nothing. Each must stay directly above the lines its match
string reads: nothing may come in between, so put any other comment (a pairing note, say) above
the `# renovate:` line. Needs the Renovate GitHub app on the repo. Dependabot can't bump these
pins (env-file values, a Makefile setting). The file's header says how to adapt it:

- Renovate reads one config file: a repo that already has one gets the asset's `customManagers`
  and `packageRules` merged into it, and no second file. Its own `extends`, `schedule` and
  `labels` stay as they are: the asset's would change every Renovate pull request in the repo. A
  plain `.json` config can't hold the asset's `//` comments: carry what they say in the
  `description` of the custom manager or rule they sit in (a match string has none of its own).
- A repo that already bumps the core registry another way (a scheduled workflow, or by hand)
  keeps that, and leaves out the manifest match strings, the `manifest.yaml` file pattern and the
  `core registry` rule, which would describe a bump Renovate never makes there (the manifests'
  `# renovate:` comments can stay: nothing reads them). Its `SOURCE_REGISTRY`, when that is the
  core registry, moves the same way and gets no `# renovate:` line (`sources.md`, "The fixture's
  core registry").
- Otherwise `SOURCE_REGISTRY` pinned to a release gets a `# renovate:` line directly above it:

  ```make
  # renovate: datasource=github-tags depName=<owner>/<repo> versioning=semver-coerced
  SOURCE_REGISTRY := https://github.com/<owner>/<repo>@v<version>[model]
  ```

  A local `SOURCE_REGISTRY` (the project's own registry directory) gets none: there is nothing
  to bump.
- Whether the fixture manifest keeps its `# renovate:` line: `sources.md`, "The fixture's core
  registry".
- Otherwise keep every match string and rule, even those that match nothing in this project: one
  that matches nothing does nothing. Where the repo's config already has a rule for the same
  dependencies (its own GitHub Actions group, say), keep the repo's, and put the asset's `weaver`
  rule after it, so the setup-weaver action joins the `weaver` group. The asset's `github actions`
  rule groups every pinned action in the repo, not only this project's: in a repo with other
  workflows and no such rule of its own, ask the user before adding it.
- Where the repo's config already has a custom manager reading one of the same pins (its own
  match string for `WEAVER_VERSION`, say), replace it with the asset's, which reads the pin's
  `# renovate:` line: two managers reading one pin give it twice.
- A build tool's own weaver pin (a Gradle or npm script that runs weaver) gets the same `depName`,
  `open-telemetry/weaver`, so the `weaver` group bumps it with the rest.

## The Renovate version

Run Renovate at the version `versions.env` pins (`RENOVATE_VERSION`), never `@latest`: a new
release can break a working repo (one was published that npm can't install). Choose the pin at
setup, the first of:

1. The version the repo already gives Renovate (a self-hosted Renovate workflow's version input, a
   `renovate` dev dependency).
2. With the hosted Renovate app, the version it last ran: the `renovate-debug` footer of its most
   recently updated pull request names it. This prints it, and nothing when the app hasn't opened
   a pull request yet:

   ```bash
   gh pr list --repo <owner>/<repo> --state all --limit 1 --search 'author:app/renovate sort:updated-desc' --json body --jq '.[0].body // "" | capture("renovate-debug:(?<f>[A-Za-z0-9+/=]+)").f | @base64d | fromjson | .updatedInVer // .createdInVer'
   ```

3. The newest release that installs: `npm view renovate version`, then
   `npx --yes --package=renovate@<version> -- renovate --version`; if it fails, work back through
   earlier releases until one installs (a release npm can't install may stop with only "A
   complete log of this run can be found in" and no error).

The pin keeps its `# renovate:` line, so Renovate bumps it like the other pins. The commands below
take the pin as `<RENOVATE_VERSION>`.

## Checking the config

Validate the config with
`npx --yes --package=renovate@<RENOVATE_VERSION> -- renovate-config-validator --no-global <config file>`.
Without `--no-global`, a config named by path is validated as Renovate's global config, not a
repo's. A warning that the `re2` module can't be loaded (not found, or built for another Node
version) is harmless: the validator falls back to JavaScript regexes.

Check the repo's own config validator too (a workflow running `renovate-config-validator`); the
part adds none. Make it validate with the version the repo's Renovate runs: a self-hosted one's
version as given, or for the hosted app the footer's, read the same way, falling back to the pin
when there is none. Run it with `--no-global`. Have the workflow run when that `versions.env`
changes, not only the config: the pin is what it falls back to. For the hosted app, the step (a
private repo's job also needs `pull-requests: read`):

```yaml
      - name: Validate the Renovate config
        env:
          GH_TOKEN: ${{ github.token }}
          GH_REPO: ${{ github.repository }}
        run: |
          source <project dir>/versions.env
          version="$(gh pr list --state all --limit 1 --search 'author:app/renovate sort:updated-desc' --json body --jq '.[0].body // "" | capture("renovate-debug:(?<f>[A-Za-z0-9+/=]+)").f | @base64d | fromjson | .updatedInVer // .createdInVer' || true)"
          if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then version="$RENOVATE_VERSION"; fi
          echo "Validating with Renovate $version"
          npx --yes --package="renovate@${version}" -- renovate-config-validator --no-global <config file>
```

An unversioned `renovate` there (`npx --package=renovate`) gets the newest release whose
`engines` allow the job's Node, and on a Node newer than the latest Renovate supports that is an
old one (Renovate 37 on Node 26), which rejects the config with "Custom Manager contains
disallowed fields: managerFilePatterns"; `@latest` takes whatever was published last. npm installs
a pinned version on any Node, with only an engine warning. Use `fileMatch` (the same patterns,
without the slashes) in place of `managerFilePatterns` only where a validator stays pinned to an
old Renovate: the current one reports `fileMatch` as a needed config migration.

A valid config can still miss a pin. Check what Renovate reads by running its extraction with the
repo root as the working directory (it reads the current directory), with the Node the repo
requires. It reads the repo's config and the files git tracks, changes nothing and looks nothing
up, so it needs no token. An untracked file is invisible to it,
so a new setup's files must be staged first (`git add`; no commit needed), or, where the index
must stay as it is, copy the config and the pinned files into a scratch `git init` repo,
`git add` them there and run it in that:

```bash
npx --yes --package=renovate@<RENOVATE_VERSION> -- renovate --platform=local --dry-run=extract \
  --report-type=file --report-path=<scratch dir>/renovate-report.json \
  > <scratch dir>/renovate.log 2>&1
jq -r '.repositories[].packageFiles.regex[]? | .packageFile as $file | .deps[]
  | "\($file) \(.depName) \(.currentValue)"' <scratch dir>/renovate-report.json
```

Every `# renovate:` line in the project's files must show up there, under its file and `depName`,
except the manifests' when the repo bumps the core registry another way (their match strings are
left out, above); any other missing one is a pin no match string fits. Renovate supports one Node
line (the `engines` of its package.json): on a newer Node it logs "Unsupported node environment
detected" and exits non-zero, but still writes the report, so judge by the report.
