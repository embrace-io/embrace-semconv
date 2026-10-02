"""Check that the templates handle every kind of value weaver allows, and fail when weaver starts
allowing one they weren't written for.

Usage: template_types.py [--work DIR]
1. Reads weaver's materialized-registry-v2 JSON schema (what templates see) and compares the
   attribute types, enum member value types, requirement levels, example shapes and the fields
   every definition has with fixtures/template-types.json. A difference is a new or dropped kind
   of value, or a field that became optional or always present: check every template that
   branches on it or uses it directly, and templates.md's guidance, then update the fixture.
2. Renders a registry using every listed attribute type, member value type and requirement level
   through the layout's docs templates; none may fall through to the raw fallback.
3. Runs templates.md's enum-member mapping example on every member value type.
Needs weaver and network access (the docs project depends on the core registry).
"""
import json
import os
import re
import shutil
import subprocess
import sys

from _common import FIXTURES, RENDER, SKILL, read, run, work_dir

EXPECTED = os.path.join(FIXTURES, "template-types.json")
FEATURES = "registry,docs,attributes,attribute-groups,events,metrics,spans,entities"
# Member values and the Kotlin each must become with templates.md's example.
MEMBERS = [
    ("str", '"x"', 'const val STR: String = "x"'),
    ("quoted", '"say \\"hi\\" $HOME \\\\ end"',
     'const val QUOTED: String = "say \\"hi\\" \\$HOME \\\\ end"'),
    ("int", "1", "const val INT: Long = 1L"),
    ("neg", "-1", "const val NEG: Long = -1L"),
    ("dbl", "1.5", "const val DBL: Double = 1.5"),
    ("whole_dbl", "2.0", "const val WHOLE_DBL: Double = 2.0"),
    ("bool", "true", "const val BOOL: Boolean = true"),
    ("omitted", None, 'const val OMITTED: String = "omitted"'),
]
# The schema's definitions of what templates iterate, whose required fields templates.md's "What
# the templates see" lists as always present.
KINDS = ["Attribute", "AttributeGroup", "AttributeGroupAttribute", "EnumEntriesSpec", "Event",
         "EventAttribute", "Metric", "MetricAttribute", "Span", "SpanAttribute", "SpanName",
         "Entity", "EntityAttribute"]


def schema_kinds(schema):
    defs = schema["$defs"]
    consts = lambda name: [v["const"] for v in defs[name]["oneOf"]]  # noqa: E731
    types = consts("PrimitiveOrArrayTypeSpec") + consts("TemplateTypeSpec")
    if any(v.get("properties", {}).get("members") for v in defs["AttributeType"]["anyOf"]):
        types.append("enum")
    levels = consts("BasicRequirementLevelSpec")
    levels += [key for v in defs["RequirementLevel"]["anyOf"] for key in v.get("required", [])]

    def shape(spec):
        if "$ref" in spec:
            return spec["$ref"].split("/")[-1]
        if spec.get("type") == "array":
            return "array of " + shape(spec["items"])
        return spec["type"]
    return {
        "attribute_types": sorted(set(types)),
        "enum_member_value_types": sorted(v["type"] for v in defs["ValueSpec"]["anyOf"]),
        "requirement_levels": sorted(set(levels)),
        "signal_requirement_levels": sorted(consts("SignalRequirementLevel")),
        "example_shapes": sorted(shape(v) for v in defs["Examples"]["anyOf"]),
        "required_fields": sorted(f"{kind}.{field}" for kind in KINDS
                                  for field in defs[kind].get("required", [])),
    }


def model_text(expected):
    def key(name):
        return "acme.t_" + re.sub(r"[^a-z0-9]+", "_", name.replace("[]", "_array")).strip("_")
    attributes, refs = [], []
    for name in expected["attribute_types"]:
        if name == "enum":
            members = "".join(f"        - id: {i}\n" + (f"          value: {v}\n" if v else "")
                              for i, v, _ in MEMBERS)
            type_block = f"    type:\n      members:\n{members}"
        else:
            type_block = f"    type: {name}\n"
        attributes.append(f"  - key: {key(name)}\n{type_block}    stability: development\n"
                          f"    brief: A {name} attribute.\n")
        refs.append(f"      - ref: {key(name)}\n")
    levels = {"required": "required", "recommended": "recommended", "opt_in": "opt_in",
              "conditionally_required": "\n          conditionally_required: When it applies."}
    level_refs = "".join(
        f"      - ref: {key(name)}\n        requirement_level: {levels[level]}\n"
        for name, level in zip(expected["attribute_types"], expected["requirement_levels"]))
    events = "".join(f"  - name: acme.event_{level}\n    requirement_level: {level}\n"
                     f"    stability: development\n    brief: An event.\n"
                     f"    attributes:\n{level_refs}"
                     for level in expected["signal_requirement_levels"])
    return ("file_format: definition/2\n\nattributes:\n" + "".join(attributes)
            + "\nattribute_groups:\n  - id: registry.acme\n    visibility: public\n"
            "    stability: development\n    brief: Every type.\n    attributes:\n"
            + "".join(refs) + "\nevents:\n" + events
            + "\nmetrics:\n  - name: acme.metric\n    instrument: counter\n    unit: \"1\"\n"
            "    stability: development\n    brief: A metric.\n    attributes:\n" + level_refs
            + "\nspans:\n  - type: acme.span\n    kind: client\n    name:\n"
            "      note: The operation.\n    stability: development\n    brief: A span.\n"
            "    attributes:\n" + level_refs
            + "\nentities:\n  - type: acme.entity\n    stability: development\n"
            f"    brief: An entity.\n    identity:\n      - ref: {key('string')}\n")


def doc_snippet():
    text = read(os.path.join(SKILL, "reference", "templates.md"))
    for block in re.findall(r"```jinja\n(.*?)```", text, re.S):
        if "member.value is integer" in block:
            return "\n".join(line[2:] if line.startswith("  ") else line
                             for line in block.splitlines())
    raise SystemExit("templates.md: no jinja block mapping member.value")


def main():
    args = work_dir(__doc__)
    base = os.path.join(args.work, "template-types")
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)
    problems = []

    schema_file = os.path.join(base, "schema.json")
    subprocess.run(["weaver", "registry", "json-schema", "-j", "materialized-registry-v2",
                    "-o", schema_file], check=True, capture_output=True)
    with open(schema_file) as f:
        found = schema_kinds(json.load(f))
    with open(EXPECTED) as f:
        expected = json.load(f)
    for field, values in found.items():
        added = sorted(set(values) - set(expected[field]))
        dropped = sorted(set(expected[field]) - set(values))
        if added or dropped:
            problems.append(f"weaver's schema changed {field}: added {added}, dropped {dropped}."
                            " Check the templates that branch on it and templates.md, then "
                            "update fixtures/template-types.json")

    project = os.path.join(base, "docs")
    if not run(args.work, "template-types-render",
               [sys.executable, RENDER, project, FEATURES,
                os.path.join(FIXTURES, "tokens", "acme.json")]):
        return 1
    subprocess.run(["git", "init", "-q", project], check=True)
    os.makedirs(os.path.join(project, "model", "acme"))
    with open(os.path.join(project, "model", "acme", "registry.yaml"), "w") as f:
        f.write(model_text(expected))
    if run(args.work, "template-types-generate-docs", ["make", "-C", project, "generate-docs"]):
        docs = "".join(read(os.path.join(d, n)) for d, _, ns in
                       os.walk(os.path.join(project, "docs")) for n in ns)
        for name in expected["attribute_types"]:
            if name != "enum" and f"`{name}`" not in docs:
                problems.append(f"the docs don't show the attribute type `{name}`")
        if "{" in docs and "members" in docs:
            problems.append("an attribute type fell through to the docs templates' raw fallback")
    else:
        problems.append("the docs templates failed on a registry using every kind of value "
                        "(see logs/template-types-generate-docs.log)")

    snippet_dir = os.path.join(base, "snippet", "registry", "kotlin")
    os.makedirs(snippet_dir)
    with open(os.path.join(snippet_dir, "weaver.yaml"), "w") as f:
        f.write("templates:\n  - pattern: members.kt.j2\n    filter: "
                "\"[(.registry.attributes // [])[] | .type.members? // [] | .[]]\"\n"
                "    application_mode: single\n    file_name: members.kt\n")
    with open(os.path.join(snippet_dir, "members.kt.j2"), "w") as f:
        f.write("{%- for member in ctx %}" + doc_snippet() + "\n{%- endfor %}\n")
    out = os.path.join(base, "snippet", "out")
    if run(args.work, "template-types-snippet",
           ["weaver", "registry", "generate", "--v2", "-r", os.path.join(project, "model"),
            "--templates", os.path.join(base, "snippet"), "kotlin", out]):
        kotlin = read(os.path.join(out, "members.kt"))
        for member_id, _, line in MEMBERS:
            if line not in kotlin:
                problems.append(f"templates.md's mapping turned {member_id} into something other "
                                f"than: {line}")
        if "WARNING" in kotlin:
            problems.append("templates.md's mapping hit its fallback for a known value type")
    else:
        problems.append("templates.md's enum mapping example failed to render")

    for problem in problems:
        print("TYPES PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + ": template-types (schema, docs, mapping)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
