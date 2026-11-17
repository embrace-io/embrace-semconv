# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Render the CI workflow with the registry and docs parts, with and without their private
sections, as it ships and with the base's fallback for setup-weaver, and run the base's workflow
checks on each: it parses, the aggregate job needs exactly the other jobs, every job installs
weaver at most once and the same way, and zizmor (pedantic persona, the latest release) finds
nothing.

Usage: uv run lint_workflows.py [--uv UV] [--work DIR]
"""
import os
import subprocess

from _docs import read, render_project, work_dir

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
        if not render_project(args.work, f"workflows-{name}", dest,
                              ["attributes", "attribute-groups"], private=access == "private",
                              policies="public-groups"):
            return 1
        workflow = os.path.join(dest, ".github", "workflows", "ci-validation.yaml")
        fallback = install == "fallback"
        if fallback:
            text, count = base.apply_fallback(read(workflow), base.fallback_step())
            if count != 3:
                problems.append(f"{name}: the base's fallback replaced {count} of the 3 jobs' "
                                "weaver steps")
            with open(workflow, "w", encoding="utf-8") as f:
                f.write(text)
        found = [f"{name}: {p}" for p in base.check_workflow(workflow, fallback)]
        if (access == "private") != ("gh auth setup-git" in read(workflow)):
            found.append(f"{name}: the private sections don't match the variant")
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
