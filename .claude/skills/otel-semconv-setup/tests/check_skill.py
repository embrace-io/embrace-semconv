"""Static checks of the skill's text and assets. No network, no weaver: run it after every edit.

Usage: check_skill.py
Exits non-zero when any check fails. The checks, and the regression each one exists for:

1. tokens: every @@TOKEN@@ in the assets is in layout.md's Tokens table, and every one there is used.
2. asset paths: every `assets/...` path the docs name exists.
3. phrases: banned or stale wording (glossary terms, renamed targets, old pins) is gone.
4. markers: skeleton and section markers in the assets are balanced.
5. commands: every shell command the docs give is recorded in verified-commands.json, as
   "verified" with how it was checked, or as "reference" (prose naming a tool, not an invocation).
   A new or edited command fails until someone runs it and records how, since commands written
   without being run are a common source of regressions.
6. rules: each rule listed in rules.json appears in exactly the files listed for it. A new copy,
   or a copy reworded away, fails: one rule drifting across files is another.
7. coverage: every token, Makefile setting and layout section names the test that exercises it in
   coverage.json, or says why it's untested: a mechanism with no test of its own is a third.
8. languages: every file is in a language tests/README.md's "Tools, languages and libraries"
   lists, so a new one (Ruby, JavaScript, Go...) is a decision, not an accident.
9. privacy: no file, tests included, carries a date, a numbered test round, or a path from a
   machine. Evidence says how to reproduce a result, not when or where it was seen.
10. breadcrumbs: no asset names the skill or points at "the layout": assets are copied into other
    repos, whose readers can't follow such a pointer.
11. conditions: every skeleton block's condition is one layout.md defines, so an agent can decide
    it.
12. line length: lines over 100 characters are reported (a warning, not a failure).
"""
import json
import os
import re
import sys

from _common import ASSETS, SKILL, TESTS, read

CLIS = ("gh", "git", "make", "weaver", "npm", "npx", "jq", "opa", "rg", "curl", "./gradlew",
        "ruby", "python3", "actionlint", "zizmor", "uv")
failures = []


def fail(check, message):
    failures.append(f"[{check}] {message}")


def skill_files():
    """Every file of the skill, relative to it, except the tests themselves."""
    out = []
    for dirpath, dirnames, names in os.walk(SKILL):
        dirnames[:] = [d for d in dirnames if os.path.join(dirpath, d) != TESTS]
        out += [os.path.relpath(os.path.join(dirpath, n), SKILL) for n in names]
    return sorted(out)


FILES = skill_files()
DOCS = [f for f in FILES if f.endswith(".md")]


def text(rel):
    return read(os.path.join(SKILL, rel))


def layout_tokens():
    table = text("reference/layout.md").split("## Tokens", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"`([A-Z][A-Z_]*)`", table))


def check_tokens():
    used = {}
    for rel in FILES:
        if rel.startswith("assets/"):
            for token in re.findall(r"@@([A-Z_]+)@@", text(rel)):
                used.setdefault(token, set()).add(rel)
    documented = layout_tokens()
    for token in sorted(set(used) - documented):
        fail("tokens", f"@@{token}@@ is used in {sorted(used[token])} but not in layout.md's table")
    for token in sorted(documented - set(used)):
        fail("tokens", f"{token} is in layout.md's table but used in no asset")


def check_asset_paths():
    for rel in DOCS:
        if rel.startswith("assets/"):
            continue
        for ref in re.findall(r"`?(assets/[A-Za-z0-9_./<>-]+)`?", text(rel)):
            ref = ref.rstrip(".,)`")
            if "<" not in ref and not os.path.exists(os.path.join(SKILL, ref)):
                fail("asset paths", f"{rel} names {ref}, which doesn't exist")


# pattern -> (why, files exempt from it, case-sensitive?)
PHRASES = {
    r"\bexported group": ("glossary: say public group", (), False),
    r"\bthe model's\b|\bfrom the model\b": ("glossary: model as a noun", (), False),
    # A quoted word is the glossary's own "don't say" list, and "core" ending a line is usually
    # "core registry" wrapped.
    r"(?<!\")\bupstream\b(?!\")": ("glossary: dependency or core registry", (), False),
    r"(?<![-/\"])\bcore\b(?! registry)(?!\.)(?!-version)(?![-_\"])(?!$)":
        ("glossary: core registry", (), False),
    r"\bREGISTRY_NAME\b": ("renamed to REGISTRY_URL", (), True),
    r"origin has no release tag": ("stale message", (), False),
    r"never the\s+fixture's own": ("stale fixture wording", (), False),
    r"`0\.1\.0` or `1\.0\.0`": ("stale stable-version wording", (), False),
    r"cutting|how a version is cut|\bcut from\b": ("glossary: release, not cut", (), False),
    r"\bcheck-policies\b": ("old target name", ("reference/upgrading.md",), False),
    r"\bwaiver\b|\bsuppress": ("glossary: known violation", (), False),
    # Describe the current state only: no version with nothing to compare it to, no plans.
    r"layout version|until the layout's tooling": ("describe the state, not versions or plans",
                                                   (), False),
}


def check_phrases():
    for rel in FILES:
        if rel.endswith("glossary.md"):
            continue
        for number, line in enumerate(text(rel).splitlines(), 1):
            for pattern, (why, exempt, case) in PHRASES.items():
                if rel in exempt:
                    continue
                if re.search(pattern, line, 0 if case else re.IGNORECASE):
                    fail("phrases", f"{rel}:{number}: {why}: {line.strip()[:90]}")


# What the assets must never say: they're copied into other repos, where a pointer to this skill
# or to "the layout" leads nowhere anyone else can follow.
BREADCRUMBS = r"otel-semconv-setup|canonical layout|\bthe layout\b(?! of this file)|layout's"


def check_breadcrumbs():
    for rel in FILES:
        if rel.startswith("assets/"):
            for number, line in enumerate(text(rel).splitlines(), 1):
                if re.search(BREADCRUMBS, line, re.IGNORECASE):
                    fail("breadcrumbs", f"{rel}:{number}: points at the skill or the layout, which "
                         f"a repo's readers can't follow: {line.strip()[:80]}")


# The skeleton block conditions layout.md's "The doc skeletons" defines. A block whose condition
# is none of these is one an agent can't decide.
STABILITY = r'"(?:unstable|stable|-dev family)"(?: \([^)]*\))?'
CONDITIONS = [
    rf"for stability {STABILITY}(?: or {STABILITY})?",
    r"(?:with|without) `release`",
    r"when BASELINE is (?:set|empty)(?: \([^)]*\))?",
    r"when KNOWN_VIOLATIONS is set",
    r"for a private repo",
    r"with the (?:attributes|attribute-groups|events|metrics|spans|entities) collection",
    r"with a signal collection \(events, metrics, spans, entities\)",
]


def check_conditions():
    for rel in FILES:
        if rel.startswith("assets/"):
            for number, line in enumerate(text(rel).splitlines(), 1):
                for condition in re.findall(r"<!-- skeleton: only (.*?) -->", line):
                    if not any(re.fullmatch(c, condition) for c in CONDITIONS):
                        fail("conditions", f"{rel}:{number}: a skeleton condition layout.md "
                             f"doesn't define: {condition}")


def check_markers():
    for rel in FILES:
        if not rel.startswith("assets/"):
            continue
        content = text(rel)
        opens = len(re.findall(r"<!-- skeleton: only", content))
        ends = content.count("<!-- skeleton: end -->")
        if opens != ends:
            fail("markers", f"{rel}: {opens} skeleton blocks opened, {ends} ended")
        stack = []
        for number, line in enumerate(content.splitlines(), 1):
            start = re.match(r"^\s*(?:#|\{#-?) ==== (?!end )([a-z-]+)", line)
            end = re.match(r"^\s*(?:#|\{#-?) ==== end ([a-z-]+)", line)
            if start:
                stack.append(start.group(1))
            elif end and (not stack or stack.pop() != end.group(1)):
                fail("markers", f"{rel}:{number}: section end {end.group(1)} doesn't match")
        if stack:
            fail("markers", f"{rel}: sections never closed: {stack}")


def makefile_targets():
    return set(re.findall(r"^([a-z][a-z0-9-]*)::?(?!=)", text("assets/project/Makefile"), re.M))


def doc_commands():
    """(command, where) for every shell command in the docs: inline code and fenced shell blocks."""
    found = []
    for rel in DOCS:
        content = text(rel)
        fenced = []
        for lang, block in re.findall(r"```([a-z]*)\n(.*?)```", content, re.S):
            if lang in ("bash", "sh", "shell", "console", ""):
                joined = re.sub(r"\\\n\s*", " ", block)
                fenced += [(line, "fenced") for line in joined.splitlines()]
        prose = re.sub(r"```.*?```", "", content, flags=re.S)
        inline = [(span, "inline") for span in re.findall(r"`([^`\n]+)`", prose)]
        for raw, kind in fenced + inline:
            command = re.sub(r"^\$ ", "", raw.strip())
            command = re.sub(r"\s{2,}#.*$", "", command)
            command = re.sub(r"\s+", " ", command).strip()
            if command.split(" ", 1)[0] in CLIS and " " in command:
                found.append((command, rel))
    return found


def check_commands():
    manifest = json.loads(read(os.path.join(TESTS, "verified-commands.json")))
    targets = makefile_targets()
    seen = {}
    for command, rel in doc_commands():
        seen.setdefault(command, set()).add(rel)
    for command in sorted(seen):
        words = command.split(" ")
        if words[0] == "make" and all(w in targets or w.startswith("-") for w in words[1:]):
            continue  # a layout target: run by matrix.py and codegen.py
        if command not in manifest:
            fail("commands", f"not in verified-commands.json (run it, then record how): "
                             f"{command}  [{', '.join(sorted(seen[command]))}]")
    for command in sorted(set(manifest) - set(seen)):
        fail("commands", f"verified-commands.json lists a command no doc gives any more: {command}")
    for command, entry in manifest.items():
        if entry.get("status") not in ("verified", "reference") or not entry.get("how"):
            fail("commands", f"needs a status of verified or reference, and a how: {command}")


def check_rules():
    rules = json.loads(read(os.path.join(TESTS, "rules.json")))
    for rule in rules:
        regex = re.compile(rule["pattern"], re.IGNORECASE)
        actual = {rel for rel in FILES if regex.search(re.sub(r"\s+", " ", text(rel)))}
        listed = set(rule["files"])
        for rel in sorted(actual - listed):
            fail("rules", f"{rule['id']}: {rel} restates the rule (point to {rule['files'][0]}, "
                          f"or list it and keep the copies in step)")
        for rel in sorted(listed - actual):
            fail("rules", f"{rule['id']}: {rel} no longer states it: reworded or removed? "
                          f"Update every copy together")


def section_names():
    names = set()
    for rel in FILES:
        if rel.startswith("assets/"):
            names.update(re.findall(r"^\s*(?:#|\{#-?) ==== (?!end )([a-z-]+)", text(rel), re.M))
    return names


def makefile_settings():
    names = re.findall(r"^([A-Z][A-Z0-9_]*) *[:?]?=(?!=)", text("assets/project/Makefile"), re.M)
    return set(names) - {"SHELL"}


def check_coverage():
    sys.path.insert(0, TESTS)
    import codegen
    import matrix
    coverage = json.loads(read(os.path.join(TESTS, "coverage.json")))
    targets = json.loads(read(os.path.join(TESTS, "field", "targets.json")))
    cases = {os.path.relpath(dirpath, ASSETS).split("validations_test/", 1)[1]
             for dirpath, _, names in os.walk(ASSETS) if "expected-error.txt" in names}
    kinds = {"tokens": layout_tokens(), "settings": makefile_settings(),
             "sections": section_names()}
    for kind, items in kinds.items():
        recorded = coverage.get(kind, {})
        for item in sorted(items - set(recorded)):
            fail("coverage", f"{kind[:-1]} {item} has no entry in coverage.json: name the test "
                             f"that exercises it, or say why it's untested")
        for item in sorted(set(recorded) - items):
            fail("coverage", f"coverage.json lists {kind[:-1]} {item}, which no longer exists")
        for item, evidence in recorded.items():
            for entry in evidence:
                kind_, _, name = entry.partition(":")
                ok = {"matrix": name in matrix.SCENARIOS, "codegen": name in codegen.PROJECTS,
                      "case": name in cases, "field": name in targets["tests"],
                      "curated-filter": True, "actions-dir": True, "release-lookups": True,
                      "renovate-extract": True, "renovate-version": True,
                      "template-types": True,
                      "internal": True,
                      "untested": bool(name)}
                if not ok.get(kind_, False):
                    fail("coverage", f"{kind[:-1]} {item}: evidence '{entry}' names nothing known")
    untested = [f"{k[:-1]} {i}" for k, items in coverage.items() for i, ev in items.items()
                if all(e.startswith("untested") for e in ev)]
    print(f"   coverage: {len(untested)} untested: {', '.join(untested) or 'none'}")


# What tests/README.md's "Tools, languages and libraries" allows: code (make, bash, Python in
# tests/, and Rego and Jinja because weaver uses them) and data or docs.
ALLOWED_SUFFIXES = {".py", ".sh", ".rego", ".j2", ".md", ".txt", ".json", ".json5", ".yaml",
                    ".yml", ".env", ".toml"}
ALLOWED_NAMES = {"Makefile", ".gitignore", ".gitattributes"}


def check_languages():
    for dirpath, dirnames, names in os.walk(SKILL):
        dirnames[:] = [d for d in dirnames if d not in (".work", "__pycache__")]
        for name in names:
            rel = os.path.relpath(os.path.join(dirpath, name), SKILL)
            suffix = os.path.splitext(name)[1]
            if name in ALLOWED_NAMES or suffix in ALLOWED_SUFFIXES:
                if suffix == ".py" and not rel.startswith("tests/"):
                    fail("languages", f"{rel}: Python outside tests/ (the layout needs no Python)")
                continue
            fail("languages", f"{rel}: not a language or file type tests/README.md lists")


# The skill and its tests carry no personal or test-run data: no dates, numbered test rounds, or
# paths from someone's machine. Evidence says how to reproduce a result, not when it was seen.
PRIVACY = {
    r"\b20\d\d-\d\d-\d\d\b": "a date",
    r"\brounds? \d+": "a numbered test round",
    # ~/.local/bin is where the layout installs tools: a convention, not someone's machine.
    r"/Users/|/home/[a-z]|~/(?!\.local/bin)|/private/tmp|/tmp/": "a path from a machine",
}


def check_privacy():
    for dirpath, dirnames, names in os.walk(SKILL):
        dirnames[:] = [d for d in dirnames if d not in (".work", "__pycache__")]
        for name in names:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, SKILL)
            if rel in ("tests/check_skill.py", "tests/self_test.py"):
                continue  # the patterns themselves, and the bad inputs that prove them
            for number, line in enumerate(read(path).splitlines(), 1):
                for pattern, what in PRIVACY.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        fail("privacy", f"{rel}:{number}: {what}: {line.strip()[:80]}")


def check_line_lengths():
    long_lines = []
    for rel in FILES:
        for number, line in enumerate(text(rel).splitlines(), 1):
            if len(line) > 100 and not line.lstrip().startswith("|") and "http" not in line \
                    and "# renovate:" not in line and not rel.endswith((".j2", ".json5")):
                long_lines.append(f"{rel}:{number} ({len(line)})")
    print(f"   warning: {len(long_lines)} lines over 100 characters: {', '.join(long_lines)}")


def main():
    for check in (check_tokens, check_asset_paths, check_phrases, check_breadcrumbs,
                  check_conditions, check_markers, check_rules,
                  check_coverage, check_languages, check_commands, check_privacy,
                  check_line_lengths):
        check()
    for failure in failures:
        print("FAILED " + failure)
    print("check_skill: " + ("ok" if not failures else f"{len(failures)} failures"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
