"""Follow reference/layout.md "Copying the layout" mechanically, as a test double for an agent.

Usage: render_layout.py DEST FEATURES,COLLECTIONS TOKENS.json [--overwrite]
The second argument lists features and collections together, comma-separated (common and
templates are implied; `private` keeps the workflows' private sections). Without --overwrite,
existing files are left alone and reported.
"""
import json
import os
import re
import sys

from _common import ASSETS

FEATURE_DIRS = {"common", "registry", "docs", "release", "renovate"}
COLLECTIONS = {"attributes", "attribute-groups", "events", "metrics", "spans", "entities"}
SECTIONED = {"Makefile", "versions.env", ".github/workflows/ci-validation.yaml",
             ".github/workflows/release.yml",
             "templates/registry/markdown/weaver.yaml", "templates/registry/markdown/readme.md.j2"}
MARK = r"^\s*(?:#|\{#-?) ==== "


def strip_sections(text, keep):
    out, skipping = [], None
    for line in text.splitlines(keepends=True):
        start = re.match(MARK + r"(?!end )([a-z-]+)", line)
        end = re.match(MARK + r"end ([a-z-]+)", line)
        if skipping:
            if end and end.group(1) == skipping:
                skipping = None
            continue
        if start and start.group(1) not in keep:
            skipping = start.group(1)
            continue
        tagged = re.match(r"^\s*- [a-z-]+ # ([a-z -]+?)\s*$", line)
        if tagged and not set(tagged.group(1).split()) <= keep:
            continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "".join(out))


def check_markers(rel, text, keep):
    stack, problems = [], []
    for number, line in enumerate(text.splitlines(), 1):
        start = re.match(MARK + r"(?!end )([a-z-]+)", line)
        end = re.match(MARK + r"end ([a-z-]+)", line)
        if start:
            stack.append(start.group(1))
            if start.group(1) not in keep:
                problems.append(f"{rel}:{number}: section {start.group(1)} was not chosen")
        elif end:
            if not stack or stack.pop() != end.group(1):
                problems.append(f"{rel}:{number}: unbalanced end {end.group(1)}")
    problems += [f"{rel}: unclosed section {name}" for name in stack]
    return problems


def main():
    dest, chosen, tokens_path = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
    overwrite = "--overwrite" in sys.argv
    keep = {"project", "common", "templates", *chosen}
    if not COLLECTIONS & keep:
        print("error: choose at least one collection")
        return 1
    with open(tokens_path) as f:
        tokens = json.load(f)
    bases = [os.path.join(ASSETS, f) for f in sorted(FEATURE_DIRS & keep)]
    for collection in sorted(COLLECTIONS & keep):
        for feature in sorted(FEATURE_DIRS & keep):
            bases.append(os.path.join(ASSETS, "collections", collection, feature))
    plan = []
    for base in bases:
        for dirpath, _, names in os.walk(base):
            for name in sorted(names):
                src = os.path.join(dirpath, name)
                plan.append((src, os.path.relpath(src, base)))
    project = os.path.join(ASSETS, "project")
    plan.append((os.path.join(project, "Makefile"), "Makefile"))
    plan.append((os.path.join(project, "ci-validation.yaml"), ".github/workflows/ci-validation.yaml"))
    if "docs" in keep:
        for name in ("README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md"):
            plan.append((os.path.join(project, "registry", name), name))
    missing, problems = set(), []
    for src, rel in plan:
        with open(src, encoding="utf-8") as f:
            text = f.read()
        if rel in SECTIONED:
            text = strip_sections(text, keep)
            problems += check_markers(rel, text, keep)
        for name, value in tokens.items():
            text = text.replace(f"@@{name}@@", value)
        missing.update(re.findall(r"@@([A-Z_]+)@@", text))
        target = os.path.join(dest, rel)
        if os.path.exists(target) and not overwrite:
            with open(target, encoding="utf-8") as f:
                same = f.read() == text
            print(("identical: " if same else "DIFFERS: ") + rel)
            continue
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote: " + rel)
    for problem in problems:
        print("MARKER PROBLEM: " + problem)
    if missing:
        print("UNRESOLVED TOKENS: " + ", ".join(sorted(missing)))
    return 1 if missing or problems else 0


if __name__ == "__main__":
    sys.exit(main())
