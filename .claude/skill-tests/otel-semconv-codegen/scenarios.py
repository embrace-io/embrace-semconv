"""Render projects and run the make targets of their template test, as an agent following the
skill would. codegen.py runs the codegen targets.

Usage: scenarios.py [--work DIR] [SCENARIO...]
Needs weaver at the pinned version, jq, git, GNU make and network access (the fixture fetches the
core registry; `install` downloads a weaver release). The template the scenarios test is
fixtures/templates/registry/keys/: it lists every convention the fixture resolves to.
"""
import json
import os
import re
import shutil
import subprocess
import sys

from _common import COLLECTIONS, FIXTURES, KEYS_TOKENS, RENDER, output, read, run, work_dir

CORE_TARGETS = ("test", "generate-all", "install-weaver", "clean")
TEMPLATE_TARGETS = ("test-templates", "update-golden")
CODEGEN_TARGETS = ("generate ", "validate-generated", "package-generated")
# An older weaver release a project may keep pinned, which the fixture must still load on.
OLDER_WEAVER = "v0.26.1"
# The heading the keys template prints for each collection.
HEADINGS = {"attributes": "attributes:", "attribute-groups": "attribute_groups:",
            "events": "events:", "metrics": "metrics:", "spans": "spans:",
            "entities": "entities:"}


def render(work, name, chosen, dest=None, tokens=KEYS_TOKENS):
    dest = dest or os.path.join(work, name, "project")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    if not run(work, f"{name}-render", [sys.executable, RENDER, dest, ",".join(chosen), tokens]):
        return None
    shutil.copytree(os.path.join(FIXTURES, "templates"), os.path.join(dest, "templates"))
    return dest


def make(project, *args):
    return output(["make", "-C", project, *args])


def check(problems, name, ok, message):
    if not ok:
        problems.append(f"{name}: {message}")


def targets(work):
    """Every target the Verify step lists is in `make help`, install-weaver runs the project's
    own script, and the tool checks pass."""
    problems = []
    project = render(work, "targets", ["attributes"])
    if not project:
        return ["targets: render failed"]
    status, text = make(project, "help")
    check(problems, "targets", status == 0 and all(
        t in text for t in CORE_TARGETS + TEMPLATE_TARGETS + CODEGEN_TARGETS),
          f"make help lacks a target:\n{text}")
    status, text = make(project, "-n", "install-weaver")
    check(problems, "targets", status == 0 and "bash scripts/install-weaver.sh" in text
          and os.path.isfile(os.path.join(project, "scripts", "install-weaver.sh")),
          f"install-weaver doesn't run the project's scripts/install-weaver.sh:\n{text}")
    for target in ("require-weaver", "require-jq"):
        status, text = make(project, target)
        check(problems, "targets", status == 0, f"make {target} failed:\n{text}")
    return problems


def templates(work, name, collections):
    problems = []
    project = render(work, name, collections)
    if not project:
        return [f"{name}: render failed"]
    status, text = make(project, "help")
    check(problems, name, status == 0 and all(t in text for t in TEMPLATE_TARGETS),
          f"make help lacks a templates target:\n{text}")
    for target in ("update-golden", "test-templates"):
        status, text = make(project, target)
        check(problems, name, status == 0, f"make {target} failed:\n{text}")
        # The fixture's own files give weaver nothing to warn about, apart from the manifest's
        # missing file_format, left out on purpose (see the asset's comment); the core
        # registry's may.
        # A finding's location is either on its warning line or on the `Provenance:` line
        # RUN_WEAVER prints after it.
        fixture_warnings = [line for line in text.splitlines()
                            if "templates_test/fixture" in line
                            and ("arning" in line or line.startswith("Provenance:"))
                            and "file_format" not in line]
        check(problems, name, not fixture_warnings,
              f"make {target} warns about the fixture: {fixture_warnings}")
    golden = os.path.join(project, "templates_test", "golden", "keys", "keys.txt")
    content = read(golden) if os.path.isfile(golden) else ""
    for collection in collections:
        check(problems, name, HEADINGS[collection] in content,
              f"the golden file has no {HEADINGS[collection]} heading")
    check(problems, name, os.path.isfile(os.path.join(project, ".github", "workflows",
                                                      "ci-validation.yaml")),
          "no CI workflow")
    return problems


def golden_drift(work):
    """test-templates fails when the golden files no longer match, and on no targets."""
    problems = []
    project = render(work, "golden-drift", ["attributes"])
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


def older_weaver(work):
    """The fixture loads on an older weaver release too, since a project keeps its own pin
    (SKILL.md step 1): install OLDER_WEAVER with the project's own script, off PATH, and run the
    template test with it through WEAVER."""
    problems = []
    project = render(work, "older-weaver", ["attributes"])
    if not project:
        return ["older-weaver: render failed"]
    bin_dir = os.path.join(work, "older-weaver", "bin")
    status, text = output(["bash", "scripts/install-weaver.sh", bin_dir], cwd=project,
                          env=dict(os.environ, WEAVER_VERSION=OLDER_WEAVER))
    if status != 0:
        return [f"older-weaver: installing weaver {OLDER_WEAVER} failed:\n{text}"]
    weaver = f"WEAVER={os.path.join(bin_dir, 'weaver')}"
    status, text = make(project, "require-weaver", weaver)
    check(problems, "older-weaver", status == 0 and OLDER_WEAVER.lstrip("v") in text,
          f"require-weaver with WEAVER didn't use weaver {OLDER_WEAVER}:\n{text}")
    for target in ("update-golden", "test-templates"):
        status, text = make(project, target, weaver)
        check(problems, "older-weaver", status == 0,
              f"make {target} with weaver {OLDER_WEAVER} failed:\n{text}")
    return problems


def weaver_failure(work):
    """A weaver run that fails makes its target fail, with weaver's error printed unwrapped."""
    problems = []
    project = render(work, "weaver-failure", ["attributes"])
    if not project:
        return ["weaver-failure: render failed"]
    status, text = make(project, "generate", "SOURCE_REGISTRY=no-such-registry")
    check(problems, "weaver-failure", status != 0 and "\nError: " in text,
          f"generate from a missing registry passed, or printed no error line:\n{text}")
    return problems


def generated_dir_guard(work):
    """generate refuses a GENERATED_DIR that can't hold only generated code, before deleting
    anything."""
    problems = []
    project = render(work, "generated-dir-guard", ["attributes"])
    if not project:
        return ["generated-dir-guard: render failed"]
    marker = os.path.join(project, "templates", "keep-me")
    with open(marker, "w", encoding="utf-8") as f:
        f.write("hand-written\n")
    for value in ("", ".", "..", "../", "templates/..", ".build", "./.build"):
        status, text = make(project, "generate", f"GENERATED_DIR={value}")
        check(problems, "generated-dir-guard", status != 0 and "GENERATED_DIR must name" in text,
              f"generate accepted GENERATED_DIR={value!r}:\n{text}")
        check(problems, "generated-dir-guard", os.path.isfile(marker),
              f"generate with GENERATED_DIR={value!r} deleted files")
    return problems


def dead_import(work):
    """An import that matches nothing in any dependency fails the template test, naming the
    pattern, though weaver itself only warns about it."""
    problems = []
    project = render(work, "dead-import", ["attributes", "metrics"])
    if not project:
        return ["dead-import: render failed"]
    metrics = os.path.join(project, "templates_test", "fixture", "fixture", "metrics.yaml")
    text = read(metrics)
    if '    - "hw.*"\n' not in text:
        return ["dead-import: the metrics fixture no longer imports hw.*"]
    with open(metrics, "w", encoding="utf-8") as f:
        f.write(text.replace('    - "hw.*"\n', '    - "hw.*"\n    - "no_such_metric.*"\n'))
    status, text = make(project, "update-golden")
    check(problems, "dead-import", status != 0 and "match nothing" in text
          and "no_such_metric.*" in text,
          f"update-golden passed with a dead import, or didn't name it:\n{text}")
    return problems


def private(work):
    """The `private` section sets --allow-git-credentials for every weaver run; without it, no
    flag is set."""
    problems = []
    for name, chosen, expected in (("private", ["attributes", "private"], True),
                                   ("public", ["attributes"], False)):
        project = render(work, f"private-{name}", chosen)
        if not project:
            return [f"private-{name}: render failed"]
        # make's database (-p, with -n so nothing runs) prints the variable as make resolved it;
        # GNU make 3.81 has no --eval.
        status, text = make(project, "-p", "-n", "help")
        flags = re.search(r"^WEAVER_FLAGS :?= ?(.*)$", text, re.M)
        has_flag = bool(flags) and "--allow-git-credentials" in flags.group(1)
        check(problems, f"private-{name}", status == 0 and bool(flags) and has_flag == expected,
              f"WEAVER_FLAGS {'lacks' if expected else 'has'} --allow-git-credentials: "
              f"{flags.group(0) if flags else 'not in make -p'}")
        if expected:
            # weaver accepts the flag on the runs the project makes.
            for target in ("update-golden", "test-templates"):
                status, text = make(project, target)
                check(problems, "private-private", status == 0,
                      f"make {target} failed with --allow-git-credentials:\n{text}")
    return problems


def subdirectory(work):
    """A project three levels down in a git repo, set up as layout.md's "Projects in a
    subdirectory" says: GENERATED_DIR points out of it into the SDK's sources, `.github/` is at
    the repo root, and the workflow's names are prefixed. generate writes only into the SDK's
    sources, and the workflow names the project and the generated code from the repo root."""
    problems = []
    repo = os.path.join(work, "subdirectory", "repo")
    if os.path.exists(repo):
        shutil.rmtree(repo)
    tokens = dict(json.loads(read(KEYS_TOKENS)), PROJECT_DIR="packages/sdk/semconv",
                  CI_WORKFLOW_NAME="Semconv CI validation",
                  CI_GATE_JOB="semconv-required-status-check", CODEGEN_TARGET="keys",
                  GENERATED_DIR="../src/generated",
                  GENERATED_REPO_PATH="packages/sdk/src/generated")
    os.makedirs(os.path.join(work, "subdirectory"), exist_ok=True)
    tokens_path = os.path.join(work, "subdirectory", "tokens.json")
    with open(tokens_path, "w", encoding="utf-8") as f:
        json.dump(tokens, f)
    project = render(work, "subdirectory", ["attributes", "no-drift"],
                     os.path.join(repo, "packages", "sdk", "semconv"), tokens_path)
    if not project:
        return ["subdirectory: render failed"]
    subprocess.run(["git", "init", "-q", repo], check=True)
    # layout.md: .github/ goes at the repo root, the workflow's file name prefixed.
    shutil.move(os.path.join(project, ".github"), os.path.join(repo, ".github"))
    workflows = os.path.join(repo, ".github", "workflows")
    os.rename(os.path.join(workflows, "ci-validation.yaml"),
              os.path.join(workflows, "semconv-ci-validation.yaml"))
    status, text = make(project, "-n", "install-weaver")
    check(problems, "subdirectory", status == 0 and "bash scripts/install-weaver.sh" in text,
          f"install-weaver from a subdirectory:\n{text}")
    status, text = make(project, "generate")
    check(problems, "subdirectory", status == 0, f"make generate failed:\n{text}")
    generated = os.path.join(repo, "packages", "sdk", "src", "generated", "keys.txt")
    check(problems, "subdirectory", os.path.isfile(generated),
          "generate didn't write into GENERATED_DIR outside the project")
    check(problems, "subdirectory", not os.path.exists(os.path.join(project, "src")),
          "generate wrote inside the project")
    workflow = read(os.path.join(workflows, "semconv-ci-validation.yaml"))
    for expected in ("working-directory: packages/sdk/semconv", "path: packages/sdk/src/generated",
                     "make -C packages/sdk/semconv generate",
                     "git add packages/sdk/src/generated/", "name: Semconv CI validation",
                     "semconv-required-status-check:"):
        check(problems, "subdirectory", expected in workflow,
              f"the workflow lacks {expected!r}")
    return problems


def install(work):
    """The install script, as `make install-weaver` and the CI fallback run it: by the version
    make passes, and by versions.env when none is passed."""
    problems = []
    project = render(work, "install", ["attributes"])
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
    # make install-weaver with WEAVER_INSTALL_DIR installs there, leaving ~/.local/bin alone.
    bin_dir = os.path.join(work, "install", "bin-make")
    status, text = make(project, "install-weaver", f"WEAVER_INSTALL_DIR={bin_dir}")
    check(problems, "install", status == 0, f"make install-weaver WEAVER_INSTALL_DIR failed:\n{text}")
    status, text = output([os.path.join(bin_dir, "weaver"), "--version"])
    check(problems, "install", status == 0 and version.lstrip("v") in text,
          f"make install-weaver didn't install {version} into WEAVER_INSTALL_DIR: {text}")
    return problems


SCENARIOS = {
    "targets": targets,
    "all-collections": lambda work: templates(work, "all-collections", COLLECTIONS),
    **{f"only-{c}": (lambda c: lambda work: templates(work, f"only-{c}", [c]))(c)
       for c in COLLECTIONS},
    "golden-drift": golden_drift,
    "older-weaver": older_weaver,
    "weaver-failure": weaver_failure,
    "dead-import": dead_import,
    "generated-dir-guard": generated_dir_guard,
    "private": private,
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
