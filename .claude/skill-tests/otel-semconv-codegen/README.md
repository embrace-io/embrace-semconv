# Tests for the otel-semconv-codegen skill

These scripts test the skill at `../../skills/otel-semconv-codegen/`. They live outside it, so
they aren't installed with it, and they aren't part of its instructions. Most regressions in
agent-facing instructions come from fixes, not the first draft: a command written without being
run, one rule drifting across files, a new mechanism with no test of its own. The checks here turn
the first into a failure; the practices below cover the others.

## Requirements (maintainers of the skill only)

Projects set up with the skill never need these. The scripts use Python 3's standard library,
except `workflows.py`, which needs PyYAML: its dependency is declared inline (PEP 723), so
`uv run` installs it. `scenarios.py`, `codegen.py`, `filters.py` and `template_types.py` also
need what a project needs (make, weaver, jq, git), and all but `template_types.py` network access.
The Renovate tests need npx (Node) for Renovate itself, since the config is only proven by
Renovate, and a logged-in gh.

## Tools, languages and libraries

New functionality, in the skill or in these tests, uses what's already here, in this order of
preference:

1. **A feature of a tool already in use**, over code of our own: weaver for resolving,
   validating and generating; jq for JSON; git and gh; make targets.
2. **make and bash** to orchestrate. These are a project's own toolchain, and all that a repo
   using the skill needs.
3. **Python 3's standard library** for logic in these tests.
4. **A maintained Python library**, through `uv` with inline (PEP 723) metadata and a pinned
   compatible range, when it replaces code we'd otherwise write: PyYAML parses the workflows.
5. **A maintained external tool**, pinned and installed by a bash script (as the project's
   `install-weaver.sh` installs weaver), or through `uv` when it's a Python package.

In use now:

- **Languages:** make and bash in the skill; Python 3 in these tests. Jinja (templates) is there
  because weaver uses it.
- **Libraries:** PyYAML.
- **Tools:** weaver, jq, git, gh and uv; zizmor, run through uv; Renovate, run through npx.

`check_skill.py` fails on a file in the skill that isn't one of these, and on any Python in it.

## After every edit

```bash
python3 check_skill.py              # static: seconds, no network
```

It fails on a token, asset path, section marker or banned phrase out of place; a command the docs
give that isn't in `verified-commands.json`; a date, test round or machine path in the skill or
these tests; an asset that points at a skill; a file of a kind the skill may not hold.

After changing a check, run `python3 self_test.py --weaver --uv uv --npx`. It breaks a copy of the
skill once per check and asserts that each check notices.

## Before calling a change done

These build scratch projects under `.work/`, or `--work DIR`.

```bash
python3 scenarios.py                # every target listed; each collection and all of them through
                                    # the template test; golden drift; a failing weaver run; a
                                    # dead import; the GENERATED_DIR guard; private registries;
                                    # a subdirectory project; the install script
python3 codegen.py                  # a Python project from the core registry through every target;
                                    # the stubs fail until implemented; broken output fails validation
python3 filters.py                  # runs templates.md's filters on the fixture: what each selects
python3 examples.py                 # renders templates.md's Jinja examples on the fixture: final
                                    # newline, deprecation marked, names from the whole ID
python3 template_types.py           # weaver's schema still allows only the kinds of value templates.md
                                    # covers; its enum mapping example on every member value type
uv run workflows.py                 # the CI workflow, public and private, as shipped and with
                                    # layout.md's fallback: gate, one weaver install per job, zizmor
                                    # (pedantic, latest)
python3 renovate_version.py         # renovate.md's version lookup and validator step (gh)
python3 renovate_extract.py         # renovate.md's extraction: Renovate reads every annotated pin
```

Validate the Renovate config itself with the command in `renovate.md`, "Checking the config", at
the version `assets/core/versions.env` pins.

## When you change the skill

- **A command in the docs:** run it the way a user would, placeholders filled in. Then add it to
  `verified-commands.json` with `"status": "verified"` and `"how"`: what you ran, the versions of
  the tools it ran on, and what it showed. No dates, machine paths or names. `make <target>` forms
  of the project's own targets are exempt, since the scenarios run them.
- **A claim about a tool's behavior:** probe it first. Where a claim is code in the docs, as the
  fallback step, the filters, the examples and the enum mapping are, test it from the doc, as
  `workflows.py`, `filters.py`, `examples.py` and `template_types.py` do.
- **One home per rule:** a rule lives in one file and the others point to it. Before changing a
  rule, search every file of the skill for its copies and paraphrases, and change them together.
- **Anything new gets a test in the same change:** a new setting, token, section or part gets a
  scenario that exercises it. A mechanism with no test of its own is untested, however simple.
- **A new pin** gets its `# renovate:` line, a match string in the Renovate config if no existing
  one fits, and shows up in `renovate_extract.py`'s report.
