"""Run every "Which core release" lookup in reference/languages.md and check that it still works.

Usage: python3 check_lookups.py [languages.md]
The file defaults to the skill's reference/languages.md; pass a broken copy to see a failure. This
script lives outside the skill, in `skill-tests/<skill>/` next to `skills/<skill>/`, so it isn't
installed with it.
Each `<!-- lookup: <name> -->` marker is followed by a bash block. Its first line must print the
latest release; a second line, where there is one, runs with that release as `<tag>` and must
print the core release it carries. Every language section must have a lookup.
Needs network access, bash, curl, jq and an authenticated gh.
"""
import os
import re
import subprocess
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(os.path.dirname(os.path.dirname(TESTS)), "skills", os.path.basename(TESTS))
LANGUAGES = os.path.join(SKILL, "reference", "languages.md")
VERSION = re.compile(r"\d+\.\d+\.\d+")


def lookups(text):
    """(name, [command lines]) for each lookup marker, in order."""
    found = []
    pattern = re.compile(r"<!-- lookup: (\S+) -->\s*```bash\n(.*?)```", re.S)
    for match in pattern.finditer(text):
        lines = [line.strip() for line in match.group(2).splitlines() if line.strip()]
        found.append((match.group(1), lines))
    return found


def run(command):
    result = subprocess.run(["bash", "-c", "set -o pipefail; " + command],
                            capture_output=True, text=True, timeout=120)
    out = result.stdout.strip()
    return result.returncode, out.splitlines()[-1].strip() if out else "", result.stderr.strip()


def main():
    with open(sys.argv[1] if len(sys.argv) > 1 else LANGUAGES, encoding="utf-8") as f:
        text = f.read()
    problems = []

    sections = re.findall(r"^## (.+)$", text, re.M)
    found = lookups(text)
    if len(found) != len(sections):
        problems.append(f"{len(found)} lookups for {len(sections)} language sections")

    status, core, err = run("gh api repos/open-telemetry/semantic-conventions/releases/latest "
                            "--jq .tag_name")
    if status != 0 or not VERSION.search(core):
        problems.append(f"core registry lookup failed: {core or err}")
    print(f"core registry: {core}")

    for name, lines in found:
        if not 1 <= len(lines) <= 2 or ("<tag>" in lines[0]) or (
                len(lines) == 2 and "<tag>" not in lines[1]):
            problems.append(f"{name}: a lookup is one line, or two with <tag> in the second only")
            continue
        status, latest, err = run(lines[0])
        if status != 0 or not VERSION.search(latest):
            problems.append(f"{name}: the latest-release line printed {latest!r} ({err})")
            continue
        carried = latest
        if len(lines) == 2:
            status, carried, err = run(lines[1].replace("<tag>", latest))
            if status != 0 or not VERSION.search(carried):
                problems.append(f"{name}: the core-release line printed {carried!r} ({err})")
                continue
        print(f"ok: {name}: latest {latest} carries {VERSION.search(carried).group(0)}")

    for problem in problems:
        print("LOOKUP PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + ": lookups")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
