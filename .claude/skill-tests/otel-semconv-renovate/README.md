# Tests for the otel-semconv-renovate skill

These scripts test the skill at `../../skills/otel-semconv-renovate/`. They live outside it, so they
aren't installed with it, and they aren't part of its instructions. They build on the base
skill's tests, which they expect at `../otel-semconv-base/`, and when the registry skill and its
tests are installed alongside (`../otel-semconv-registry/`), `renovate_extract.py` covers the
registry part's pins too. The base's `README.md` has the requirements and the tools policy; they
apply here too, plus npx (Node) for Renovate itself, since the config is only proven by Renovate.

## After every edit

```bash
python3 ../otel-semconv-base/check_skill.py .   # static: seconds, no network
```

## Before calling a change done

These build scratch projects under the base tests' `.work/`, or `--work DIR`.

```bash
python3 renovate_version.py         # part.md's version lookup and validator step (gh)
python3 renovate_extract.py         # part.md's extraction: Renovate reads every annotated pin (npx)
```

Validate the config itself with the command in `part.md`, "Checking the config", at the version
`assets/project/versions.env` pins.

## When you change the skill

The base's `README.md`, "When you change the skill", applies. A new pin in any part gets its
`# renovate:` line, a match string here if no existing one fits, and shows up in
`renovate_extract.py`'s report.
