# Tests for the otel-semconv-base skill

These scripts test the skill at `../../skills/otel-semconv-base/`. They live outside it, so they
aren't installed with it, and they aren't part of its instructions. Most regressions in
agent-facing instructions come from fixes, not the first draft: a command written without being
run, one rule drifting across files, a new mechanism with no test of its own. The checks here turn
the first into a failure; the practices below cover the others.

Skills that build on the base reuse these scripts: `render.py` and `add_part.py` build their test
projects, `check_skill.py` runs on their tests directory, and `workflows.py`'s checks run on their
workflows.

## Requirements (maintainers of the skill only)

Projects set up with the skill never need these. The scripts use Python 3's standard library,
except `workflows.py`, which needs PyYAML: its dependency is declared inline (PEP 723), so
`uv run` installs it. `scenarios.py` also needs what a project needs (make, weaver, jq, git), plus
network access.

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

- **Languages:** make and bash in the skills; Python 3 in these tests. Jinja (templates) and Rego
  (policies) are there because weaver uses them.
- **Libraries:** PyYAML.
- **Tools:** weaver, jq, git, gh and uv; zizmor, run through uv.

`check_skill.py` fails on a file in a skill that isn't one of these, and on any Python in a skill.

## After every edit

```bash
python3 check_skill.py              # static: seconds, no network
```

It fails on a token, asset path, section marker or banned phrase out of place; a command the docs
give that isn't in `verified-commands.json`; a date, test round or machine path in the skill or
these tests; an asset that points at a skill; a file of a kind a skill may not hold.

`skeletons.py <skill>/assets/skeletons` resolves a skill's skeletons (`layout.md`, "Skeletons") for
every mix of choices, failing on a condition layout.md doesn't define, an unbalanced block, or a
marker left behind. The skills that ship skeletons run it on theirs.

After changing a check, run `python3 self_test.py --weaver --uv uv`. It breaks a copy of the skill
once per check and asserts that each check notices.

## Before calling a change done

These build scratch projects under `.work/`, or `--work DIR`.

```bash
python3 scenarios.py                # core alone; each collection and all of them through the template
                                    # test; golden drift; a subdirectory project; the install script
uv run workflows.py                 # the CI workflow as shipped and with layout.md's fallback: gate,
                                    # one weaver install per job, zizmor (pedantic, latest)
```

## When you change the skill

- **A command in the docs:** run it the way a user would, placeholders filled in. Then add it to
  `verified-commands.json` with `"status": "verified"` and `"how"`: what you ran, the versions of
  the tools it ran on, and what it showed. No dates, machine paths or names. `make <target>` forms
  of the project's own targets are exempt, since the scenarios run them.
- **A claim about a tool's behavior:** probe it first. Where a claim is code in the docs, as the
  fallback step is, test it from the doc, as `workflows.py` does.
- **One home per rule:** a rule lives in one file and the others point to it. Before changing a
  rule, search every file of the skill (and of the skills that build on it) for its copies and
  paraphrases, and change them together.
- **Anything new gets a test in the same change:** a new setting, token, section or part gets a
  scenario that exercises it. A mechanism with no test of its own is untested, however simple.
