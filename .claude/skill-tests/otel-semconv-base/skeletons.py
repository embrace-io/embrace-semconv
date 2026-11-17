"""Resolve skeletons' conditional blocks the way reference/layout.md ("Skeletons") says, for
every combination of choices, and check that each condition is one layout.md defines, that the
blocks balance, and that no block marker is left.

Usage: skeletons.py SKELETONS_DIR
The skills that ship skeletons (docs, release) pass their assets/skeletons/. No network, no
weaver.
"""
import itertools
import os
import re
import sys

from _common import read

ONLY = re.compile(r"^\s*<!-- skeleton: only (.*?) -->\s*$")
END = re.compile(r"^\s*<!-- skeleton: end -->\s*$")
COLLECTIONS = ("attributes", "attribute-groups", "events", "metrics", "spans", "entities")
SIGNALS = {"events", "metrics", "spans", "entities"}
STABILITIES = {"unstable": "unstable", "stable": "stable", "-dev family": "-dev family"}


def holds(condition, choice):
    """Whether CONDITION holds for CHOICE; raises ValueError for a condition layout.md doesn't
    define."""
    if condition.startswith("for stability "):
        named = re.findall(r'"([^"]+)"', condition)
        if not named or any(n not in STABILITIES for n in named):
            raise ValueError(condition)
        return choice["stability"] in named
    if condition == "with `release`":
        return choice["release"]
    if condition == "without `release`":
        return not choice["release"]
    if re.fullmatch(r"when BASELINE is set(?: \([^)]*\))?", condition):
        return choice["baseline"]
    if re.fullmatch(r"when BASELINE is empty(?: \([^)]*\))?", condition):
        return not choice["baseline"]
    if condition == "when KNOWN_VIOLATIONS is set":
        return choice["known"]
    if condition == "for a private repo":
        return choice["private"]
    if condition == "with `public-groups`":
        return choice["public_groups"]
    collection = re.fullmatch(r"with the ([a-z-]+) collection", condition)
    if collection and collection.group(1) in COLLECTIONS:
        return collection.group(1) in choice["collections"]
    if condition == "with a signal collection (events, metrics, spans, entities)":
        return bool(SIGNALS & set(choice["collections"]))
    raise ValueError(condition)


def resolve(text, choice):
    out, stack = [], []
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        only, end = ONLY.match(line), END.match(line)
        if only:
            stack.append(holds(only.group(1), choice))
        elif end:
            if not stack:
                raise ValueError(f"line {number}: an end with no open block")
            stack.pop()
        elif "<!-- skeleton: only" in line or "<!-- skeleton: end" in line:
            raise ValueError(f"line {number}: a block marker that isn't on a line of its own")
        elif all(stack):
            out.append(line)
    if stack:
        raise ValueError(f"{len(stack)} blocks never ended")
    return "".join(out)


def choices():
    for stability, release, baseline, known, private, collections, public_groups in (
            itertools.product(STABILITIES, (True, False), (True, False), (True, False),
                              (True, False),
                              (("attributes", "attribute-groups"), ("attributes",), ("events",),
                               COLLECTIONS),
                              (True, False))):
        if public_groups and "attributes" not in collections:
            continue
        yield {"stability": stability, "release": release, "baseline": baseline, "known": known,
               "private": private, "collections": collections, "public_groups": public_groups}


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    directory = sys.argv[1]
    problems, rendered = [], 0
    for name in sorted(os.listdir(directory)):
        text = read(os.path.join(directory, name))
        for choice in choices():
            try:
                result = resolve(text, choice)
            except ValueError as error:
                problems.append(f"{name}: {error}")
                break
            rendered += 1
            if re.search(r"<!-- skeleton: (only|end)", result):
                problems.append(f"{name}: a block marker is left for {choice}")
                break
    for problem in problems:
        print("SKELETON PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + f": skeletons ({rendered} renders)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
