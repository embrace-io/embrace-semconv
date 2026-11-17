"""Check that templates.md's guidance covers every kind of value weaver allows, and fail when
weaver starts allowing one it wasn't written for.

Usage: template_types.py [--work DIR]
1. Reads weaver's materialized-registry-v2 JSON schema (what templates see) and compares the
   attribute types, enum member value types, requirement levels, example shapes and the fields
   every definition has with fixtures/template-types.json. A difference is a new or dropped kind
   of value, or a field that became optional or always present: check templates.md's "What the
   templates see" and its examples, then update the fixture.
2. Runs templates.md's enum-member mapping example on a registry with every member value type.
Needs weaver; no network.
"""
import json
import os
import re
import shutil
import subprocess
import sys

from _codegen import FIXTURES, SKILL, read, run, work_dir

EXPECTED = os.path.join(FIXTURES, "template-types.json")
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
MANIFEST = """schema_url: https://example.com/schemas/template-types/0.0.0-dev
description: Every enum member value type, for templates.md's mapping example.
stability: development
"""


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


def members_model():
    members = "".join(f"        - id: {i}\n" + (f"          value: {v}\n" if v else "")
                      for i, v, _ in MEMBERS)
    return ("file_format: definition/2\n\nattributes:\n  - key: acme.t_enum\n    type:\n"
            f"      members:\n{members}    stability: development\n    brief: An enum.\n")


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
                            " Check templates.md's guidance and examples, then update "
                            "fixtures/template-types.json")

    model = os.path.join(base, "model")
    os.makedirs(os.path.join(model, "acme"))
    with open(os.path.join(model, "manifest.yaml"), "w") as f:
        f.write(MANIFEST)
    with open(os.path.join(model, "acme", "registry.yaml"), "w") as f:
        f.write(members_model())
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
           ["weaver", "registry", "generate", "--v2", "-r", model,
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
    print(("ok" if not problems else "FAILED") + ": template-types (schema, mapping)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
