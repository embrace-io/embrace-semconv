"""Render base projects and run their make targets, as an agent following the skill would.

Usage: scenarios.py [--work DIR] [SCENARIO...]
Needs weaver at the pinned version, jq, git, GNU make and network access (the fixture fetches the
core registry; `install` downloads a weaver release). The template the `templates` scenarios use is
fixtures/templates/registry/keys/: it lists every convention the fixture resolves to.
"""
import os
import shutil
import subprocess
import sys

from _common import COLLECTIONS, FIXTURES, RENDER, TOKENS, output, read, run, work_dir

CORE_TARGETS = ("test", "generate-all", "install-weaver", "clean")
TEMPLATE_TARGETS = ("test-templates", "update-golden")
# The heading the keys template prints for each collection.
HEADINGS = {"attributes": "attributes:", "attribute-groups": "attribute_groups:",
            "events": "events:", "metrics": "metrics:", "spans": "spans:",
            "entities": "entities:"}


def render(work, name, chosen, dest=None):
    dest = dest or os.path.join(work, name, "project")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    if not run(work, f"{name}-render", [sys.executable, RENDER, dest, ",".join(chosen), TOKENS]):
        return None
    if "templates" in chosen:
        shutil.copytree(os.path.join(FIXTURES, "templates"), os.path.join(dest, "templates"))
    return dest


def make(project, *args):
    return output(["make", "-C", project, *args])


def check(problems, name, ok, message):
    if not ok:
        problems.append(f"{name}: {message}")


def core(work):
    problems = []
    project = render(work, "core", [])
    if not project:
        return ["core: render failed"]
    status, text = make(project, "help")
    check(problems, "core", status == 0 and all(t in text for t in CORE_TARGETS),
          f"make help lacks a core target:\n{text}")
    check(problems, "core", not any(t in text for t in TEMPLATE_TARGETS),
          "make help lists templates targets without the templates part")
    status, text = make(project, "-n", "install-weaver")
    check(problems, "core", status == 0 and "bash scripts/install-weaver.sh" in text
          and os.path.isfile(os.path.join(project, "scripts", "install-weaver.sh")),
          f"install-weaver doesn't run the project's scripts/install-weaver.sh:\n{text}")
    for target in ("require-weaver", "require-jq", "test", "generate-all"):
        status, text = make(project, target)
        check(problems, "core", status == 0, f"make {target} failed:\n{text}")
    status, text = make(project)
    check(problems, "core", status == 0, f"make (all) failed:\n{text}")
    check(problems, "core", not os.path.exists(os.path.join(project, ".github")),
          "core alone wrote .github/")
    return problems


def templates(work, name, collections):
    problems = []
    project = render(work, name, ["templates", *collections])
    if not project:
        return [f"{name}: render failed"]
    status, text = make(project, "help")
    check(problems, name, status == 0 and all(t in text for t in TEMPLATE_TARGETS),
          f"make help lacks a templates target:\n{text}")
    for target in ("update-golden", "test-templates"):
        status, text = make(project, target)
        check(problems, name, status == 0, f"make {target} failed:\n{text}")
    golden = os.path.join(project, "templates_test", "golden", "keys", "keys.txt")
    content = read(golden) if os.path.isfile(golden) else ""
    for collection in collections:
        check(problems, name, HEADINGS[collection] in content,
              f"the golden file has no {HEADINGS[collection]} heading")
    check(problems, name, os.path.isfile(os.path.join(project, ".github", "workflows",
                                                      "ci-validation.yaml")),
          "no CI workflow with the templates part")
    return problems


def golden_drift(work):
    """test-templates fails when the golden files no longer match, and on no targets."""
    problems = []
    project = render(work, "golden-drift", ["templates", "attributes"])
    if not project:
        return ["golden-drift: render failed"]
    status, text = make(project, "update-golden")
    check(problems, "golden-drift", status == 0, f"update-golden failed:\n{text}")
    golden = os.path.join(project, "templates_test", "golden", "keys", "keys.txt")
    with open(golden, "a", encoding="utf-8") as f:
        f.write("a line no template renders\n")
    status, text = make(project, "test-templates")
    check(problems, "golden-drift", status != 0 and "does not match" in text,
          f"test-templates passed, or failed for another reason, on a changed golden file:\n{text}")
    status, text = make(project, "test-templates", "TEMPLATE_TARGETS=")
    check(problems, "golden-drift", status != 0 and "TEMPLATE_TARGETS is empty" in text,
          f"test-templates didn't refuse an empty TEMPLATE_TARGETS:\n{text}")
    return problems


def subdirectory(work):
    """A project three levels down in a git repo: install-weaver runs the project's own script."""
    problems = []
    repo = os.path.join(work, "subdirectory", "repo")
    if os.path.exists(repo):
        shutil.rmtree(repo)
    project = render(work, "subdirectory", [], os.path.join(repo, "packages", "sdk", "semconv"))
    if not project:
        return ["subdirectory: render failed"]
    subprocess.run(["git", "init", "-q", repo], check=True)
    status, text = make(project, "-n", "install-weaver")
    check(problems, "subdirectory", status == 0 and "bash scripts/install-weaver.sh" in text,
          f"install-weaver from a subdirectory:\n{text}")
    return problems


def install(work):
    """The install script, as `make install-weaver` and the CI fallback run it: by the version
    make passes, and by versions.env when none is passed."""
    problems = []
    project = render(work, "install", [])
    if not project:
        return ["install: render failed"]
    version = [line.split("=", 1)[1] for line in read(os.path.join(project, "versions.env"))
               .splitlines() if line.startswith("WEAVER_VERSION=")][0]
    for label, env in (("passed", dict(os.environ, WEAVER_VERSION=version)),
                       ("versions.env", {k: v for k, v in os.environ.items()
                                         if k != "WEAVER_VERSION"})):
        bin_dir = os.path.join(work, "install", f"bin-{label.replace('.', '-')}")
        status, text = output(["bash", "scripts/install-weaver.sh", bin_dir], cwd=project, env=env)
        check(problems, "install", status == 0, f"install script ({label}) failed:\n{text}")
        status, text = output([os.path.join(bin_dir, "weaver"), "--version"])
        check(problems, "install", status == 0 and version.lstrip("v") in text,
              f"installed weaver ({label}) isn't {version}: {text}")
    return problems


SCENARIOS = {
    "core": core,
    "all-collections": lambda work: templates(work, "all-collections", COLLECTIONS),
    **{f"only-{c}": (lambda c: lambda work: templates(work, f"only-{c}", [c]))(c)
       for c in COLLECTIONS},
    "golden-drift": golden_drift,
    "subdirectory": subdirectory,
    "install": install,
}


def main():
    args = work_dir(__doc__)
    names = args.names or list(SCENARIOS)
    problems = []
    for name in names:
        found = SCENARIOS[name](args.work)
        print(("ok" if not found else "FAILED") + f": scenario {name}")
        problems += found
    for problem in problems:
        print("SCENARIO PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
