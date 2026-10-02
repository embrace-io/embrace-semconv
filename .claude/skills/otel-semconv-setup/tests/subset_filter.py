"""Run the key-selection filters exactly as reference/templates.md prints them ("Choosing what to
generate": the key-list block and the namespace variant; "Choosing how to split output": the
one-file-per-namespace block), on the layout's fixture, and check what they claim: they select
exactly the keys the fixture defines, and nothing an import brings in.

Usage: subset_filter.py [--work DIR]
Extracting the snippets from the doc means an edit to them is tested, not remembered.
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


def doc_filters():
    """(the key-list block's jq, the namespace variant's `map(...)`) from templates.md."""
    text = read(os.path.join(SKILL, "reference", "templates.md"))
    section = text.split("## Choosing what to generate", 1)[-1].split("\n## ", 1)[0]
    blocks = [b for b in re.findall(r"```yaml\n(.*?)```", section, re.S) if "filter: >" in b]
    if not blocks:
        raise SystemExit("templates.md: no filter block under 'Choosing what to generate'")
    body = blocks[0].split("filter: >", 1)[1].split("\n    application_mode", 1)[0]
    key_list = "\n".join(line.strip() for line in body.strip("\n").splitlines())
    inline = re.search(r'`(map\(select\(\.key \| startswith\("<namespace>\.".*?)`',
                       section.replace("\n", " "), re.S)
    if not inline:
        raise SystemExit("templates.md: no namespace `map(select(.key | startswith(...)))`")
    namespace = ('[{ id: "selected", attributes: ((.registry.attributes // [])\n'
                 '| map(select(.provenance.source | not))\n| ' + inline.group(1) + ') }]')
    # "Choosing how to split output": the one-file-per-namespace block, its files joined again.
    split = text.split("## Choosing how to split output", 1)[-1].split("\n## ", 1)[0]
    per_ns = [b for b in re.findall(r"```yaml\n(.*?)```", split, re.S) if "per namespace" in b]
    if not per_ns:
        raise SystemExit("templates.md: no one-file-per-namespace block")
    body = per_ns[0].split("filter: >", 1)[1].split("\n    application_mode", 1)[0]
    per_namespace = ("[{ attributes: ((" + "\n".join(
        line.strip() for line in body.strip("\n").splitlines())
        + ") | map(.attributes) | add // []) }]")
    return key_list, namespace, per_namespace


def select_keys(work, dest, name, jq):
    templates = os.path.join(dest, ".build", f"subset-{name}", "registry", "markdown")
    os.makedirs(templates)
    indented = "\n".join("      " + line for line in jq.splitlines())
    with open(os.path.join(templates, "weaver.yaml"), "w") as f:
        f.write("templates:\n  - pattern: keys.txt.j2\n    filter: >\n"
                f"{indented}\n    application_mode: each\n    file_name: keys.txt\n")
    with open(os.path.join(templates, "keys.txt.j2"), "w") as f:
        f.write(TEMPLATE)
    out = os.path.join(dest, ".build", f"subset-{name}-out")
    if not run(work, f"subset-filter-{name}",
               ["weaver", "registry", "generate", "-r", "templates_test/fixture", "--v2",
                "--templates", f".build/subset-{name}", "markdown", out], cwd=dest):
        return None
    return set(read(os.path.join(out, "keys.txt")).split())


def main():
    args = work_dir(__doc__)
    dest = os.path.join(args.work, "subset-filter")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    subprocess.run(["git", "init", "-q", dest], check=True)
    if not run(args.work, "subset-filter-render",
               [sys.executable, RENDER, dest, "registry,attributes,attribute-groups",
                os.path.join(FIXTURES, "tokens", "acme.json")]):
        return 1
    fixture = os.path.join(dest, "templates_test", "fixture")
    defined = set()
    for dirpath, _, names in os.walk(fixture):
        for name in names:
            if name.endswith(".yaml") and name != "manifest.yaml":
                defined.update(re.findall(r"^\s*- key: ([\w.]+)",
                                          read(os.path.join(dirpath, name)), re.M))
    problems = []
    for name, jq in zip(("key-list", "namespace", "per-namespace"), doc_filters()):
        keys = select_keys(args.work, dest, name, jq)
        if keys is None:
            problems.append(f"{name}: weaver failed on the filter (see its log)")
        elif keys != defined:
            problems.append(f"{name}: selected {sorted(keys)}, expected the fixture's own "
                            f"{sorted(defined)}")
    for problem in problems:
        print("FILTER PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + f": subset-filter ({len(defined)} fixture keys)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
