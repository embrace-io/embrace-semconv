# Tests for the otel-semconv-registry skill

These scripts test the skill at `../../skills/otel-semconv-registry/`. They live outside it, so they
aren't installed with it, and they aren't part of its instructions. They build on the base skill's
tests (its renderer, `add_part.py`, `check_skill.py` and workflow checks), which they expect at
`../otel-semconv-base/`. The base's `README.md` has the requirements and the tools policy; they
apply here too, plus opa for the policy tests.

## After every edit

```bash
python3 ../otel-semconv-base/check_skill.py .   # static: seconds, no network
```

After changing a check, run `python3 self_test.py --weaver`. It breaks a copy of the skill once per
check and asserts that each check notices.

## Before calling a change done

These build scratch projects under the base tests' `.work/`, or `--work DIR`.

```bash
python3 scenarios.py                # a registry per mix of collections and local policies (none, its
                                    # own, public-groups), with and without the base's templates
                                    # part: validate-registry, test-validations, test-policies
uv run lint_workflows.py            # the workflow with the registry's jobs, public and private, with and
                                    # without templates, with setup-weaver and the fallback
```

## When you change the skill

The base's `README.md`, "When you change the skill", applies. A new validation gets its invalid
registry under `assets/registry/validations_test/` (`reference/validations.md`, "Adding a
validation"); the scenarios then run it in every project.
