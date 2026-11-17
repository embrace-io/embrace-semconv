"""Run reference/part.md's Renovate version lookup and its validator step exactly as printed, on
a repo the hosted Renovate app has opened pull requests in and on one it hasn't, and check what
they claim: the lookup prints the version the app last ran, or nothing; the step validates with
that version, or falls back to versions.env's pin.

Usage: renovate_version.py [--work DIR]
Needs a logged-in gh and network. Nothing is validated: the step's npx line is replaced by an
echo of the version it would run.
"""
import os
import re
import subprocess
import sys

from _renovate import SKILL, pinned_version, read, work_dir

# Test data only: a public repo the hosted app opens pull requests in, and one it never has
# (GitHub's own sample repo, which doesn't use Renovate).
WITH_APP = "open-telemetry/opentelemetry-js"
WITHOUT_APP = "octocat/Hello-World"
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def doc_snippets():
    """(the lookup command, the validator step's run script) from part.md."""
    text = read(os.path.join(SKILL, "reference", "part.md"))
    lookup = [b for b in re.findall(r"```bash\n(.*?)```", text, re.S) if "renovate-debug" in b]
    step = [b for b in re.findall(r"```yaml\n(.*?)```", text, re.S) if "renovate-debug" in b]
    if not lookup or not step:
        raise SystemExit("part.md: no renovate-debug lookup and validator step")
    script = step[0].split("run: |\n", 1)[1]
    indent = len(script) - len(script.lstrip(" "))
    return lookup[0].strip(), "\n".join(line[indent:] for line in script.splitlines())


def main():
    args = work_dir(__doc__)
    lookup, script = doc_snippets()
    problems = []

    found = {}
    for repo in (WITH_APP, WITHOUT_APP):
        result = subprocess.run(["bash", "-c", lookup.replace("<owner>/<repo>", repo)],
                                capture_output=True, text=True)
        found[repo] = result.stdout.strip()
        if result.returncode != 0:
            problems.append(f"the lookup failed on {repo}: {result.stderr.strip()[:200]}")
    if not SEMVER.match(found[WITH_APP]):
        problems.append(f"the lookup printed {found[WITH_APP]!r} for {WITH_APP}, not the version "
                        "its pull requests' footer names")
    if found[WITHOUT_APP]:
        problems.append(f"the lookup printed {found[WITHOUT_APP]!r} for {WITHOUT_APP}, which has "
                        "no Renovate pull request")

    env_file = os.path.join(args.work, "renovate-version", "versions.env")
    os.makedirs(os.path.dirname(env_file), exist_ok=True)
    with open(env_file, "w") as f:
        f.write(f"RENOVATE_VERSION={pinned_version()}\n")
    body = script.replace("source <project dir>/versions.env", f"source '{env_file}'")
    body = re.sub(r"^npx .*$", 'echo "would validate with ${version}"', body, flags=re.M)
    for repo, expected in ((WITH_APP, found[WITH_APP]), (WITHOUT_APP, pinned_version())):
        result = subprocess.run(["bash", "-e", "-c", body], capture_output=True, text=True,
                                env={**os.environ, "GH_REPO": repo})
        if result.returncode != 0 or f"would validate with {expected}" not in result.stdout:
            problems.append(f"the validator step on {repo} didn't choose {expected}: "
                            f"{(result.stdout + result.stderr).strip()[:200]}")

    for problem in problems:
        print("RENOVATE VERSION PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED")
          + f": renovate-version ({WITH_APP}: {found[WITH_APP] or 'none'}; {WITHOUT_APP}: none)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
