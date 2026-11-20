"""Add another skill's part to a project render.py made, following reference/layout.md "Adding a
part" mechanically, as a test double for an agent. Skills that build on this one test with it.

Usage: add_part.py DEST ASSETS PARTS KEEP TOKENS.json
ASSETS is the other skill's assets/ directory. PARTS lists the directories under it whose files are
copied to the project (comma-separated, may be empty). KEEP lists the sections to keep in its
fragments: its part, its chosen sections and collections, `private`. The fragments are ASSETS/project/Makefile (a
Makefile section), ASSETS/project/ci-validation.yaml (CI jobs, with the aggregate job's new `needs`
entries in its header) and ASSETS/project/versions.env (pins), each optional. A project with no CI
workflow yet gets the base's, with only the aggregate job, before the jobs are added.
"""
import json
import os
import re
import sys

from _common import ASSETS as BASE_ASSETS
from render import check_markers, strip_sections

# The order of the Makefile's top-level sections (layout.md, "Adding a part").
ORDER = ["project", "common", "templates", "registry", "docs", "release", "codegen"]
GATE = "  # Aggregate gate for branch protection"
SECTION = re.compile(r"^# ==== (?!end )([a-z-]+)")
ALL_SECTIONS = {"project", "common", "templates", "core", "private", "policies", "public-groups",
                "attribute-groups", "events", "metrics", "spans", "entities", "registry", "docs",
                "release", "codegen", "renovate"}


def fill(text, tokens, missing):
    for name, value in tokens.items():
        text = text.replace(f"@@{name}@@", value)
    missing.update(re.findall(r"@@([A-Z_]+)@@", text))
    return text


def top_level_sections(lines):
    """(index, name) of each top-level section start line in a Makefile."""
    found, depth = [], 0
    for index, line in enumerate(lines):
        start = SECTION.match(line)
        if start:
            if depth == 0:
                found.append((index, start.group(1)))
            depth += 1
        elif line.startswith("# ==== end "):
            depth -= 1
    return found


def add_makefile_section(path, fragment, keep, tokens, missing):
    name = SECTION.match(fragment).group(1)
    lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
    later = [index for index, existing in top_level_sections(lines)
             if ORDER.index(existing) > ORDER.index(name)]
    if later:
        lines[later[0]:later[0]] = [fragment, "\n"]
    else:
        lines += ["\n", fragment]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)


def add_ci_jobs(path, fragment, keep, tokens, missing):
    """Add the fragment's jobs above the aggregate job, and the `needs` entries its header lists
    whose tags are all kept. Without a workflow, start from the base's, without its templates job
    (a project with the templates part already has the workflow)."""
    if not os.path.exists(path):
        base = open(os.path.join(BASE_ASSETS, "project", "ci-validation.yaml"),
                    encoding="utf-8").read()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(fill(strip_sections(base, {"project", "common"} | keep), tokens, missing))
    header, jobs = re.match(r"((?:#[^\n]*\n|\n)*)(.*)", fragment, re.S).groups()
    needs = [entry for entry, tags in re.findall(r"^#\s+(- [a-z-]+ # ([a-z -]+))$", header, re.M)
             if set(tags.split()) <= keep]
    text = open(path, encoding="utf-8").read()
    if GATE not in text:
        raise SystemExit(f"{path} has no aggregate job to add jobs above")
    text = text.replace(GATE, jobs.strip("\n") + "\n\n" + GATE, 1)
    entries = list(re.finditer(r"^      - [a-z-]+ # [a-z -]+\n", text, re.M))
    anchor = entries[-1].end() if entries else re.search(r"^    needs:\n", text, re.M).end()
    text = text[:anchor] + "".join(f"      {n}\n" for n in needs) + text[anchor:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def add_pins(path, fragment, keep, tokens, missing):
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + fragment)


def main():
    dest, assets, parts, keep, tokens_path = sys.argv[1:6]
    parts = [p for p in parts.split(",") if p]
    keep = {k for k in keep.split(",") if k}
    with open(tokens_path) as f:
        tokens = json.load(f)
    missing, problems = set(), []
    for part in parts:
        base = os.path.join(assets, part)
        for dirpath, _, names in os.walk(base):
            for name in sorted(names):
                src = os.path.join(dirpath, name)
                target = os.path.join(dest, os.path.relpath(src, base))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                # A copied file can have sections too (a workflow's `private` ones): keep only
                # the chosen, as the part's fragments do.
                text = strip_sections(open(src, encoding="utf-8").read(),
                                      keep | {"project", "common", "core", "templates"})
                with open(target, "w", encoding="utf-8") as f:
                    f.write(fill(text, tokens, missing))
                print("wrote: " + os.path.relpath(target, dest))
    fragments = {
        "Makefile": (os.path.join(dest, "Makefile"), add_makefile_section),
        "ci-validation.yaml": (os.path.join(dest, ".github", "workflows", "ci-validation.yaml"),
                               add_ci_jobs),
        "versions.env": (os.path.join(dest, "versions.env"), add_pins),
    }
    for name, (target, add) in fragments.items():
        src = os.path.join(assets, "project", name)
        if not os.path.exists(src):
            continue
        text = fill(strip_sections(open(src, encoding="utf-8").read(), keep), tokens, missing)
        add(target, text, keep, tokens, missing)
        problems += check_markers(name, open(target, encoding="utf-8").read(), ALL_SECTIONS)
        print(f"added: {name}")
    for problem in problems:
        print("MARKER PROBLEM: " + problem)
    if missing:
        print("UNRESOLVED TOKENS: " + ", ".join(sorted(missing)))
    return 1 if missing or problems else 0


if __name__ == "__main__":
    sys.exit(main())
