"""Paths and helpers shared by the skill's test scripts. Not part of the skill's instructions.

The tests of a skill live outside it, so they aren't installed with it: `skill-tests/<skill>/`
next to `skills/<skill>/`.
"""
import argparse
import os
import re
import subprocess
import sys


def skill_of(tests):
    """The skill directory whose tests are in TESTS."""
    return os.path.join(os.path.dirname(os.path.dirname(tests)), "skills", os.path.basename(tests))


TESTS = os.path.dirname(os.path.abspath(__file__))
SKILL = skill_of(TESTS)
ASSETS = os.path.join(SKILL, "assets")
FIXTURES = os.path.join(TESTS, "fixtures")
RENDER = os.path.join(TESTS, "render.py")
# The tokens of a Python codegen project generated from the core registry.
TOKENS = os.path.join(FIXTURES, "tokens", "codegen.json")
# The same, testing only the template that lists every convention the fixture resolves to
# (fixtures/templates/registry/keys/), for the scenarios that exercise the template test alone.
KEYS_TOKENS = os.path.join(FIXTURES, "tokens", "keys.json")
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


def render_project(work, label, dest, chosen, tokens=TOKENS):
    """Render a project into DEST with render.py: core, templates and codegen, plus CHOSEN (other
    parts, collections, `private`). Returns success."""
    os.makedirs(dest, exist_ok=True)
    return run(work, f"{label}-render", [sys.executable, RENDER, dest, ",".join(chosen), tokens])


def pinned_version():
    """The Renovate version versions.env's renovate section pins."""
    match = re.search(r"^RENOVATE_VERSION=(\S+)$",
                      read(os.path.join(ASSETS, "core", "versions.env")), re.M)
    if not match:
        raise SystemExit("versions.env: no RENOVATE_VERSION")
    return match.group(1)


def output(args, cwd=None, env=None):
    """Run a command and return (exit status, stdout + stderr)."""
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()
