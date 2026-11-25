"""Run the jq filters reference/templates.md prints, exactly as it prints them, on the
template test's fixture, and check what the doc claims each selects.

Usage: filters.py [FILTER...] [--work DIR]
- key-list, namespace ("Choosing what to generate") and per-namespace ("Choosing how to split
  output"): exactly the keys the fixture defines, nothing an import brings in.
- curated ("What the templates see"): every attribute the fixture defines or references, once
  each, and nothing that only an import brings in.
- key-list-filled, namespace-filled, namespace-other: the key-list and namespace filters filled
  in as a project would (two listed keys; the `fixture` namespace; a namespace with no keys),
  without the `fixture.*` alternative: exactly the listed keys, the namespace's keys, nothing.
Extracting the snippets from the doc means an edit to them is tested, not remembered. Needs
weaver and network access (the fixture depends on the core registry).
"""
import os
import re
import shutil
import subprocess
import sys

from _common import COLLECTIONS, RENDER, SKILL, TOKENS, read, run, work_dir

TEMPLATE = """{%- for attribute in ctx.attributes %}
{{ attribute.key }}
{%- endfor %}
"""


def section(text, title):
    return text.split(f"## {title}", 1)[-1].split("\n## ", 1)[0]


def filter_body(block):
    body = block.split("filter: >", 1)[1].split("\n    application_mode", 1)[0]
    return "\n".join(line.strip() for line in body.strip("\n").splitlines())


def doc_filters():
    text = read(os.path.join(SKILL, "reference", "templates.md"))
    choosing = section(text, "Choosing what to generate")
    blocks = [b for b in re.findall(r"```yaml\n(.*?)```", choosing, re.S) if "filter: >" in b]
    if not blocks:
        raise SystemExit("templates.md: no filter block under 'Choosing what to generate'")
    key_list = filter_body(blocks[0])
    inline = re.search(r'`(map\(select\(\.key \| startswith\("<namespace>\.".*?)`',
                       choosing.replace("\n", " "), re.S)
    if not inline:
        raise SystemExit("templates.md: no namespace `map(select(.key | startswith(...)))`")
    namespace = ('[{ id: "selected", attributes: ((.registry.attributes // [])\n'
                 '| map(select(.provenance.source | not))\n| ' + inline.group(1) + ') }]')
    split = section(text, "Choosing how to split output")
    per_ns = [b for b in re.findall(r"```yaml\n(.*?)```", split, re.S) if "per namespace" in b]
    if not per_ns:
        raise SystemExit("templates.md: no one-file-per-namespace block")
    per_namespace = ("[{ attributes: ((" + filter_body(per_ns[0])
                     + ") | map(.attributes) | add // []) }]")
    seen = section(text, "What the templates see")
    curated = [b for b in re.findall(r"```yaml\n(.*?)```", seen, re.S) if "unique_by(.key)" in b]
    if not curated:
        raise SystemExit("templates.md: no yaml block with `unique_by(.key)`")
    body = curated[0].split("filter: >", 1)[1]
    curated_jq = "[{ attributes: (\n" + "\n".join(line.strip() for line in
                                                 body.strip("\n").splitlines()) + "\n) }]"
    filters = {"key-list": key_list, "namespace": namespace, "per-namespace": per_namespace,
               "curated": curated_jq}
    # The same filters as a project fills them in, without the `fixture.*` alternative, so the
    # list match (`any`) and the namespace match do the selecting themselves.
    listed = key_list.replace('["<key>", "<key>"]', '["fixture.str", "fixture.enum"]')
    listed = listed.replace('\nor ($key | startswith("fixture."))', "")
    by_namespace = namespace.replace(' or startswith("fixture.")', "")
    if listed == key_list or by_namespace == namespace or "<key>" in listed:
        raise SystemExit("templates.md: the key-list or namespace filter changed shape; update "
                         "filters.py's filled-in variants")
    filters["key-list-filled"] = listed
    filters["namespace-filled"] = by_namespace.replace("<namespace>", "fixture")
    filters["namespace-other"] = by_namespace.replace("<namespace>", "no_such_namespace")
    return filters


# What each filled-in variant must select, by name; the others select what main() says.
FILLED = {"key-list-filled": {"fixture.str", "fixture.enum"}, "namespace-other": set()}


def select_keys(work, dest, name, jq):
    templates = os.path.join(dest, ".build", f"filter-{name}", "registry", "keys")
    os.makedirs(templates)
    indented = "\n".join("      " + line for line in jq.splitlines())
    with open(os.path.join(templates, "weaver.yaml"), "w") as f:
        f.write("templates:\n  - pattern: keys.txt.j2\n    filter: >\n"
                f"{indented}\n    application_mode: each\n    file_name: keys.txt\n")
    with open(os.path.join(templates, "keys.txt.j2"), "w") as f:
        f.write(TEMPLATE)
    out = os.path.join(dest, ".build", f"filter-{name}-out")
    if not run(work, f"filter-{name}",
               ["weaver", "registry", "generate", "-r", "templates_test/fixture", "--v2",
                "--templates", f".build/filter-{name}", "keys", out], cwd=dest):
        return None
    return set(read(os.path.join(out, "keys.txt")).split())


def fixture_keys(dest):
    defined, referenced = set(), set()
    for dirpath, _, names in os.walk(os.path.join(dest, "templates_test", "fixture")):
        for name in names:
            if name.endswith(".yaml") and name != "manifest.yaml":
                text = read(os.path.join(dirpath, name))
                defined.update(re.findall(r"^\s*- key: ([\w.]+)", text, re.M))
                referenced.update(re.findall(r"^\s*- ref: ([\w.]+)", text, re.M))
    return defined, referenced


def main():
    args = work_dir(__doc__)
    filters = doc_filters()
    dest = os.path.join(args.work, "filters")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    subprocess.run(["git", "init", "-q", dest], check=True)
    if not run(args.work, "filters-render",
               [sys.executable, RENDER, dest, ",".join(COLLECTIONS), TOKENS]):
        return 1
    defined, referenced = fixture_keys(dest)
    problems = []
    for name in args.names or list(filters):
        keys = select_keys(args.work, dest, name, filters[name])
        expected = (FILLED[name] if name in FILLED
                    else defined | referenced if name == "curated" else defined)
        if keys is None:
            problems.append(f"{name}: weaver failed on the filter (see its log)")
        elif keys != expected:
            problems.append(f"{name}: selected {sorted(keys)}; expected {sorted(expected)} "
                            f"(extra {sorted(keys - expected)}, missing {sorted(expected - keys)})")
        else:
            print(f"ok: filter {name} ({len(keys)} keys)")
    for problem in problems:
        print("FILTER PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + ": filters")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
