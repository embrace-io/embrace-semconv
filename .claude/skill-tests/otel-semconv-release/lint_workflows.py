# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Render the release workflow (with the registry's CI workflow beside it), with and without its
private sections, as it ships and with the base's fallback for setup-weaver, and check it: it
parses, it installs weaver once and the way the variant says, it doesn't cache weaver when the
action installs it, and zizmor (pedantic persona, the latest release) finds nothing in either
workflow.

Usage: uv run lint_workflows.py [--uv UV] [--work DIR]
"""
import os
import subprocess

import yaml

from _release import read, render_project, work_dir

import workflows as base  # the base skill's workflows.py, next to these tests

VARIANTS = {f"{install}-{access}": (install, access)
            for install in ("action", "fallback") for access in ("public", "private")}


def main():
    args = work_dir(__doc__, options=("--uv",))
    uv = args.uv or "uv"
    token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    env = dict(os.environ)
    zizmor = [uv, "tool", "run", "zizmor@latest", "--persona", "pedantic", "--format", "plain"]
    if token:
        env["GH_TOKEN"] = token
    else:
        zizmor.append("--offline")
        print("note: no `gh auth token`, so zizmor runs offline (no online audits)")
    problems = []
    for name, (install, access) in VARIANTS.items():
        dest = os.path.join(args.work, "workflows", name)
        if not render_project(args.work, f"workflows-{name}", dest, private=access == "private"):
            return 1
        workflows = os.path.join(dest, ".github", "workflows")
        fallback = install == "fallback"
        found = []
        for workflow, expected in (("release.yml", 1), ("ci-validation.yaml", 2)):
            path = os.path.join(workflows, workflow)
            if fallback:
                text, count = base.apply_fallback(read(path), base.fallback_step())
                if count != expected:
                    found.append(f"{name}: {workflow}: the fallback replaced {count} of "
                                 f"{expected} jobs' weaver steps")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
            found += [f"{name}: {workflow}: {p}" for p in base.check_workflow(path, fallback)]
        release = yaml.safe_load(read(os.path.join(workflows, "release.yml")))
        for step in release["jobs"]["release"]["steps"]:
            if str(step.get("uses", "")).startswith(base.SETUP_WEAVER) and \
                    str(step.get("with", {}).get("cache")).lower() != "false":
                found.append(f"{name}: release.yml caches weaver while publishing")
        if (access == "private") != ("gh auth setup-git" in read(os.path.join(workflows,
                                                                               "release.yml"))):
            found.append(f"{name}: release.yml's private sections don't match the variant")
        result = subprocess.run(zizmor + [os.path.join(dest, ".github")], env=env,
                                capture_output=True, text=True)
        if result.returncode != 0:
            found.append(f"{name}: zizmor:\n{result.stdout}{result.stderr}")
        print(("ok" if not found else "FAILED") + f": workflows ({name})")
        problems += found
    for problem in problems:
        print("WORKFLOW PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
