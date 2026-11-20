"""Prove the checks catch what they exist for: break a copy of the skill once per check, and
assert that the check fails on it.

Usage: self_test.py [--work DIR] [--weaver] [--uv UV]
Static cases always run. --weaver adds the scenarios' cases (weaver, network); --uv adds the
workflow cases (zizmor through uv, PyYAML).
"""
import os
import shutil
import subprocess
import sys

from _common import SKILL, TESTS, work_dir

NAME = os.path.basename(SKILL)

# (name, file in the skill, old text, new text, text the check's failure prints)
STATIC = [
    ("token", "assets/core/versions.env", "WEAVER_VERSION=v",
     "@@UNLISTED_TOKEN@@\nWEAVER_VERSION=v", "[tokens]"),
    ("asset-path", "SKILL.md", "(`assets/core/versions.env`)",
     "(`assets/core/no-such-file`)", "[asset paths]"),
    ("command", "SKILL.md", "`make install-weaver` installs it.",
     "`make install-weaver` installs it, or `gh api repos/x/y --jq .unverified`.", "[commands]"),
    ("marker", "assets/project/Makefile", "# ==== end templates\n", "", "[markers]"),
    ("privacy", "reference/layout.md", "## Copying", "Seen on 2030-01-01.\n\n## Copying",
     "[privacy]"),
    ("breadcrumb", "assets/core/.gitignore", "/.build/", "/.build/  # from otel-semconv-base",
     "[breadcrumbs]"),
    ("language", "assets/core/scripts/helper.py", None, "print('a project needs no Python')\n",
     "[languages]"),
]


def copy_skill(work, name):
    """A copy of the skill and its tests, laid out as they are installed; returns both paths."""
    root = os.path.join(work, "self-test", name)
    if os.path.exists(root):
        shutil.rmtree(root)
    ignore = shutil.ignore_patterns(".work", "__pycache__")
    skill = os.path.join(root, "skills", NAME)
    tests = os.path.join(root, "skill-tests", NAME)
    shutil.copytree(SKILL, skill, ignore=ignore)
    shutil.copytree(TESTS, tests, ignore=ignore)
    return skill, tests


def mutate(skill, rel, old, new):
    path = os.path.join(skill, rel)
    if old is None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return
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
    args = work_dir(__doc__, flags=("--weaver",), options=("--uv",))
    results = []
    for name, rel, old, new, expected in STATIC:
        skill, tests = copy_skill(args.work, name)
        mutate(skill, rel, old, new)
        results.append(caught(name, [sys.executable, os.path.join(tests, "check_skill.py")],
                              expected))
    # A skeleton block whose condition layout.md doesn't define: skeletons.py fails on it.
    skeletons = os.path.join(args.work, "self-test", "skeleton")
    os.makedirs(skeletons, exist_ok=True)
    with open(os.path.join(skeletons, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Title\n<!-- skeleton: only when the moon is full -->\nText.\n"
                "<!-- skeleton: end -->\n")
    results.append(caught("a skeleton condition layout.md doesn't define",
                          [sys.executable, os.path.join(TESTS, "skeletons.py"), skeletons],
                          "when the moon is full"))
    if args.weaver:
        # A templates section whose test-templates no longer compares: the drift scenario fails.
        skill, tests = copy_skill(args.work, "golden-compare")
        mutate(skill, "assets/project/Makefile", "@if ! git --no-pager diff",
               "@if false && git --no-pager diff")
        results.append(caught("a test-templates that never fails",
                              [sys.executable, os.path.join(tests, "scenarios.py"),
                               "--work", os.path.join(args.work, "self-test", "golden-work"),
                               "golden-drift"], "SCENARIO PROBLEM"))
    if args.uv:
        # A local action used as `uses: ./...`: zizmor reports it.
        skill, tests = copy_skill(args.work, "zizmor")
        mutate(skill, "assets/project/ci-validation.yaml", "      - name: Compare what",
               "      - uses: ./.github/actions/assert-no-drift\n        with:\n          path: x\n"
               "          label: x\n          regenerate-hint: x\n\n      - name: Compare what")
        results.append(caught("a `uses: ./` zizmor flags",
                              [args.uv, "run", os.path.join(tests, "workflows.py"), "--uv",
                               args.uv, "--work", os.path.join(args.work, "self-test", "z-work")],
                              "self-repository"))
        # A fallback snippet that no longer replaces the action's steps.
        skill, tests = copy_skill(args.work, "fallback")
        mutate(skill, "reference/layout.md", "run: make install-weaver", "run: make install")
        results.append(caught("a fallback that isn't make install-weaver",
                              [args.uv, "run", os.path.join(tests, "workflows.py"), "--uv",
                               args.uv, "--work", os.path.join(args.work, "self-test", "f-work")],
                              "the fallback still uses the action"))
    print(("ok" if all(results) else "FAILED") + f": self-test ({len(results)} cases)")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
