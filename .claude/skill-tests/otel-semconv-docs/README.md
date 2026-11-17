# Tests for the otel-semconv-docs skill

These scripts test the skill at `../../skills/otel-semconv-docs/`. They live outside it, so they
aren't installed with it, and they aren't part of its instructions. They build on the base and
registry skills' tests, which they expect at `../otel-semconv-base/` and
`../otel-semconv-registry/`. The base's `README.md` has the requirements and the tools policy; they
apply here too.

## After every edit

```bash
python3 ../otel-semconv-base/check_skill.py .   # static: seconds, no network
python3 ../otel-semconv-base/skeletons.py ../../skills/otel-semconv-docs/assets/skeletons
```

After changing a check, run `python3 self_test.py --weaver`. It breaks a copy of the skill once per
check and asserts that each check notices.

## Before calling a change done

These build scratch projects under the base tests' `.work/`, or `--work DIR`.

```bash
python3 scenarios.py                # docs for a registry with an import, one of events, with the
                                    # .weaver.toml template settings; and whether the shared
                                    # templates still need the import exclusion
uv run lint_workflows.py            # the workflow with the registry and docs jobs, public and private,
                                    # with setup-weaver and the fallback
```

When `workaround-still-needed` fails, the shared templates leave imported definitions out on
their own: remove `templates/registry/docs-import-only/` from the assets and its step from the
Makefile section, the part's "Imported definitions", and that scenario, in one change.

## When you change the skill

The base's `README.md`, "When you change the skill", applies.
