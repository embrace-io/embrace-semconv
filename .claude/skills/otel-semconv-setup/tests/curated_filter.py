"""Run the curated-codegen filter exactly as reference/templates.md prints it, on the layout's
fixture, and check what it claims: every attribute the registry defines or references, once each,
and nothing that only an import brings in.

Usage: curated_filter.py [--work DIR]
Extracting the snippet from the doc means an edit to it is tested, not remembered.
"""
import os
import re
import shutil
import subprocess
import sys

from _common import FIXTURES, RENDER, SKILL, read, run, work_dir

TEMPLATE = """{%- for attribute in ctx.attributes %}
{{ attribute.key }}
{%- endfor %}
"""


def doc_filter():
    """The jq after `filter: >` in the yaml block that ends with `| unique_by(.key)`."""
    text = read(os.path.join(SKILL, "reference", "templates.md"))
    for block in re.findall(r"```yaml\n(.*?)```", text, re.S):
        if "unique_by(.key)" in block and "filter: >" in block:
            body = block.split("filter: >", 1)[1]
            return "\n".join(line[2:] if line.startswith("  ") else line
                             for line in body.strip("\n").splitlines())
    raise SystemExit("templates.md: no yaml block with `filter: >` and `unique_by(.key)`")


def main():
    args = work_dir(__doc__)
    dest = os.path.join(args.work, "curated-filter")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    subprocess.run(["git", "init", "-q", dest], check=True)
    collections = "attributes,attribute-groups,events,metrics,spans,entities"
    if not run(args.work, "curated-filter-render",
               [sys.executable, RENDER, dest, "registry," + collections,
                os.path.join(FIXTURES, "tokens", "acme.json")]):
        return 1
    templates = os.path.join(dest, ".build", "filter-templates", "registry", "markdown")
    os.makedirs(templates)
    jq = "\n".join("        " + line for line in doc_filter().splitlines())
    with open(os.path.join(templates, "weaver.yaml"), "w") as f:
        f.write("templates:\n  - pattern: keys.txt.j2\n    filter: >\n"
                f"      [{{ attributes: (\n{jq}\n      ) }}]\n"
                "    application_mode: each\n    file_name: keys.txt\n")
    with open(os.path.join(templates, "keys.txt.j2"), "w") as f:
        f.write(TEMPLATE)
    out = os.path.join(dest, ".build", "filter-out")
    if not run(args.work, "curated-filter-generate",
               ["weaver", "registry", "generate", "-r", "templates_test/fixture", "--v2",
                "--templates", ".build/filter-templates", "markdown", out], cwd=dest):
        return 1
    keys = set(read(os.path.join(out, "keys.txt")).split())
    fixture = os.path.join(dest, "templates_test", "fixture")
    defined, referenced = set(), set()
    for dirpath, _, names in os.walk(fixture):
        for name in names:
            if name.endswith(".yaml") and name != "manifest.yaml":
                text = read(os.path.join(dirpath, name))
                defined.update(re.findall(r"^\s*- key: ([\w.]+)", text, re.M))
                referenced.update(re.findall(r"^\s*- ref: ([\w.]+)", text, re.M))
    expected = defined | referenced
    problems = []
    if keys - expected:
        problems.append(f"let through keys the fixture neither defines nor references "
                        f"(imports?): {sorted(keys - expected)}")
    if expected - keys:
        problems.append(f"left out keys the fixture defines or references: "
                        f"{sorted(expected - keys)}")
    for problem in problems:
        print("FILTER PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + f": curated-filter ({len(keys)} keys)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
