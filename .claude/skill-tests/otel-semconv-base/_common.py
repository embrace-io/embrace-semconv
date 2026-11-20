"""Paths and helpers shared by the skill's test scripts. Not part of the skill's instructions.

The tests of a skill live outside it, so they aren't installed with it: `skill-tests/<skill>/`
next to `skills/<skill>/`.
"""
import argparse
import os
import subprocess


def skill_of(tests):
    """The skill directory whose tests are in TESTS."""
    return os.path.join(os.path.dirname(os.path.dirname(tests)), "skills", os.path.basename(tests))


TESTS = os.path.dirname(os.path.abspath(__file__))
SKILL = skill_of(TESTS)
ASSETS = os.path.join(SKILL, "assets")
FIXTURES = os.path.join(TESTS, "fixtures")
RENDER = os.path.join(TESTS, "render.py")
TOKENS = os.path.join(FIXTURES, "tokens", "base.json")
COLLECTIONS = ("attributes", "attribute-groups", "events", "metrics", "spans", "entities")


def work_dir(description, flags=(), options=()):
    """Parse --work DIR (default .work here, which .gitignore keeps out of git), any FLAGS
    (on/off options), any OPTIONS (each taking a value), and scenario names."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("names", nargs="*", help="scenarios to run (default: all)")
    parser.add_argument("--work", default=os.path.join(TESTS, ".work"),
                        help="where to build scratch projects and logs")
    for flag in flags:
        parser.add_argument(flag, action="store_true")
    for option in options:
        parser.add_argument(option)
    args = parser.parse_args()
    os.makedirs(args.work, exist_ok=True)
    return args


def run(work, label, args, cwd=None, env=None):
    """Run a command, log its output to WORK/logs/LABEL.log, print ok/FAILED, return success."""
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    logs = os.path.join(work, "logs")
    os.makedirs(logs, exist_ok=True)
    log = os.path.join(logs, f"{label}.log")
    with open(log, "w") as f:
        f.write(result.stdout + result.stderr)
    print(("ok" if result.returncode == 0 else "FAILED") + f": {label} (log: {log})")
    return result.returncode == 0


def output(args, cwd=None, env=None):
    """Run a command and return (exit status, stdout + stderr)."""
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()
