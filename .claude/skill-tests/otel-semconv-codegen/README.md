# Tests for the otel-semconv-codegen skill

These scripts test the skill at `../../skills/otel-semconv-codegen/`. They live outside it, so they
aren't installed with it, and they aren't part of its instructions. They build on the base skill's
tests (its renderer, `add_part.py`, `check_skill.py` and workflow checks), which they expect at
`../otel-semconv-base/`. The base's `README.md` has the requirements and the tools policy; they
apply here too.

## After every edit

```bash
python3 ../otel-semconv-base/check_skill.py .   # static: seconds, no network
```

After changing a check, run `python3 self_test.py --weaver`. It breaks a copy of the skill once per
check and asserts that each check notices.

## Before calling a change done

These build scratch projects under the base tests' `.work/`, or `--work DIR`.

```bash
python3 codegen.py                  # a Python project from the core registry through every target;
                                    # the stubs fail until implemented; broken output fails validation
python3 filters.py                  # runs templates.md's filters on the fixture: what each selects
python3 template_types.py           # weaver's schema still allows only the kinds of value templates.md
                                    # covers; its enum mapping example on every member value type
uv run lint_workflows.py            # the workflow with the codegen job, public and private, with
                                    # setup-weaver and with the base's fallback: the base's checks
```

## When you change the skill

The base's `README.md`, "When you change the skill", applies: run every command before it goes in
the docs and record it in `verified-commands.json`; probe claims about tools; one home per rule; a
test for anything new, in the same change. Where a claim is code in the docs, as the filters and
the enum mapping are, test it from the doc.
