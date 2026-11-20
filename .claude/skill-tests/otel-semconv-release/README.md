# Tests for the otel-semconv-release skill

These scripts test the skill at `../../skills/otel-semconv-release/`. They live outside it, so they
aren't installed with it, and they aren't part of its instructions. They build on the base and
registry skills' tests, which they expect at `../otel-semconv-base/` and
`../otel-semconv-registry/`. The base's `README.md` has the requirements and the tools policy; they
apply here too, plus a logged-in gh for the lookups.

## After every edit

```bash
python3 ../otel-semconv-base/check_skill.py .   # static: seconds, no network
python3 ../otel-semconv-base/skeletons.py ../../skills/otel-semconv-release/assets/skeletons
```

After changing a check, run `python3 self_test.py --weaver`. It breaks a copy of the skill once per
check and asserts that each check notices.

## Before calling a change done

These build scratch projects under the base tests' `.work/`, or `--work DIR`.

```bash
python3 scenarios.py                # print-version and package (no token in the published manifest),
                                    # and a -dev family's VERSION_SUFFIX
python3 release_lookups.py          # release.yml's tag and draft lookups: only "not found" is an answer
uv run lint_workflows.py            # the release workflow, public and private, with setup-weaver
                                    # (uncached) and the fallback
```

## When you change the skill

The base's `README.md`, "When you change the skill", applies. A change to the release workflow's
lookups goes through `release_lookups.py`, which runs the steps from the asset itself.
