"""Run the release workflow's tag and draft lookups exactly as the skill's release.yml has them,
against a public repo, and check that only "not found" reads as an answer: an existing tag or a
published release refuses, a missing one goes on (tag) or refuses with the draft hint (release),
and a lookup that fails for another reason (a bad token here) stops with GitHub's error instead.

Usage: release_lookups.py [--work DIR]
Needs gh (logged in) and network access. The token is passed to the steps in their environment,
as Actions does, and never printed.
"""
import os
import re
import subprocess
import sys

from _release import ASSETS, read, work_dir

WORKFLOW = os.path.join(ASSETS, "release", ".github", "workflows", "release.yml")
# Test data only: a public repo with a published release.
REPO = "open-telemetry/semantic-conventions"
EXISTING = "v1.44.0"
MISSING = "v0.0.0-never-released"
TAG_STEP = "Refuse if the git tag already exists"
DRAFT_STEP = "Find the draft release matching schema_url"

# (step, tag, token, expected exit code is zero, text the output must contain)
CASES = [
    (TAG_STEP, EXISTING, "real", False, "already exists"),
    (TAG_STEP, MISSING, "real", True, "is new"),
    (TAG_STEP, MISSING, "bad", False, "Could not check whether tag"),
    (DRAFT_STEP, EXISTING, "real", False, "already published"),
    (DRAFT_STEP, MISSING, "real", False, "Expected a draft release"),
    (DRAFT_STEP, MISSING, "bad", False, "Could not look up the release"),
]


def step_script(text, name):
    """The `run: |` block of the step named NAME, dedented."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == f"- name: {name}"), None)
    if start is None:
        raise SystemExit(f"release.yml: no step named '{name}'")
    run = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |")
    indent = len(lines[run]) - len(lines[run].lstrip())
    body = []
    for line in lines[run + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line)
    width = min(len(line) - len(line.lstrip()) for line in body if line.strip())
    return "\n".join(line[width:] for line in body) + "\n"


def main():
    args = work_dir(__doc__)
    temp = os.path.join(args.work, "release-lookups")
    os.makedirs(temp, exist_ok=True)
    token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    if not token:
        print("FAILED: release-lookups needs a logged-in gh (`gh auth token` printed nothing)")
        return 1
    text = read(WORKFLOW)
    problems = []
    for step, tag, which, should_pass, expected in CASES:
        env = dict(os.environ, GH_TOKEN=token if which == "real" else "not-a-token", TAG=tag,
                   GITHUB_REPOSITORY=REPO, GH_REPO=REPO, RUNNER_TEMP=temp)
        # Actions runs a step's script with `bash -e`.
        result = subprocess.run(["bash", "-e", "-c", step_script(text, step)], env=env,
                                capture_output=True, text=True)
        output = re.sub(re.escape(token), "<token>", result.stdout + result.stderr)
        label = f"{step} ({tag}, {which} token)"
        if (result.returncode == 0) != should_pass or expected not in output:
            problems.append(f"{label}: exit {result.returncode}, expected "
                            f"{'success' if should_pass else 'failure'} with '{expected}':\n"
                            + output)
        else:
            print(f"   ok: {label}")
    for problem in problems:
        print("RELEASE PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + ": release-lookups (only not-found is an answer)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
