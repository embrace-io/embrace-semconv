# Tests for the otel-semconv-setup skill

These scripts test the skill itself. They aren't part of its instructions, and `new_round.py`
leaves them out of the snapshots agents test. Most regressions in this skill have come from fixes,
not the first draft: a command written without being run, one rule drifting across files, a new
mechanism with no test of its own. The checks here turn those patterns into failures.

## Requirements (maintainers of the skill only)

Repos that use the skill never need these. The scripts use Python 3's standard library, except
`parse_workflows.py`, which needs PyYAML: its dependency is declared inline (PEP 723), so
`uv run` installs it. The weaver-dependent scripts also need what the layout itself needs
(make, weaver, jq, opa, git), plus network access; `renovate_extract.py` also needs npx, on a
Node that Renovate supports.

## Tools, languages and libraries

New functionality, in the skill or in these tests, uses what's already here, in this order of
preference:

1. **A feature of a tool already in use**, over code of our own: weaver for resolving,
   validating and generating; jq for JSON; git and gh; make targets.
2. **make and bash** to orchestrate. These are the layout's own toolchain, and all that a repo
   using the skill needs.
3. **Python 3's standard library** for logic in these tests.
4. **A maintained Python library**, through `uv` with inline (PEP 723) metadata and a pinned
   compatible range, when it replaces code we'd otherwise write: PyYAML replaced a YAML parser.
5. **A maintained external tool**, pinned and installed by a bash script (as the layout's
   `install-weaver.sh` installs weaver), or through `uv` when it's a Python package.

In use now:

- **Languages:** make and bash; Python 3 in these tests. Rego (policies) and Jinja (templates)
  are there because weaver uses them.
- **Libraries:** PyYAML.
- **Tools:** weaver, jq, opa, git, gh and uv; zizmor, run through uv; Renovate, run through npx
  (Node), since the layout's Renovate config is only proven by Renovate itself.

Don't write what a library or tool in this list already does, such as parsing, schema
validation or linting. Don't add a language unless nothing here can do the job: nothing Ruby or
Node could do that Python or make can't already. The layout itself stays within what setting up
a repo needs: no Python there. `check_skill.py` fails on a file in a language not listed here.

## After every edit

```bash
python3 tests/check_skill.py        # static: seconds, no network
```

It fails on:

- a token, asset path, section marker or banned phrase out of place;
- a **command** the docs give that isn't in `verified-commands.json`, as `verified` (with how) or
  `reference` (prose naming a tool, not an invocation);
- a **rule** from `rules.json` that appears in a file not listed for it, or has vanished from one
  that is;
- a **token, Makefile setting or layout section** with no entry in `coverage.json`;
- a file in a **language** "Tools, languages and libraries" doesn't list, or Python outside
  `tests/`.

After changing a check, run `python3 tests/self_test.py --uv uv`. It breaks a copy of the skill
once per check and asserts that each check notices (`--uv` adds the gate case below).

## Before a field-test round

These build scratch projects under `tests/.work/`, or `--work DIR`.

```bash
python3 tests/matrix.py                 # every collection mix, then every make target; a -dev family;
                                        # a model setting only the fields weaver requires
python3 tests/codegen.py                # codegen from the core registry, and from a curated one
python3 tests/curated_filter.py         # runs templates.md's curated filter on the fixture
python3 tests/subset_filter.py          # runs templates.md's key-list and namespace filters on it
python3 tests/actions_dir.py            # ACTIONS_DIR finds the actions from a subdirectory, and without git
python3 tests/renovate_extract.py       # runs layout.md's Renovate extraction; every annotated pin is read
python3 tests/renovate_version.py       # layout.md's Renovate version lookup and validator step (gh)
python3 tests/release_lookups.py        # release.yml's tag and draft lookups: only "not found" is an answer
python3 tests/template_types.py         # weaver's schema still allows only the kinds of value the templates handle
uv run tests/parse_workflows.py         # parses the rendered YAML; checks each gate's needs
python3 tests/lint_workflows.py         # zizmor on the rendered workflows, as client-side runs it
python3 tests/self_test.py --weaver --uv uv   # also breaks the filters, a match string, a lookup, the gate and a `uses:`
```

`lint_workflows.py` holds the rendered workflows to the checks a repo adopting the layout gates
merges on. The client-side registry's ruleset blocks on every zizmor alert and runs zizmor
through `open-telemetry/shared-workflows`: the latest release, online audits, and the `pedantic`
persona on its registry branch. The script runs `pedantic` (a superset of the default `regular`),
online when `gh auth token` gives a token.

## When you change the skill

- **A command in the docs:** run it the way a user would, placeholders filled in. Then add it to
  `verified-commands.json` with `"status": "verified"` and `"how"`: what you ran, the versions
  of the tools it ran on, and what it showed. No dates, machine paths or names: evidence says how
  to reproduce a result, not when or where it was seen. `make <target>` forms of the layout's own targets are exempt, since the matrix runs
  them.
- **A claim about a tool's behavior** ("weaver warns", "npm refuses"): probe it first. Keep the
  probe script in `probes/` when it's reusable. Where a claim is code in the docs, as the curated
  filter is, test it from the doc, as `curated_filter.py` does.
- **A rule stated in more than one file:** prefer one home and a pointer. If a copy is needed (a
  skeleton an end user reads, say), list the file under the rule in `rules.json`. When the rule
  changes, `check_skill.py` shows every copy that no longer matches.
- **Anything new** (a setting, token, section, collection or case): give it a test in the same
  change (a matrix scenario, a `validations_test` case or a codegen project), then record it in
  `coverage.json`. `untested: <reason>` is allowed, and it's counted.
- **Fix the class, not the instance:** before editing, list every place the same case applies:
  every step that fetches, every field that needs it.

## Field tests

Fresh agents run the skill against real repos, one scenario each (`field/targets.json`):

| Test | Scenario |
|---|---|
| T1 | a published registry updates itself to the layout |
| T2a | a new published, private registry with attributes and events |
| T2b | a new stable, unpublished, metrics-only registry with docs |
| T2c | push T2a's output, watch CI, release `v0.1.0-dev` (after T2a) |
| T3 | update a `-dev` family registry whose origin is a fork |
| T4 | TypeScript codegen from a published registry in an npm-workspaces monorepo |
| T5 | v1 to `definition/2` migration with build-time Gradle codegen, byte-identical |
| T6 | a subdirectory registry with committed Kotlin consumes a federated registry |

A round:

1. Run every check above; fix anything red first.
2. Run `python3 tests/field/new_round.py N --setup --workspace <dir> --clones <dir>
   --github-owner <owner>`. `--clones` is the directory holding a clone of each repo
   `targets.json` names, under the repo's name; `--github-owner` owns T2c's test repo. It freezes
   the skill as `skill-rN`, renders the prompts into `<workspace>/rN/prompts/`, and creates the
   worktrees and empty repos.
3. Create the private GitHub repo it prints, for T2c.
4. Launch one agent per prompt for this round's tests (step 7), in parallel, passing the prompt
   text verbatim. Start T2c when T2a reports. The worktrees of tests the round skips stay
   unused.
5. Save each report under `<workspace>/rN/results/`. Triage by the report's tags:
   - [A] caused a failure, a retry, or a wrong or unsafe result;
   - [B] the skill or doc is wrong, or contradicts itself, a tool or the repo;
   - [C] a judgement call;
   - [D] polish.
6. **Verify every [A] and [B] yourself** before acting on it: a probe, a snapshot search, or the
   tool's actual output. Agents' claims are often right and sometimes refuted. An [A] that is the
   agent's own slip, or the environment's, doesn't count.
7. A test **fails** when it has a verified [A] or [B]; a round is **clean** when none of its
   tests fails. Which tests a round runs:
   - The first round runs every test.
   - After a round with failures, fix minimally (small passes), rerun the checks, and run only
     the tests that failed. T2a and T2c run together: T2c pushes T2a's output.
   - Once those are clean, run the tests that round skipped, as one confirming round: the fixes
     may have broken them. The loop is done when that round is clean; its failures start the
     cycle again.

   Set a round limit before starting; if the limit arrives and rounds still aren't clean, stop
   and rethink the approach rather than keep iterating.
8. Tracing an issue's origin: search each `skill-r*` snapshot for the text in question. The first
   snapshot that has it tells you which fix pass wrote it.

`targets.json` names each scenario's public repo and base commit; nothing in it is specific to a
machine or a person, which come from `new_round.py`'s options. Replace them to test against other
repos. The curated codegen fixture imports a public federated registry
(`embrace-io/embrace-semconv`) for the same reason.
