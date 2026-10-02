"""Prove the checks catch what they exist for: copy the skill, make one known-bad edit, and assert
the right check fails. A check that has never been seen failing proves nothing.

Usage: self_test.py [--weaver] [--uv UV] [--work DIR]
--weaver also breaks the curated and subset filters in templates.md, a Renovate match string,
the release workflow's tag lookup and the attributes docs template's examples, and runs
curated_filter.py, subset_filter.py, renovate_extract.py, renovate_version.py, release_lookups.py
and the matrix's
minimal-fields scenario (needs weaver, npx, a logged-in gh and network). --uv UV (the uv command, e.g. `uv`) also drops a job from the CI gate's `needs` and
runs parse_workflows.py, and puts back a `uses: ./...` and runs lint_workflows.py (network).
Run this after changing any check.
"""
import os
import shutil
import subprocess
import sys

from _common import SKILL, work_dir

# (check tag that must fail, file, old text or None to append, new text)
MUTATIONS = [
    ("commands", "reference/templates.md", None,
     "\nRun `gh run list --commit abc123` to see it.\n"),
    ("rules", "reference/glossary.md", None,
     "\nA stable signal references a less stable attribute only at `opt_in`.\n"),
    ("rules", "assets/project/registry/CONTRIBUTING.md", "less stable attribute",
     "lower-stability attribute"),
    ("coverage", "assets/project/Makefile", "WEAVER_FLAGS :=\n", "WEAVER_FLAGS :=\nNEW_SETTING :=\n"),
    ("tokens", "assets/project/Makefile", None, "# @@NEW_TOKEN@@\n"),
    ("phrases", "reference/versioning.md", None, "\nThis is how a version is cut.\n"),
    ("phrases", "assets/project/Makefile", None, "# Built from layout version 2.\n"),
    ("breadcrumbs", "assets/common/.gitignore", None, "# Copied from the otel-semconv-setup skill.\n"),
    ("conditions", "assets/project/registry/README.md", None,
     '<!-- skeleton: only for stability "beta" -->\nBeta.\n<!-- skeleton: end -->\n'),
    ("asset paths", "reference/layout.md", None, "\nSee `assets/no-such-file.txt`.\n"),
    ("privacy", "tests/verified-commands.json", "names a tool or subcommand in prose",
     "names a tool (checked 2026-01-01) in prose"),
    ("privacy", "tests/field/targets.json", "\"embrace-io/embrace-semconv\"",
     "\"/Users/someone/work/embrace-semconv\""),
    ("languages", "tests/new_check.rb", None, "puts 'a new language'\n"),
    ("languages", "assets/common/setup.py", None, "print('Python in the layout')\n"),
    # The old default: relative to the project, so a project in a subdirectory misses the actions
    ("actions-dir", "assets/project/Makefile",
     "ACTIONS_DIR := $(or $(shell git rev-parse --show-toplevel 2>/dev/null),.)/.github/actions",
     "ACTIONS_DIR := .github/actions"),
]
# Breaks whose checks need network access, run with --weaver.
NETWORK_BREAKS = [
    ("curated-filter", "reference/templates.md",
     "(((.registry.attributes // []) | map(select(.provenance.source | not)))",
     "(((.registry.attributes // []))"),
    # `startswith` on the key list rather than the key: jq fails on it
    ("subset-filter", "reference/templates.md",
     'or ($key | startswith("fixture."))', 'or startswith("fixture.")'),
    # A match string that no longer fits versions.env's weaver pin: the config stays valid
    ("renovate-extract", "assets/renovate/.github/renovate.json5",
     "\\\\s+WEAVER_VERSION=", "\\\\s+WEAVER="),
    # The tag lookup reading any failure as "the tag is new" again
    ("release-lookups", "assets/release/.github/workflows/release.yml",
     'if [[ "$response" != *"(HTTP 404)"* ]]; then', "if false; then"),
    # The attributes docs template iterating any non-string `examples` again: a single number fails
    ("minimal-fields", "assets/docs/templates/registry/markdown/macros.j2",
     "    {%- elif values is sequence -%}\n", "    {%- else -%}\n"),
    # The one-file-per-namespace example without its provenance filter: imports leak in
    ("subset-filter", "reference/templates.md",
     "      (.registry.attributes // [])\n      | map(select(.provenance.source | not))\n"
     "      | group_by(.key | split(\".\") | .[0])\n",
     "      (.registry.attributes // [])\n      | group_by(.key | split(\".\") | .[0])\n"),
    # The Renovate version lookup reading a footer field that isn't there: every repo falls back
    ("renovate-version", "reference/layout.md", ".updatedInVer // .createdInVer'\n",
     ".updatedVer // .createdVer'\n"),
    # The recorded kinds missing one weaver allows, as after a weaver upgrade adds a type
    ("template-types", "tests/fixtures/template-types.json", '"any", "boolean", ',
     '"boolean", '),
    # The recorded always-present fields missing one, as when weaver makes an optional one required
    ("template-types", "tests/fixtures/template-types.json", '"AttributeGroup.attributes", ',
     ""),
    # templates.md's mapping example without a branch for doubles: 1.5 hits the fallback
    ("template-types", "reference/templates.md",
     "  {%- elif member.value is float %}\n  const val {{ name }}: Double = {{ member.value }}\n",
     ""),
]
# Checks run by their own script, the text their failure prints, and the script's arguments.
SCRIPTS = {"curated-filter": ("curated_filter.py", "FILTER PROBLEM"),
           "subset-filter": ("subset_filter.py", "FILTER PROBLEM"),
           "actions-dir": ("actions_dir.py", "ACTIONS_DIR PROBLEM"),
           "renovate-extract": ("renovate_extract.py", "RENOVATE PROBLEM"),
           "renovate-version": ("renovate_version.py", "RENOVATE VERSION PROBLEM"),
           "release-lookups": ("release_lookups.py", "RELEASE PROBLEM"),
           "minimal-fields": ("matrix.py", "FAILED: minimal-fields", ["minimal-fields"]),
           "template-types": ("template_types.py", "TYPES PROBLEM")}
GATE_BREAK = ("assets/project/ci-validation.yaml", "      - test-policies # registry attributes\n")


def gate_case(work, uv):
    """A gate job missing one of the jobs in its `needs`: parse_workflows.py must fail."""
    copy = copy_skill(work, "gate")
    mutate(copy, GATE_BREAK[0], GATE_BREAK[1], "")
    rendered = os.path.join(work, "self-test", "gate-work")
    project = os.path.join(rendered, "matrix", "project")
    if os.path.exists(rendered):
        shutil.rmtree(rendered)
    subprocess.run([sys.executable, os.path.join(copy, "tests", "render_layout.py"), project,
                    "registry,docs,attributes,attribute-groups",
                    os.path.join(copy, "tests", "fixtures", "tokens", "acme.json")],
                   check=True, capture_output=True)
    result = subprocess.run([uv, "run", os.path.join(copy, "tests", "parse_workflows.py"),
                             rendered], capture_output=True, text=True)
    output = result.stdout + result.stderr
    caught = result.returncode != 0 and "FAILED" in output and "gate" in output
    print(("ok" if caught else "FAILED") + ": parse_workflows catches a gate missing a job")
    if not caught:
        print(output)
    return caught


def zizmor_case(work, uv):
    """A local action used as `uses: ./...` again: lint_workflows.py must fail on zizmor."""
    copy = copy_skill(work, "zizmor")
    mutate(copy, "assets/project/ci-validation.yaml", "uses: $/.github/actions/setup-weaver",
           "uses: ./.github/actions/setup-weaver")
    result = subprocess.run([sys.executable, os.path.join(copy, "tests", "lint_workflows.py"),
                             "--uv", uv, "--work", os.path.join(work, "self-test", "zizmor-work")],
                            capture_output=True, text=True)
    output = result.stdout + result.stderr
    caught = result.returncode != 0 and "self-repository" in output
    print(("ok" if caught else "FAILED") + ": lint_workflows catches a `uses: ./` zizmor flags")
    if not caught:
        print(output)
    return caught


def copy_skill(work, name):
    dest = os.path.join(work, "self-test", name, os.path.basename(SKILL))
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(SKILL, dest, ignore=shutil.ignore_patterns(".work", "__pycache__"))
    return dest


def mutate(copy, rel, old, new):
    path = os.path.join(copy, rel)
    text = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
    if old is None:
        text += new
    elif old in text:
        text = text.replace(old, new, 1)
    else:
        raise SystemExit(f"self_test: '{old}' not found in {rel}: update the mutation")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def check(copy, script, work, extra=()):
    args = [sys.executable, os.path.join(copy, "tests", script), *extra]
    if script != "check_skill.py":
        args += ["--work", os.path.join(work, "self-test", "filter-work")]
    return subprocess.run(args, capture_output=True, text=True)


def main():
    args = work_dir(__doc__, flags=("--weaver",), options=("--uv",))
    work, ok = args.work, True
    baseline = check(copy_skill(work, "baseline"), "check_skill.py", work)
    print(("ok" if baseline.returncode == 0 else "FAILED") + ": unmodified skill passes")
    ok &= baseline.returncode == 0
    cases = MUTATIONS + (NETWORK_BREAKS if args.weaver else [])
    for number, (tag, rel, old, new) in enumerate(cases, 1):
        copy = copy_skill(work, f"mutation-{number}")
        mutate(copy, rel, old, new)
        script, expected, *extra = SCRIPTS.get(tag, ("check_skill.py", f"[{tag}]"))
        result = check(copy, script, work, *extra)
        output = result.stdout + result.stderr
        caught = result.returncode != 0 and expected in output
        print(("ok" if caught else "FAILED") + f": {tag} catches a bad edit to {rel}")
        if not caught:
            print(output)
        ok &= caught
    if args.uv:
        ok &= gate_case(work, args.uv)
        ok &= zizmor_case(work, args.uv)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
