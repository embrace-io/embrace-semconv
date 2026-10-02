"""Run the Renovate extraction check exactly as reference/layout.md prints it, on rendered
projects that carry every kind of `# renovate:` pin the layout has, and check what it claims:
every annotated pin shows up in the report, under its file and depName.

Usage: renovate_extract.py [--work DIR]
The registry project has versions.env's three pins and both manifests' core registry; the codegen
project adds a SOURCE_REGISTRY pinned to a release, annotated as layout.md says. Needs git, jq,
npx and network access (npx fetches Renovate). Extracting the block from the doc means an edit to
it is tested, not remembered.
"""
import os
import re
import shutil
import subprocess
import sys

from _common import FIXTURES, RENDER, SKILL, read, run, work_dir

PROJECTS = [
    ("registry", "registry,attributes,attribute-groups,renovate", "acme.json"),
    ("codegen", "codegen,attributes,renovate", "core-codegen.json"),
]
SOURCE_REGISTRY_ANNOTATION = ("# renovate: datasource=github-tags "
                              "depName=open-telemetry/semantic-conventions versioning=semver-coerced\n")
# A `# renovate:` comment line; the match strings in renovate.json5 quote one, so they don't count.
ANNOTATION = re.compile(r"^\s*# renovate: .*?depName=(\S+)", re.M)


def doc_block():
    """The bash block of layout.md's `renovate` section that runs the extraction."""
    text = read(os.path.join(SKILL, "reference", "layout.md"))
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        if "--dry-run=extract" in block:
            return "\n".join(line.strip() for line in block.splitlines())
    raise SystemExit("layout.md: no bash block with --dry-run=extract")


def render(work, name, features, tokens):
    dest = os.path.join(work, "renovate-extract", name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    if not run(work, f"renovate-extract-{name}-render",
               [sys.executable, RENDER, dest, features, os.path.join(FIXTURES, "tokens", tokens)]):
        return None
    if name == "codegen":
        makefile = os.path.join(dest, "Makefile")
        text = read(makefile).replace("SOURCE_REGISTRY :=", SOURCE_REGISTRY_ANNOTATION
                                      + "SOURCE_REGISTRY :=", 1)
        with open(makefile, "w", encoding="utf-8") as f:
            f.write(text)
    # layout.md: Renovate reads only tracked files, so they are staged first.
    subprocess.run(["git", "init", "-q", dest], check=True)
    subprocess.run(["git", "-C", dest, "add", "-A"], check=True)
    return dest


def renovate_version():
    """The Renovate version the layout's versions.env pins."""
    text = read(os.path.join(SKILL, "assets", "common", "versions.env"))
    match = re.search(r"^RENOVATE_VERSION=(\S+)", text, re.M)
    if not match:
        raise SystemExit("versions.env: no RENOVATE_VERSION")
    return match.group(1)


def annotated(project):
    """(file, depName) for every `# renovate:` line in the project's tracked files."""
    files = subprocess.run(["git", "-C", project, "ls-files"], check=True, capture_output=True,
                           text=True).stdout.split()
    pins = set()
    for name in files:
        for match in ANNOTATION.finditer(read(os.path.join(project, name))):
            pins.add((name, match.group(1)))
    return pins


def main():
    args = work_dir(__doc__)
    block = doc_block()
    problems = []
    for name, features, tokens in PROJECTS:
        project = render(args.work, name, features, tokens)
        if not project:
            return 1
        scratch = os.path.join(args.work, "renovate-extract", f"{name}-scratch")
        os.makedirs(scratch, exist_ok=True)
        script = block.replace("<scratch dir>", scratch).replace("<RENOVATE_VERSION>",
                                                                  renovate_version())
        # The doc says to judge by the report, not the exit code (Renovate exits non-zero on a
        # Node newer than it supports), so only the jq step's success counts here.
        result = subprocess.run(["bash", "-c", script], cwd=project, capture_output=True,
                                text=True)
        with open(os.path.join(scratch, "output.log"), "w", encoding="utf-8") as f:
            f.write(result.stdout + result.stderr)
        if result.returncode != 0:
            problems.append(f"{name}: the doc's block failed (see {scratch}/output.log and "
                            f"renovate.log)")
        extracted = {tuple(line.split()[:2]) for line in result.stdout.splitlines()
                     if len(line.split()) >= 2}
        expected = annotated(project)
        if not expected:
            problems.append(f"{name}: the rendered project has no `# renovate:` lines")
        for file, dep in sorted(expected - extracted):
            problems.append(f"{name}: {file}: {dep} is annotated but Renovate didn't extract it")
        print(f"   {name}: {len(expected)} annotated, {len(extracted)} extracted")
    for problem in problems:
        print("RENOVATE PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + ": renovate-extract (every annotated pin)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
