"""Render the minimal Jinja examples reference/templates.md prints, exactly as it prints them, on
the template test's fixture, and check what the doc claims of them: each file ends with a
newline, marks the fixture's deprecated attribute (`fixture.old_str`) deprecated, and is named
from the whole group ID or namespace; the Python one compiles.

Usage: examples.py [--work DIR]
The Kotlin example renders one file per public attribute group, the Python and TypeScript ones
one file per namespace with the doc's per-namespace filter. Needs weaver and network access (the
fixture depends on the core registry). Extracting the examples from the doc means an edit to them
is tested, not remembered.
"""
import os
import re
import shutil
import subprocess
import sys

from _common import SKILL, TOKENS, read, render_project, run, work_dir

PER_GROUP = """templates:
  - pattern: attributes.kt.j2
    filter: '(.registry.attribute_groups // []) | map(select(.provenance.source | not))'
    application_mode: each
    file_name: "{{ ctx.id | replace('registry.', '') | replace('.', '_') | camel_case }}Attributes.kt"
"""
# The deprecation marker each language's example must give fixture.old_str.
MARKERS = {"kt": "@Deprecated(", "py": "Deprecated:", "ts": "@deprecated"}


def doc_examples():
    """{extension: template} for the examples under "Minimal examples", and the per-namespace
    filter's weaver.yaml from "Choosing how to split output"."""
    text = read(os.path.join(SKILL, "reference", "templates.md"))
    minimal = text.split("Minimal examples", 1)[1].split("\n## ", 1)[0]
    examples = {}
    for block in re.findall(r"```jinja\n(.*?)```", minimal, re.S):
        name = re.match(r"\{# attributes\.(\w+)\.j2", block)
        if not name:
            raise SystemExit(f"templates.md: an example with no attributes.<ext>.j2 header:\n{block}")
        examples[name.group(1)] = block
    if set(examples) != set(MARKERS):
        raise SystemExit(f"templates.md: examples for {sorted(examples)}, expected {sorted(MARKERS)}")
    split = text.split("## Choosing how to split output", 1)[1].split("\n## ", 1)[0]
    per_ns = [b for b in re.findall(r"```yaml\n(.*?)```", split, re.S) if "per namespace" in b]
    if not per_ns:
        raise SystemExit("templates.md: no one-file-per-namespace block")
    return examples, per_ns[0]


def render(work, dest, ext, template, weaver_yaml):
    """Render TEMPLATE as target ext-example; returns {file name: text}, or None on failure."""
    target = os.path.join(dest, ".build", "examples", "registry", f"{ext}-example")
    os.makedirs(target)
    with open(os.path.join(target, f"attributes.{ext}.j2"), "w", encoding="utf-8") as f:
        f.write(template)
    with open(os.path.join(target, "weaver.yaml"), "w", encoding="utf-8") as f:
        f.write(weaver_yaml)
    out = os.path.join(dest, ".build", f"examples-{ext}-out")
    if not run(work, f"example-{ext}", ["weaver", "registry", "generate", "-r",
                                       "templates_test/fixture", "--v2", "--templates",
                                       ".build/examples", f"{ext}-example", out], cwd=dest):
        return None
    return {name: read(os.path.join(out, name)) for name in sorted(os.listdir(out))}


def check(ext, files):
    problems = []
    if not files:
        return [f"{ext}: rendered no files"]
    for name, text in files.items():
        if not text.endswith("\n") or text.endswith("\n\n"):
            problems.append(f"{ext}: {name} doesn't end with exactly one newline")
    # fixture.old_str is the fixture's only deprecated attribute, so the file holding it must
    # carry the marker.
    marked = [text for text in files.values() if "fixture.old_str" in text]
    if not marked or not all(MARKERS[ext] in text for text in marked):
        problems.append(f"{ext}: fixture.old_str isn't marked {MARKERS[ext]!r}")
    if ext == "kt":
        # templates.md's escaping rule: KDoc needs both comment terminators escaped, and the
        # fixture's briefs contain neither, so the example's template is checked instead.
        template = doc_examples()[0]["kt"]
        for terminator in ("'*/'", "'/*'"):
            if f"replace({terminator}" not in template:
                problems.append(f"kt: the example doesn't escape {terminator} in KDoc")
        if not any("object FixtureDefinedAttributes" in text for text in files.values()):
            problems.append("kt: the object isn't named from the whole group ID "
                            f"(files: {sorted(files)})")
    if ext == "py":
        for name, text in files.items():
            try:
                compile(text, name, "exec")
            except SyntaxError as error:
                problems.append(f"py: {name} doesn't compile: {error}")
    return problems


def main():
    args = work_dir(__doc__)
    examples, per_namespace = doc_examples()
    dest = os.path.join(args.work, "examples")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    subprocess.run(["git", "init", "-q", dest], check=True)
    if not render_project(args.work, "examples", dest, ["attributes"], TOKENS):
        return 1
    problems = []
    for ext, template in sorted(examples.items()):
        weaver_yaml = PER_GROUP if ext == "kt" else per_namespace.replace("<ext>", ext)
        files = render(args.work, dest, ext, template, weaver_yaml)
        found = check(ext, files) if files is not None else [f"{ext}: weaver failed (see its log)"]
        print(("ok" if not found else "FAILED") + f": example {ext} ({len(files or {})} files)")
        problems += found
    for problem in problems:
        print("EXAMPLE PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + ": examples")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
