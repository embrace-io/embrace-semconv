"""Prove this skill's checks catch what they exist for: break a copy of the skill (laid out with
copies of the skills it builds on, and their tests, as they are installed) once per check, and
assert that the check fails on it.

Usage: self_test.py [--work DIR] [--weaver]
Static cases always run; --weaver adds the cases that need weaver, gh and network access.
"""
import os
import shutil
import subprocess
import sys

from _release import SKILL, TESTS, work_dir

NAME = os.path.basename(SKILL)
SKILLS = os.path.dirname(SKILL)
TESTS_ROOT = os.path.dirname(TESTS)
OTHERS = ("otel-semconv-base", "otel-semconv-registry")


def copy_skills(work, name):
    """Copies of this skill, the ones it builds on, and their tests; returns this skill's copy and
    its tests' copy."""
    root = os.path.join(work, "self-test", name)
    if os.path.exists(root):
        shutil.rmtree(root)
    ignore = shutil.ignore_patterns(".work", "__pycache__")
    for skill in (NAME, *OTHERS):
        shutil.copytree(os.path.join(SKILLS, skill), os.path.join(root, "skills", skill),
                        ignore=ignore)
        shutil.copytree(os.path.join(TESTS_ROOT, skill), os.path.join(root, "skill-tests", skill),
                        ignore=ignore)
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


def main():
    args = work_dir(__doc__, flags=("--weaver",))
    results = []

    skill, tests = copy_skills(args.work, "unbalanced")
    mutate(skill, "assets/skeletons/RELEASING.md", "<!-- skeleton: end -->\n", "")
    results.append(caught("an unbalanced skeleton block", [
        sys.executable, os.path.join(os.path.dirname(tests), "otel-semconv-base", "skeletons.py"),
        os.path.join(skill, "assets", "skeletons")], "never ended"))

    if args.weaver:
        work = os.path.join(args.work, "self-test", "weaver-work")
        # A tag lookup that reads any failure as "the tag is new" (fail-open).
        skill, tests = copy_skills(args.work, "fail-open")
        mutate(skill, "assets/release/.github/workflows/release.yml",
               'if [[ "$response" != *"(HTTP 404)"* ]]; then', "if false; then")
        results.append(caught("a tag lookup that fails open", [
            sys.executable, os.path.join(tests, "release_lookups.py"), "--work", work],
            "Could not check whether tag"))
        # A package that bakes another URI into the published manifest.
        skill, tests = copy_skills(args.work, "uri")
        mutate(skill, "assets/project/Makefile", "/releases/download/v$$version/resolved.yaml",
               "/releases/download/latest/resolved.yaml")
        results.append(caught("a manifest pointing at another release", [
            sys.executable, os.path.join(tests, "scenarios.py"), "--work", work, "package"],
            "SCENARIO PROBLEM"))
    print(("ok" if all(results) else "FAILED") + f": self-test ({len(results)} cases)")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
