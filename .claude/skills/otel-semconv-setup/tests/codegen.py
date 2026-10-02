"""Build the two codegen projects from the current layout, add what an agent would supply (Python
templates, a curated model, platform recipes), and run their targets.

Usage: codegen.py [core] [curated] [--work DIR]
`core` generates straight from the core registry; `curated` defines a registry of its own that
imports a federated registry's public group and references a core attribute.
"""
import os
import re
import shutil
import subprocess
import sys

from _common import FIXTURES, RENDER, run, work_dir

RECIPES = {
    "core": """validate-generated: generate
\tpython3 -m compileall -q $(GENERATED_DIR)
\tpython3 -c 'from semconv_attributes import session_attributes; assert session_attributes.SESSION_ID == "session.id"; print("generated constants OK")'
""",
    "curated": """validate-generated: generate
\tpython3 -m compileall -q $(GENERATED_DIR)
\tpython3 -c 'from semconv_attributes import emb_attributes, session_attributes; assert emb_attributes.EMB_USER_SESSION_ID == "emb.user_session_id"; assert session_attributes.SESSION_ID == "session.id"; print("generated constants OK")'
""",
}
PACKAGE = """package-generated: validate-generated
\t@mkdir -p .build/package-generated
\tpython3 -m zipfile -c .build/package-generated/semconv_attributes.zip $(GENERATED_DIR)
"""
# name -> (features and collections, tokens, fixtures/codegen/ directory with its Python templates)
PROJECTS = {
    "core": ("codegen,attributes", "core-codegen.json", "python"),
    "curated": ("registry,codegen,attribute-groups", "curated-codegen.json", "curated-python"),
}
# A public federated registry for the curated project to import (test data only).
EXTRA_DEPENDENCY = """  - schema_url: https://embrace.io/schemas/embrace/0.3.0
    registry_path: https://github.com/embrace-io/embrace-semconv@v0.3.0[model]
"""


def replace_recipe(text, target, recipe):
    """Replace the recipe of TARGET (its rule line through the next blank line)."""
    pattern = re.compile(r"^" + re.escape(target) + r":.*?\n(?=\n)", re.S | re.M)
    new, count = pattern.subn(lambda _: recipe, text, count=1)
    if count != 1:
        raise SystemExit(f"no recipe for {target}")
    return new


def build(work, name):
    chosen, tokens, templates = PROJECTS[name]
    dest = os.path.join(work, "codegen", name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    subprocess.run(["git", "init", "-q", dest], check=True)
    if not run(work, f"codegen-{name}-render",
               [sys.executable, RENDER, dest, chosen, os.path.join(FIXTURES, "tokens", tokens)]):
        return False
    shutil.copytree(os.path.join(FIXTURES, "codegen", templates),
                    os.path.join(dest, "templates", "registry", "python"))
    makefile = os.path.join(dest, "Makefile")
    with open(makefile) as f:
        text = f.read()
    if name == "core":
        # A consumer gets no registry and none of the registry's own validations.
        extra = [path for path in ("model", "validations_test") if os.path.exists(os.path.join(dest, path))]
        extra += [name for name in ("test-validations:", "validate-registry:", "REPO_URL :=")
                  if re.search(r"^" + re.escape(name), text, re.M)]
        if extra:
            print("FAILED: codegen-core-consumer-only (has " + ", ".join(extra) + ")")
            return False
        print("ok: codegen-core-consumer-only")
    text = replace_recipe(text, "validate-generated", RECIPES[name])
    text = replace_recipe(text, "package-generated", PACKAGE)
    with open(makefile, "w") as f:
        f.write(text)
    if name == "curated":
        os.makedirs(os.path.join(dest, "model", "sdk"))
        shutil.copyfile(os.path.join(FIXTURES, "codegen", "curated-model", "registry.yaml"),
                        os.path.join(dest, "model", "sdk", "registry.yaml"))
        with open(os.path.join(dest, "model", "manifest.yaml"), "a") as f:
            f.write(EXTRA_DEPENDENCY)
    targets = ["update-golden", "generate", "test", "package-generated"]
    if name == "curated":
        targets[1:1] = ["validate-registry"]
    return all(run(work, f"codegen-{name}-{target}", ["make", target], cwd=dest)
               for target in targets)


def main():
    args = work_dir(__doc__)
    return 0 if all(build(args.work, name) for name in args.names or list(PROJECTS)) else 1


if __name__ == "__main__":
    sys.exit(main())
