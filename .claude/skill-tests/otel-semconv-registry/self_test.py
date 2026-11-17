"""Prove this skill's checks catch what they exist for: break a copy of the skill (laid out with a
copy of the base skill, and both their tests, as they are installed) once per check, and assert
that the check fails on it.

Usage: self_test.py [--work DIR] [--weaver]
Static cases always run; --weaver adds the cases that need weaver and network access.
"""
import os
import shutil
import subprocess
import sys

from _registry import BASE_TESTS, SKILL, TESTS, work_dir

NAME = os.path.basename(SKILL)
BASE = os.path.join(os.path.dirname(SKILL), "otel-semconv-base")


def copy_skills(work, name):
    """Copies of both skills and their tests; returns this skill's copy and its tests' copy."""
    root = os.path.join(work, "self-test", name)
    if os.path.exists(root):
        shutil.rmtree(root)
    ignore = shutil.ignore_patterns(".work", "__pycache__")
    for src, dest in ((SKILL, ("skills", NAME)), (BASE, ("skills", "otel-semconv-base")),
                      (TESTS, ("skill-tests", NAME)),
                      (BASE_TESTS, ("skill-tests", "otel-semconv-base"))):
        shutil.copytree(src, os.path.join(root, *dest), ignore=ignore)
    return os.path.join(root, "skills", NAME), os.path.join(root, "skill-tests", NAME)


def mutate(skill, rel, old, new):
    path = os.path.join(skill, rel)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if old not in text:
        raise SystemExit(f"self_test is stale: {rel} no longer contains {old!r}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.replace(old, new, 1))


def caught(label, args, expected):
    result = subprocess.run(args, capture_output=True, text=True)
    output = result.stdout + result.stderr
    ok = result.returncode != 0 and expected in output
    print(("ok" if ok else "FAILED") + f": {label} is caught")
    if not ok:
        print(output)
    return ok


def check_skill(tests):
    """The base's static checks, run on the copied skill's tests directory."""
    return [sys.executable, os.path.join(os.path.dirname(tests), "otel-semconv-base",
                                         "check_skill.py"), tests]


def main():
    args = work_dir(__doc__, flags=("--weaver",))
    results = []

    skill, tests = copy_skills(args.work, "token")
    mutate(skill, "assets/registry/model/manifest.yaml", "@@REGISTRY_DESCRIPTION@@",
           "@@UNLISTED_DESCRIPTION@@")
    results.append(caught("a token missing from part.md", check_skill(tests), "[tokens]"))

    skill, tests = copy_skills(args.work, "breadcrumb")
    mutate(skill, "assets/registry/model/manifest.yaml", "# `schema_url` alone",
           "# Set up by otel-semconv-registry. `schema_url` alone")
    results.append(caught("an asset that names the skill", check_skill(tests), "[breadcrumbs]"))

    if args.weaver:
        # validate-dependencies no longer checks that each declared schema_url is in the tree:
        # test-validations finds its case passing.
        skill, tests = copy_skills(args.work, "dependencies")
        mutate(skill, "assets/project/Makefile", "    if (!(url in loaded)) {",
               "    if (0) {")
        results.append(caught("a validation that stops failing", [
            sys.executable, os.path.join(tests, "scenarios.py"), "--work",
            os.path.join(args.work, "self-test", "weaver-work"), "groups-only"],
            "SCENARIO PROBLEM"))
    print(("ok" if all(results) else "FAILED") + f": self-test ({len(results)} cases)")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
