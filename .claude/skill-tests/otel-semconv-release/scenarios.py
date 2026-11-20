"""Set up a registry project with the release part on the base layout, and run its targets.

Usage: scenarios.py [SCENARIO ...] [--work DIR]
Needs weaver at the pinned version, jq, opa, git, GNU make and network access.
- package: print-version prints the manifest's version, and package writes the publication
  artifacts with the release's resolved_registry_uri, even when git's view of origin carries a
  token (a CI credential pattern): REPO_URL must not pick it up.
- dev-family: with VERSION_SUFFIX := -dev, print-version (which the Release workflow reads)
  accepts 0.1.0-dev and refuses 0.1.0.
"""
import os
import subprocess
import sys

from _release import output, read, render_project, run, work_dir

EXPECTED_URI = ("resolved_registry_uri: https://github.com/acme/acme-semconv/releases/"
                "download/v0.1.0-dev/resolved.yaml")


def package(work):
    name = "package"
    dest = os.path.join(work, "release", name)
    if not render_project(work, name, dest):
        return [f"{name}: render failed"]
    subprocess.run(["git", "-C", dest, "config",
                    "url.https://x-access-token:FAKE@github.com/acme/acme-semconv.insteadOf",
                    "git@github.com:acme/acme-semconv"], check=True)
    problems = []
    status, text = output(["make", "-C", dest, "-s", "print-version"])
    if status != 0 or text.strip() != "0.1.0-dev":
        problems.append(f"{name}: print-version printed {text.strip()!r}")
    if not run(work, f"{name}-package", ["make", "package"], cwd=dest):
        return problems + [f"{name}: make package failed"]
    manifest = read(os.path.join(dest, ".build", "package", "manifest.yaml"))
    uri = next((line for line in manifest.splitlines()
                if line.startswith("resolved_registry_uri:")), "")
    if uri != EXPECTED_URI:
        problems.append(f"{name}: {uri!r}, expected {EXPECTED_URI!r}")
    if not os.path.exists(os.path.join(dest, ".build", "package", "resolved.yaml")):
        problems.append(f"{name}: no resolved.yaml")
    if not os.path.exists(os.path.join(dest, ".github", "workflows", "release.yml")):
        problems.append(f"{name}: no release workflow")
    return problems


def dev_family(work):
    name = "dev-family"
    dest = os.path.join(work, "release", name)
    if not render_project(work, name, dest):
        return [f"{name}: render failed"]
    makefile = os.path.join(dest, "Makefile")
    text = read(makefile)
    with open(makefile, "w") as f:
        f.write(text.replace("\nVERSION_SUFFIX :=\n", "\nVERSION_SUFFIX := -dev\n", 1))
    problems = []
    status, text = output(["make", "-C", dest, "-s", "print-version"])
    if status != 0 or text.strip() != "0.1.0-dev":
        problems.append(f"{name}: print-version didn't accept 0.1.0-dev: {text.strip()!r}")
    manifest = os.path.join(dest, "model", "manifest.yaml")
    text = read(manifest)
    with open(manifest, "w") as f:
        f.write(text.replace("/acme/0.1.0-dev", "/acme/0.1.0", 1))
    status, text = output(["make", "-C", dest, "-s", "print-version"])
    if status == 0 or "VERSION_SUFFIX" not in text:
        problems.append(f"{name}: print-version didn't refuse 0.1.0: {text.strip()!r}")
    return problems


SCENARIOS = {"package": package, "dev-family": dev_family}


def main():
    args = work_dir(__doc__)
    problems = []
    for name in args.names or list(SCENARIOS):
        found = SCENARIOS[name](args.work)
        print(("ok" if not found else "FAILED") + f": scenario {name}")
        problems += found
    for problem in problems:
        print("SCENARIO PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
