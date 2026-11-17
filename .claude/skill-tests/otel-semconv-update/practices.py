"""Check reference/practices.md's table, which the skill applies in order: rows are numbered 1, 2,
3, ... with every cell filled, and each practice is applied by this skill or an otel-semconv
skill. When that skill is installed next to this one, it must exist; one that isn't installed is
listed, not failed, since a branch may carry only some of the skills.

Usage: practices.py
No network.
"""
import os
import re
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.join(os.path.dirname(TESTS), "otel-semconv-base"))

from _common import read, skill_of  # noqa: E402

SKILL = skill_of(TESTS)
SKILLS = os.path.dirname(SKILL)


def main():
    text = read(os.path.join(SKILL, "reference", "practices.md"))
    rows = [line for line in text.splitlines() if re.match(r"^\| \d+ \|", line)]
    problems, unchecked = [], set()
    for expected, row in enumerate(rows, 1):
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) != 4 or not all(cells):
            problems.append(f"row {expected}: not four filled cells: {row[:60]}")
            continue
        if cells[0] != str(expected):
            problems.append(f"row {expected} is numbered {cells[0]}")
        owners = re.findall(r"otel-semconv-[a-z]+", cells[3])
        if not owners and not cells[3].startswith("this skill"):
            problems.append(f"row {expected}: applied by neither this skill nor an otel-semconv "
                            f"skill: {cells[3]}")
        for owner in owners:
            if not os.path.isdir(os.path.join(SKILLS, owner)):
                unchecked.add(owner)
    if not rows:
        problems.append("practices.md has no numbered practice rows")
    for problem in problems:
        print("PRACTICES PROBLEM: " + problem)
    if unchecked:
        print("   not installed here, so not checked: " + ", ".join(sorted(unchecked)))
    print(("ok" if not problems else "FAILED") + f": practices ({len(rows)} rows)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
