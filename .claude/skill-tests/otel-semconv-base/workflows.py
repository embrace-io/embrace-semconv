# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Render the CI workflow as it ships and with reference/layout.md's fallback applied, then check
both: each parses, the aggregate job needs exactly the other jobs, every job installs weaver one
way only, and zizmor (pedantic persona, the latest release) finds nothing.

Usage: uv run workflows.py [--uv UV] [--work DIR]
zizmor runs through `uv tool run`, online when `gh auth token` gives a token, offline otherwise
(which it says). No weaver is needed.
"""
import os
import re
import shutil
import subprocess
import sys
import textwrap

import yaml

from _common import COLLECTIONS, RENDER, SKILL, TOKENS, read, run, work_dir

SETUP_WEAVER = "open-telemetry/weaver/.github/actions/setup-weaver@"


def fallback_step():
    """The step layout.md's "When the action isn't allowed" gives, as a workflow's steps are
    indented (the block itself is indented for the Markdown list it is in)."""
    layout = read(os.path.join(SKILL, "reference", "layout.md"))
    section = layout.split("**When the action isn't allowed:**", 1)[1]
    block = textwrap.dedent(re.search(r"```yaml\n(.*?)```", section, re.S).group(1)).strip("\n")
    return textwrap.indent(block, "      ") + "\n"


def apply_fallback(text, step):
    """Replace each job's "Read pinned weaver version" and "Install Weaver" steps with STEP."""
    pattern = re.compile(r"      - name: Read pinned weaver version\n.*?"
                         r"      - name: Install Weaver\n        uses: [^\n]+\n"
                         r"        with:\n(?:          [^\n]+\n)+", re.S)
    replaced, count = pattern.subn(step.replace("\\", "\\\\"), text)
    return replaced, count


def check_workflow(path, fallback):
    """Problems in the workflow at PATH: a gate that doesn't need every other job, or a job that
    installs weaver more than once or not the way FALLBACK says. A job without weaver (one that
    only runs OPA, say) installs it not at all; every other job installs it once."""
    problems = []
    doc = yaml.safe_load(read(path))
    jobs = doc["jobs"]
    weaver_jobs = 0
    for job_id, job in jobs.items():
        if job.get("needs") and "always()" in str(job.get("if", "")):
            needs = sorted(job["needs"])
            if needs != sorted(set(jobs) - {job_id}):
                problems.append(f"gate {job_id} needs {needs}, jobs are {sorted(set(jobs) - {job_id})}")
            continue
        steps = job.get("steps", [])
        installs = [s for s in steps if s.get("name") == "Install Weaver"]
        uses = [s for s in steps if str(s.get("uses", "")).startswith(SETUP_WEAVER)]
        reads = [s for s in steps if s.get("name") == "Read pinned weaver version"]
        if not installs and not uses and not reads:
            continue
        weaver_jobs += 1
        if len(installs) != 1:
            problems.append(f"{job_id}: {len(installs)} Install Weaver steps")
        elif fallback and (uses or reads or installs[0].get("run") != "make install-weaver"):
            problems.append(f"{job_id}: the fallback still uses the action or reads the version")
        elif not fallback and (len(uses) != 1 or len(reads) != 1):
            problems.append(f"{job_id}: doesn't install weaver with setup-weaver")
    if not weaver_jobs:
        problems.append("no job installs weaver")
    return problems


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
    for variant in ("action", "fallback"):
        dest = os.path.join(args.work, "workflows", variant)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        if not run(args.work, f"workflows-{variant}-render",
                   [sys.executable, RENDER, dest, ",".join(["templates", "no-drift", *COLLECTIONS]),
                    TOKENS]):
            return 1
        workflow = os.path.join(dest, ".github", "workflows", "ci-validation.yaml")
        if variant == "fallback":
            text, count = apply_fallback(read(workflow), fallback_step())
            if count == 0:
                problems.append("fallback: layout.md's step replaced no Install Weaver step")
            with open(workflow, "w", encoding="utf-8") as f:
                f.write(text)
        problems += [f"{variant}: {p}" for p in check_workflow(workflow, variant == "fallback")]
        result = subprocess.run(zizmor + [os.path.join(dest, ".github")], env=env,
                                capture_output=True, text=True)
        if result.returncode != 0:
            problems.append(f"{variant}: zizmor:\n{result.stdout}{result.stderr}")
        print(("ok" if not problems else "FAILED") + f": workflows ({variant})")
    for problem in problems:
        print("WORKFLOW PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
