"""Prove the checks catch what they exist for: break a copy of the skill once per check, and
assert that the check fails on it.

Usage: self_test.py [--work DIR] [--weaver] [--uv UV] [--npx]
Static cases always run. --weaver adds the cases that need weaver and network access; --uv adds
the workflow cases (zizmor through uv, PyYAML); --npx the Renovate case (npx, network).
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
    ("codegen-token", "assets/project/Makefile", "@@GENERATED_DIR@@", "@@UNLISTED_DIR@@",
     "[tokens]"),
    ("asset-path", "SKILL.md", "(`assets/core/versions.env`)",
     "(`assets/core/no-such-file`)", "[asset paths]"),
    ("command", "SKILL.md", "`make install-weaver` installs it.",
     "`make install-weaver` installs it, or `gh api repos/x/y --jq .unverified`.", "[commands]"),
    ("marker", "assets/project/Makefile", "# ==== end templates\n", "", "[markers]"),
    ("privacy", "reference/layout.md", "## Copying", "Seen on 2030-01-01.\n\n## Copying",
     "[privacy]"),
    ("breadcrumb", "assets/core/.gitignore", "/.build/", "/.build/  # from otel-semconv-codegen",
     "[breadcrumbs]"),
    ("language", "assets/core/scripts/helper.py", None, "print('a project needs no Python')\n",
     "[languages]"),
    ("phrase", "reference/sources.md", "## A private source registry",
     "Pin the upstream registry.\n\n## A private source registry", "[phrases]"),
    ("stale-command", "SKILL.md", " (`gh run watch`)", "", "[commands]"),
    ("wrapped-command", "reference/sources.md", "## A private source registry",
     "Run `gh api repos/x/y\n  --jq .unverified`.\n\n## A private source registry", "[commands]"),
]

# Dynamic cases: (name, "skill" or "tests", file, old text, new text, test command, its arguments,
# text the failure prints, the flag that enables the case).
DYNAMIC = [
    ("a test-templates that never fails", "skill", "assets/project/Makefile",
     "@if ! git --no-pager diff", "@if false && git --no-pager diff",
     "scenarios.py", ["golden-drift"], "SCENARIO PROBLEM", "weaver"),
    ("a RUN_WEAVER that ignores weaver's failure", "skill", "assets/project/Makefile",
     "\nif [[ $$status -ne 0 ]]; then exit $$status; fi\n", "\n",
     "scenarios.py", ["weaver-failure"], "SCENARIO PROBLEM", "weaver"),
    ("a RUN_WEAVER that ignores dead imports", "skill", "assets/project/Makefile",
     'if [[ -n "$$unmatched" ]]; then', "if false; then",
     "scenarios.py", ["dead-import"], "SCENARIO PROBLEM", "weaver"),
    ("a private section that sets no flag", "skill", "assets/project/Makefile",
     "WEAVER_FLAGS += --allow-git-credentials\n", "",
     "scenarios.py", ["private"], "SCENARIO PROBLEM", "weaver"),
    ("a fixture manifest an older weaver rejects", "skill",
     "assets/templates/templates_test/fixture/manifest.yaml",
     "schema_url: https://example.com/schemas/templates-fixture/",
     "file_format: definition_manifest/2.0\nschema_url: https://example.com/schemas/templates-fixture/",
     "scenarios.py", ["older-weaver"], "SCENARIO PROBLEM", "weaver"),
    ("a fixture weaver warns about", "skill",
     "assets/collections/metrics/templates_test/fixture/fixture/metrics.yaml",
     '    unit: "1"\n    requirement_level: recommended\n', '    unit: "1"\n',
     "scenarios.py", ["only-metrics"], "SCENARIO PROBLEM", "weaver"),
    ("a GENERATED_DIR guard that lets .. through", "skill", "assets/project/Makefile",
     '""|.|./|/|..|../|', '""|.|./|/|', "scenarios.py", ["generated-dir-guard"],
     "SCENARIO PROBLEM", "weaver"),
    ("a drift check at the project-relative path", "skill", "assets/project/ci-validation.yaml",
     "path: @@GENERATED_REPO_PATH@@", "path: @@GENERATED_DIR@@",
     "scenarios.py", ["subdirectory"], "SCENARIO PROBLEM", "weaver"),
    # templates.md's key-list filter without its `fixture.*` part selects nothing in the
    # fixture, so the template test would prove nothing.
    ("a key-list filter that selects nothing in the fixture", "skill", "reference/templates.md",
     '(["<key>", "<key>"] | any(. == $key))\n                 or ($key | startswith("fixture."))',
     '(["<key>", "<key>"] | any(. == $key))', "filters.py", ["key-list"], "FILTER PROBLEM",
     "weaver"),
    ("a key-list filter whose list matches every key", "skill", "reference/templates.md",
     '(["<key>", "<key>"] | any(. == $key))', '(["<key>", "<key>"] | any(. != $key))',
     "filters.py", ["key-list-filled"], "FILTER PROBLEM", "weaver"),
    ("a Kotlin example with no deprecation marker", "skill", "reference/templates.md",
     '    @Deprecated("{{', '    // Deprecated("{{', "examples.py", [], "EXAMPLE PROBLEM", "weaver"),
    ("a codegen template that drops deprecated attributes", "tests",
     "fixtures/codegen/python/weaver.yaml", "      | map(select(.provenance.source | not))\n",
     "      | map(select(.provenance.source | not))\n      | map(select(.deprecated | not))\n",
     "codegen.py", ["core"], "CODEGEN PROBLEM", "weaver"),
    ("a CI job the aggregate job doesn't need", "skill", "assets/project/ci-validation.yaml",
     "      - validate-generated # codegen\n", "", "codegen.py", ["core"], "CODEGEN PROBLEM",
     "weaver"),
    ("a pin no match string fits", "skill", "assets/renovate/.github/renovate.json5",
     '"# renovate: datasource=(?<datasource>\\\\S+) depName=(?<depName>\\\\S+) '
     'versioning=(?<versioning>\\\\S+)\\\\s+SOURCE_REGISTRY',
     '"# renovate: datasource=(?<datasource>\\\\S+) depName=(?<depName>\\\\S+) '
     'versioning=(?<versioning>\\\\S+)\\\\s+NO_SUCH_SETTING',
     "renovate_extract.py", ["core"], "pinned but Renovate didn't extract it", "npx"),
    ("a registry_path no match string reads", "skill", "assets/renovate/.github/renovate.json5",
     "\\\\s+registry_path:", "\\\\s+no_such_field:", "renovate_extract.py", ["core"],
     "pinned but Renovate didn't extract it", "npx"),
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
    args = work_dir(__doc__, flags=("--weaver", "--npx"), options=("--uv",))
    results = []
    for name, rel, old, new, expected in STATIC:
        skill, tests = copy_skill(args.work, name)
        mutate(skill, rel, old, new)
        results.append(caught(name, [sys.executable, os.path.join(tests, "check_skill.py")],
                              expected))
    enabled = {"weaver": args.weaver, "npx": args.npx}
    for number, (label, where, rel, old, new, script, names, expected, flag) in enumerate(DYNAMIC):
        if not enabled[flag]:
            continue
        skill, tests = copy_skill(args.work, f"dynamic-{number}")
        mutate(skill if where == "skill" else tests, rel, old, new)
        work = os.path.join(args.work, "self-test", f"dynamic-{number}-work")
        results.append(caught(label, [sys.executable, os.path.join(tests, script),
                                      "--work", work, *names], expected))
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
