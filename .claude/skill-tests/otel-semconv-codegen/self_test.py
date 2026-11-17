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

from _codegen import BASE_TESTS, SKILL, TESTS, work_dir

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
    mutate(skill, "assets/project/Makefile", "@@GENERATED_DIR@@", "@@UNLISTED_DIR@@")
    results.append(caught("a token missing from part.md", check_skill(tests), "[tokens]"))

    skill, tests = copy_skills(args.work, "command")
    mutate(skill, "SKILL.md", "## Rules", "Run `gh api repos/x/y --jq .unverified`.\n\n## Rules")
    results.append(caught("an unverified command", check_skill(tests), "[commands]"))

    if args.weaver:
        work = os.path.join(args.work, "self-test", "weaver-work")
        # templates.md's key-list filter without its `fixture.*` part selects nothing in the
        # fixture, so the template test would prove nothing.
        skill, tests = copy_skills(args.work, "filter")
        mutate(skill, "reference/templates.md",
               '(["<key>", "<key>"] | any(. == $key))\n                 or ($key | startswith("fixture."))',
               '(["<key>", "<key>"] | any(. == $key))')
        results.append(caught("a key-list filter that selects nothing in the fixture", [
            sys.executable, os.path.join(tests, "filters.py"), "--work", work, "key-list"],
            "FILTER PROBLEM"))
        # A CI fragment whose header no longer gives the aggregate job its needs entry.
        skill, tests = copy_skills(args.work, "needs")
        mutate(skill, "assets/project/ci-validation.yaml", "#   - validate-generated # codegen\n",
               "")
        results.append(caught("a CI job the aggregate job doesn't need", [
            sys.executable, os.path.join(tests, "codegen.py"), "--work", work, "core"],
            "CODEGEN PROBLEM"))
    print(("ok" if all(results) else "FAILED") + f": self-test ({len(results)} cases)")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
