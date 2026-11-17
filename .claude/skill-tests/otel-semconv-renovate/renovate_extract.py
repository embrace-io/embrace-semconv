"""Run the Renovate extraction check exactly as reference/part.md prints it, on a project with
every kind of `# renovate:` pin the otel-semconv parts annotate, and check what it claims: every
annotated pin shows up in the report, under its file and depName.

Usage: renovate_extract.py [--work DIR]
The project has the base's weaver pin and fixture manifest, the registry part's policy pack, OPA
and core registry pins when the registry skill is installed alongside, this part's Renovate pin,
and a codegen SOURCE_REGISTRY pinned to a release, annotated as part.md says (a Makefile line of
its own, since the codegen part isn't set up here). Needs git, jq, npx and network access (npx fetches Renovate). Extracting the block from
the doc means an edit to it is tested, not remembered.
"""
import os
import re
import shutil
import subprocess
import sys

from _renovate import SKILL, WITH_REGISTRY, pinned_version, read, render_project, work_dir

# A `# renovate:` comment line; the match strings in renovate.json5 quote one, so they don't count.
ANNOTATION = re.compile(r"^\s*# renovate: .*?depName=(\S+)", re.M)


def doc_blocks():
    """(the SOURCE_REGISTRY annotation, the extraction command) from part.md."""
    text = read(os.path.join(SKILL, "reference", "part.md"))
    make = [b for b in re.findall(r"```make\n(.*?)```", text, re.S) if "SOURCE_REGISTRY" in b]
    bash = [b for b in re.findall(r"```bash\n(.*?)```", text, re.S) if "--dry-run=extract" in b]
    if not make or not bash:
        raise SystemExit("part.md: no SOURCE_REGISTRY block or extraction block")
    source = "\n".join(line.strip() for line in make[0].splitlines())
    source = source.replace("<owner>/<repo>", "open-telemetry/semantic-conventions").replace(
        "<version>", "1.44.0")
    return source + "\n", "\n".join(line.strip() for line in bash[0].splitlines())


def annotated(project):
    """(file, depName) for every `# renovate:` line in the project's tracked files."""
    files = subprocess.run(["git", "-C", project, "ls-files"], check=True, capture_output=True,
                           text=True).stdout.split()
    return {(name, match.group(1)) for name in files
            for match in ANNOTATION.finditer(read(os.path.join(project, name)))}


def main():
    args = work_dir(__doc__)
    source, block = doc_blocks()
    project = os.path.join(args.work, "renovate-extract", "project")
    if os.path.exists(project):
        shutil.rmtree(project)
    if not render_project(args.work, "renovate-extract", project):
        return 1
    with open(os.path.join(project, "Makefile"), "a", encoding="utf-8") as f:
        f.write("\n" + source)
    # part.md: Renovate reads only tracked files, so they are staged first.
    subprocess.run(["git", "-C", project, "add", "-A"], check=True)
    scratch = os.path.join(args.work, "renovate-extract", "scratch")
    os.makedirs(scratch, exist_ok=True)
    script = block.replace("<scratch dir>", scratch).replace("<RENOVATE_VERSION>",
                                                              pinned_version())
    # part.md says to judge by the report, not Renovate's exit code (it exits non-zero on a Node
    # newer than it supports), so only the jq step's success counts here.
    result = subprocess.run(["bash", "-c", script], cwd=project, capture_output=True, text=True)
    with open(os.path.join(scratch, "output.log"), "w", encoding="utf-8") as f:
        f.write(result.stdout + result.stderr)
    problems = []
    if result.returncode != 0:
        problems.append(f"the doc's block failed (see {scratch}/output.log and renovate.log)")
    extracted = {tuple(line.split()[:2]) for line in result.stdout.splitlines()
                 if len(line.split()) >= 2}
    expected = annotated(project)
    for file, dep in sorted(expected - extracted):
        problems.append(f"{file}: {dep} is annotated but Renovate didn't extract it")
    print(f"   {len(expected)} annotated, {len(extracted)} extracted"
          + ("" if WITH_REGISTRY else " (no registry skill here, so not its pins)"))
    for problem in problems:
        print("RENOVATE PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + ": renovate-extract (every annotated pin)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
