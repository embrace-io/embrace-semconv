# Tests for the otel-semconv-update skill

These scripts test the skill at `../../skills/otel-semconv-update/`. They live outside it, so they
aren't installed with it, and they aren't part of its instructions. They use the base skill's
tests, which they expect at `../otel-semconv-base/`.

The skill has no assets: each practice is applied, and tested, by the skill that owns it. What is
checked here is the skill's own text.

```bash
python3 ../otel-semconv-base/check_skill.py .   # static: commands, phrases, privacy
python3 practices.py                            # the practices table: numbered, filled, owned
```

## When you change the skill

The base's `README.md`, "When you change the skill", applies. When a skill sets up a new practice,
add its row to `reference/practices.md`, in the order it applies, with how to tell a repo lacks it.
