# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6,<7"]
# ///
"""Render the CI workflow, with and without its private sections, as it ships and with
reference/layout.md's fallback applied, then check each: it parses, the aggregate job needs
exactly the other jobs, every job installs weaver one way only, and zizmor (pedantic persona, the
latest release) finds nothing.

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
# The jobs that run weaver: test-templates and validate-generated.
WEAVER_JOBS = 2
VARIANTS = {f"{install}-{access}": (install == "fallback", access == "private")
            for install in ("action", "fallback") for access in ("public", "private")}


def fallback_step():
    """The step layout.md's "When the action isn't allowed" gives, as a workflow's steps are
    indented (the block itself is indented for the Markdown list it is in)."""
    layout = read(os.path.join(SKILL, "reference", "layout.md"))
    section = layout.split("**When the action isn't allowed:**", 1)[1]
    block = textwrap.dedent(re.search(r"```yaml\n(.*?)```", section, re.S).group(1)).strip("\n")
    return textwrap.indent(block, "      ") + "\n"


def dotslash_form():
    """(the `uses:` value, the comment ending its line, the header line replacing the `$/` one)
    layout.md's actionlint form gives."""
    layout = read(os.path.join(SKILL, "reference", "layout.md"))
    uses = re.search(r"`uses: (\./\.github/actions/assert-no-drift)`", layout)
    comment = re.search(r"`(# zizmor: ignore\[self-repository\])`", layout)
    header = re.search(r"replace it with\s+`(# [^`]+)`", layout)
    if not uses or not comment or not header:
        raise SystemExit("layout.md: no actionlint form for the drift step")
    return uses.group(1), comment.group(1), re.sub(r"\s+", " ", header.group(1))


def dependabot_ignore():
    """The dependency-name layout.md's Dependabot ignore entry gives for setup-weaver."""
    layout = read(os.path.join(SKILL, "reference", "layout.md"))
    match = re.search(r"```yaml\n\s*ignore:\n\s*- dependency-name: (\S+)\n\s*```", layout)
    if not match:
        raise SystemExit("layout.md: no Dependabot ignore entry for setup-weaver")
    return match.group(1)


def apply_fallback(text, step):
    """Replace each job's "Read pinned weaver version" and "Install Weaver" steps with STEP."""
    pattern = re.compile(r"      - name: Read pinned weaver version\n.*?"
                         r"      - name: Install Weaver\n        uses: [^\n]+\n"
                         r"        with:\n(?:          [^\n]+\n)+", re.S)
    replaced, count = pattern.subn(step.replace("\\", "\\\\"), text)
    return replaced, count


def check_workflow(path, fallback):
    """Problems in the workflow at PATH: a gate that doesn't need every other job, or a job that
    installs weaver more than once or not the way FALLBACK says. A job without weaver (one the
    repo adds that runs only the platform's tools, say) installs it not at all; every other job
    installs it once."""
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
    for variant, (fallback, private) in VARIANTS.items():
        dest = os.path.join(args.work, "workflows", variant)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        chosen = ["no-drift", *COLLECTIONS] + (["private"] if private else [])
        if not run(args.work, f"workflows-{variant}-render",
                   [sys.executable, RENDER, dest, ",".join(chosen), TOKENS]):
            return 1
        workflow = os.path.join(dest, ".github", "workflows", "ci-validation.yaml")
        found = []
        if fallback:
            text, count = apply_fallback(read(workflow), fallback_step())
            if count != WEAVER_JOBS:
                found.append(f"layout.md's fallback replaced {count} of the {WEAVER_JOBS} jobs' "
                             "steps")
            with open(workflow, "w", encoding="utf-8") as f:
                f.write(text)
        found += check_workflow(workflow, fallback)
        if private and "gh auth setup-git" not in read(workflow):
            found.append("no private sections kept")
        result = subprocess.run(zizmor + [os.path.join(dest, ".github")], env=env,
                                capture_output=True, text=True)
        if result.returncode != 0:
            found.append(f"zizmor:\n{result.stdout}{result.stderr}")
        print(("ok" if not found else "FAILED") + f": workflows ({variant})")
        problems += [f"{variant}: {p}" for p in found]
    # layout.md's actionlint form: the drift step as `./` with zizmor's ignore comment, which
    # zizmor then reports as ignored, not as a finding.
    dest = os.path.join(args.work, "workflows", "dotslash")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    if not run(args.work, "workflows-dotslash-render",
               [sys.executable, RENDER, dest, ",".join(["no-drift", *COLLECTIONS]), TOKENS]):
        return 1
    workflow = os.path.join(dest, ".github", "workflows", "ci-validation.yaml")
    uses, comment, header = dotslash_form()
    text = read(workflow)
    found = []
    if "uses: $/.github/actions/assert-no-drift\n" not in text:
        found.append("the workflow has no `uses: $/` drift step to change")
    old_header = re.search(r"^# .*`uses: \$/…`.*\n", text, re.M)
    if not old_header:
        found.append("the workflow has no header line about `uses: $/…` to replace")
    else:
        text = text.replace(old_header.group(0), header + "\n")
    if "$/" in text.replace("uses: $/.github/actions/assert-no-drift\n", ""):
        found.append("the actionlint form leaves a `$/` outside the drift step")
    with open(workflow, "w", encoding="utf-8") as f:
        f.write(text.replace("uses: $/.github/actions/assert-no-drift\n",
                             f"uses: {uses} {comment}\n"))
    # Dependabot names a subpath action by its full path (a real Dependabot run named
    # setup-weaver's that way, and ignored only that name), so the ignore entry must be the
    # path the workflow's `uses:` gives.
    if dependabot_ignore() != SETUP_WEAVER.rstrip("@"):
        found.append(f"layout.md's Dependabot ignore entry {dependabot_ignore()} isn't the "
                     f"workflow's setup-weaver path {SETUP_WEAVER.rstrip('@')}")
    result = subprocess.run(zizmor + [os.path.join(dest, ".github")], env=env,
                            capture_output=True, text=True)
    output = result.stdout + result.stderr
    if result.returncode != 0 or "1 ignored" not in output:
        found.append(f"zizmor on the actionlint form:\n{output}")
    print(("ok" if not found else "FAILED") + ": workflows (dotslash)")
    problems += [f"dotslash: {p}" for p in found]
    for problem in problems:
        print("WORKFLOW PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
