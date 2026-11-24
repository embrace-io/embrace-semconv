"""Run the Renovate extraction check exactly as reference/renovate.md prints it, on projects with
every kind of `# renovate:` pin the skill's parts annotate, and check what it claims: Renovate
extracts exactly the annotated pins, each under its file and depName, with the pinned value.

Usage: renovate_extract.py [--work DIR] [PROJECT...]
One project per case sources.md's "The fixture's core registry" distinguishes:
- core: SOURCE_REGISTRY is the core registry, annotated as renovate.md says, and the fixture
  manifest keeps its line, so both come out under the core registry's depName, at one release;
- federated: SOURCE_REGISTRY is a published federated registry, and the fixture manifest's line
  is deleted, so nothing moves the fixture;
- own: SOURCE_REGISTRY is a registry directory of the project's own whose manifest annotates its
  core registry dependency the way the fixture's does, and the fixture keeps its line.
The fixture manifest's line gives two pins (schema_url and registry_path); every other line one.
Needs git, jq, npx and network access (npx fetches Renovate). Extracting the blocks from the doc
means an edit to them is tested, not remembered.
"""
import json
import os
import re
import shutil
import subprocess
import sys

from _common import SKILL, TOKENS, pinned_version, read, render_project, work_dir

CORE = "open-telemetry/semantic-conventions"
FEDERATED = ("embrace-io/embrace-semconv", "0.3.0")
FIXTURE = "templates_test/fixture/manifest.yaml"


def doc_blocks():
    """(the annotated SOURCE_REGISTRY lines, with <owner>/<repo> and <version> left in, and the
    extraction command) from renovate.md."""
    text = read(os.path.join(SKILL, "reference", "renovate.md"))
    make = [b for b in re.findall(r"```make\n(.*?)```", text, re.S) if "SOURCE_REGISTRY" in b]
    bash = [b for b in re.findall(r"```bash\n(.*?)```", text, re.S) if "--dry-run=extract" in b]
    if not make or not bash:
        raise SystemExit("renovate.md: no SOURCE_REGISTRY block or extraction block")
    source = "\n".join(line.strip() for line in make[0].splitlines()) + "\n"
    return source, "\n".join(line.strip() for line in bash[0].splitlines())


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def replace_source(project, lines):
    """Replace the Makefile's SOURCE_REGISTRY line with LINES."""
    makefile = os.path.join(project, "Makefile")
    new, count = re.subn(r"^SOURCE_REGISTRY := .*\n", lambda _: lines, read(makefile), count=1,
                         flags=re.M)
    if count != 1:
        raise SystemExit("the rendered Makefile has no SOURCE_REGISTRY line")
    write(makefile, new)


def fixture_annotation(project):
    """The fixture manifest's `# renovate:` line and the two lines it annotates."""
    text = read(os.path.join(project, FIXTURE))
    match = re.search(r"^ *# renovate: .*\n.*\n.*\n", text, re.M)
    if not match:
        raise SystemExit("the rendered fixture manifest has no # renovate: line")
    return match.group(0)


def delete_fixture_annotation(project):
    path = os.path.join(project, FIXTURE)
    write(path, re.sub(r"^ *# renovate: .*\n", "", read(path), count=1, flags=re.M))


def setup(name, project, source):
    """Make the project NAME's case; returns the (file, depName, value) pins it must give."""
    core = json.loads(read(TOKENS))["CORE_VERSION"]
    weaver = re.search(r"^WEAVER_VERSION=(\S+)$", read(os.path.join(project, "versions.env")),
                       re.M).group(1)
    pins = {("versions.env", "open-telemetry/weaver", weaver),
            ("versions.env", "renovate", pinned_version())}
    fixture = {(FIXTURE, CORE, core), (FIXTURE, CORE, f"v{core}")}
    if name == "core":
        replace_source(project, source.replace("<owner>/<repo>", CORE).replace("<version>", core))
        return pins | fixture | {("Makefile", CORE, f"v{core}")}
    if name == "federated":
        repo, version = FEDERATED
        replace_source(project, source.replace("<owner>/<repo>", repo).replace("<version>",
                                                                               version))
        delete_fixture_annotation(project)
        return pins | {("Makefile", repo, f"v{version}")}
    # own: a registry directory of the project's own, depending on the core registry the way the
    # fixture does, annotated the same way.
    replace_source(project, "SOURCE_REGISTRY := model\n")
    write(os.path.join(project, "model", "manifest.yaml"),
          "schema_url: https://example.com/schemas/own/0.1.0-dev\n"
          "description: A registry of the project's own.\nstability: development\n"
          "dependencies:\n" + fixture_annotation(project))
    return pins | fixture | {("model/manifest.yaml", CORE, core),
                             ("model/manifest.yaml", CORE, f"v{core}")}


def check(work, name, source, block):
    project = os.path.join(work, "renovate-extract", name, "project")
    if os.path.exists(project):
        shutil.rmtree(project)
    os.makedirs(project)
    subprocess.run(["git", "init", "-q", project], check=True)
    if not render_project(work, f"renovate-extract-{name}", project, ["renovate", "attributes"]):
        return [f"{name}: render failed"]
    expected = setup(name, project, source)
    # renovate.md: Renovate reads only tracked files, so they are staged first.
    subprocess.run(["git", "-C", project, "add", "-A"], check=True)
    scratch = os.path.join(work, "renovate-extract", name, "scratch")
    os.makedirs(scratch, exist_ok=True)
    script = block.replace("<scratch dir>", scratch).replace("<RENOVATE_VERSION>",
                                                              pinned_version())
    # renovate.md says to judge by the report, not Renovate's exit code (it exits non-zero on a
    # Node newer than it supports), so only the jq step's success counts here.
    result = subprocess.run(["bash", "-c", script], cwd=project, capture_output=True, text=True)
    write(os.path.join(scratch, "output.log"), result.stdout + result.stderr)
    if result.returncode != 0:
        return [f"{name}: the doc's block failed (see {scratch}/output.log and renovate.log)"]
    extracted = {tuple(line.split()[:3]) for line in result.stdout.splitlines()
                 if len(line.split()) >= 3}
    problems = [f"{name}: {f} {d} {v} is pinned but Renovate didn't extract it"
                for f, d, v in sorted(expected - extracted)]
    problems += [f"{name}: Renovate extracted {f} {d} {v}, which nothing should give"
                 for f, d, v in sorted(extracted - expected)]
    print(f"   {name}: {len(expected)} pins expected, {len(extracted)} extracted")
    return problems


def main():
    args = work_dir(__doc__)
    source, block = doc_blocks()
    problems = []
    for name in args.names or ["core", "federated", "own"]:
        found = check(args.work, name, source, block)
        print(("ok" if not found else "FAILED") + f": renovate-extract ({name})")
        problems += found
    for problem in problems:
        print("RENOVATE PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
