"""Build codegen projects on the base layout, add what an agent would supply (Python templates,
platform recipes), and run their targets.

Usage: codegen.py [PROJECT...] [--work DIR]
Needs weaver at the pinned version, jq, git, GNU make, python3 and network access.
- core: generates straight from the core registry, committed code, every target.
- stubs: the part as copied: validate-generated and package-generated fail until implemented.
- broken: a template emitting code that can't compile makes validate-generated fail, as the
  skill's Verify step says.
"""
import os
import re
import shutil
import sys

from _codegen import FIXTURES, output, read, render_project, run, work_dir

VALIDATE = """validate-generated: generate
\tpython3 -m compileall -q $(GENERATED_DIR)
\tpython3 -c 'from semconv_attributes import session_attributes; assert session_attributes.SESSION_ID == "session.id"; print("generated constants OK")'
"""
PACKAGE = """package-generated: validate-generated
\t@mkdir -p .build/package-generated
\tpython3 -m zipfile -c .build/package-generated/semconv_attributes.zip $(GENERATED_DIR)
"""
BASE_PARTS = ["templates", "no-drift", "attributes"]


def replace_recipe(text, target, recipe):
    """Replace the recipe of TARGET (its rule line through the next blank line)."""
    pattern = re.compile(r"^" + re.escape(target) + r":.*?\n(?=\n)", re.S | re.M)
    new, count = pattern.subn(lambda _: recipe, text, count=1)
    if count != 1:
        raise SystemExit(f"no recipe for {target}")
    return new


def build(work, name, implement=True):
    dest = os.path.join(work, "codegen", name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    if not render_project(work, f"codegen-{name}", dest, BASE_PARTS, ["codegen"]):
        return None
    shutil.copytree(os.path.join(FIXTURES, "codegen", "python"),
                    os.path.join(dest, "templates", "registry", "python"))
    if implement:
        makefile = os.path.join(dest, "Makefile")
        text = replace_recipe(read(makefile), "validate-generated", VALIDATE)
        with open(makefile, "w") as f:
            f.write(replace_recipe(text, "package-generated", PACKAGE))
    return dest


def core(work):
    problems = []
    dest = build(work, "core")
    if not dest:
        return ["core: render failed"]
    status, text = output(["make", "-C", dest, "help"])
    if not all(t in text for t in ("generate ", "validate-generated", "package-generated")):
        problems.append(f"core: make help lacks a codegen target:\n{text}")
    workflow = read(os.path.join(dest, ".github", "workflows", "ci-validation.yaml"))
    if "  validate-generated:" not in workflow or "- validate-generated # codegen" not in workflow:
        problems.append("core: the CI workflow lacks the validate-generated job or its needs entry")
    for target in ("update-golden", "generate", "test", "package-generated", ""):
        if not run(work, f"codegen-core-{target or 'all'}", ["make", target] if target else ["make"],
                   cwd=dest):
            problems.append(f"core: make {target or '(all)'} failed")
    golden = os.path.join(dest, "templates_test", "golden", "python")
    if not any(name.endswith(".py") for name in os.listdir(golden)):
        problems.append("core: no Python golden files")
    return problems


def stubs(work):
    problems = []
    dest = build(work, "stubs", implement=False)
    if not dest:
        return ["stubs: render failed"]
    for target in ("validate-generated", "package-generated"):
        status, text = output(["make", "-C", dest, target])
        if status == 0 or "is not implemented for this project yet" not in text:
            problems.append(f"stubs: make {target} didn't fail as a stub:\n{text}")
    return problems


def broken(work):
    dest = build(work, "broken")
    if not dest:
        return ["broken: render failed"]
    template = os.path.join(dest, "templates", "registry", "python", "attributes.py.j2")
    text = read(template).replace("{{ attribute.key | screaming_snake_case }} =",
                                  "{{ attribute.key | screaming_snake_case }}-broken =")
    with open(template, "w") as f:
        f.write(text)
    status, out = output(["make", "-C", dest, "validate-generated"])
    return [] if status != 0 else [f"broken: validate-generated passed on code that can't compile"]


PROJECTS = {"core": core, "stubs": stubs, "broken": broken}


def main():
    args = work_dir(__doc__)
    problems = []
    for name in args.names or list(PROJECTS):
        found = PROJECTS[name](args.work)
        print(("ok" if not found else "FAILED") + f": codegen {name}")
        problems += found
    for problem in problems:
        print("CODEGEN PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
