"""Static checks of a skill's text and assets. No network, no weaver: run it after every edit.

Usage: check_skill.py [TESTS_DIR]
TESTS_DIR is the skill's tests directory, `skill-tests/<skill>/` next to `skills/<skill>/`; it
defaults to this one. Skills that build on this one pass their own. Its checks.json says where the
skill's tokens table and Makefile are; its verified-commands.json records how each command the docs
give was checked. Exits non-zero when any check fails. The checks, and the regression each one
exists for:

1. tokens: every @@TOKEN@@ in the assets is in the Tokens table, and every one there is used.
2. asset paths: every `assets/...` path the docs name exists.
3. phrases: banned or stale wording (glossary terms) is gone.
4. markers: section markers in the assets are balanced.
5. commands: every shell command the docs give is recorded in verified-commands.json, as
   "verified" with how it was checked, or as "reference" (prose naming a tool, not an invocation).
   A new or edited command fails until someone runs it and records how, since commands written
   without being run are a common source of regressions.
6. languages: every file of the skill is in a language the base's README.md "Tools, languages and
   libraries" lists, and none is Python: a project needs none.
7. privacy: no file, the tests included, carries a date, a numbered test round, or a path from a
   machine. Evidence says how to reproduce a result, not when or where it was seen.
8. breadcrumbs: no asset names a skill or points at "the layout": assets are copied into other
   repos, whose readers can't follow such a pointer.
9. line length: lines over 100 characters are reported (a warning, not a failure).
"""
import json
import os
import re
import sys

from _common import read, skill_of

TESTS = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(
    os.path.abspath(__file__))
SKILL = skill_of(TESTS)
CONFIG = json.loads(read(os.path.join(TESTS, "checks.json")))
CLIS = ("gh", "git", "make", "weaver", "jq", "rg", "curl", "python3", "zizmor", "uv", "cp", "bash",
        "go", "npm", "npx", "cargo", "swift", "./gradlew", "tsc")
SKIP_DIRS = (".work", "__pycache__")
failures = []


def fail(check, message):
    failures.append(f"[{check}] {message}")


def files_under(root):
    """Every file under ROOT, relative to it."""
    out = []
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        out += [os.path.relpath(os.path.join(dirpath, n), root) for n in names]
    return sorted(out)


FILES = files_under(SKILL)
DOCS = [f for f in FILES if f.endswith(".md")]


def text(rel):
    return read(os.path.join(SKILL, rel))


def layout_tokens():
    """The tokens the skill's Tokens table lists; none for a skill with no assets (and so no
    tokens_doc)."""
    if not CONFIG.get("tokens_doc"):
        return set()
    table = text(CONFIG["tokens_doc"]).split("## Tokens", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `([A-Z][A-Z_]*)`", table, re.M))


def makefile_text():
    return text(CONFIG["makefile"]) if CONFIG.get("makefile") else ""


def check_tokens():
    used = {}
    for rel in FILES:
        if rel.startswith("assets/"):
            for token in re.findall(r"@@([A-Z_]+)@@", text(rel)):
                used.setdefault(token, set()).add(rel)
    documented = layout_tokens()
    for token in sorted(set(used) - documented):
        fail("tokens", f"@@{token}@@ is used in {sorted(used[token])} but not in the Tokens table")
    for token in sorted(documented - set(used)):
        fail("tokens", f"{token} is in the Tokens table but used in no asset")


def check_asset_paths():
    for rel in DOCS:
        for ref in re.findall(r"`?(assets/[A-Za-z0-9_./<>-]+)`?", text(rel)):
            ref = ref.rstrip(".,)`")
            if "<" not in ref and not os.path.exists(os.path.join(SKILL, ref)):
                fail("asset paths", f"{rel} names {ref}, which doesn't exist")


# pattern -> (why, case-sensitive?)
PHRASES = {
    r"\bexported group": ("glossary: say public group", False),
    r"\bthe model's\b|\bfrom the model\b": ("glossary: model as a noun", False),
    # A quoted word is the glossary's own "don't say" list, and "core" ending a line is usually
    # "core registry" wrapped.
    r"(?<!\")\bupstream\b(?!\")": ("glossary: dependency or core registry", False),
    r"(?<![-/\"`])\bcore\b(?! registry)(?!\.)(?![-_\"`])(?!$)": ("glossary: core registry", False),
    r"\bwaiver\b|\bsuppress": ("glossary: known violation", False),
    r"layout version": ("describe the state, not versions or plans", False),
}


def check_phrases():
    for rel in FILES:
        if rel.endswith("glossary.md"):
            continue
        for number, line in enumerate(text(rel).splitlines(), 1):
            for pattern, (why, case) in PHRASES.items():
                if re.search(pattern, line, 0 if case else re.IGNORECASE):
                    fail("phrases", f"{rel}:{number}: {why}: {line.strip()[:90]}")


# What the assets must never say: they're copied into other repos, where a pointer to a skill or
# to "the layout" leads nowhere anyone else can follow.
BREADCRUMBS = r"otel-semconv-|canonical layout|\bthe layout\b|layout's"


def check_breadcrumbs():
    for rel in FILES:
        if rel.startswith("assets/"):
            for number, line in enumerate(text(rel).splitlines(), 1):
                if re.search(BREADCRUMBS, line, re.IGNORECASE):
                    fail("breadcrumbs", f"{rel}:{number}: points at a skill or the layout, which "
                         f"a repo's readers can't follow: {line.strip()[:80]}")


def check_markers():
    for rel in FILES:
        if not rel.startswith("assets/"):
            continue
        stack = []
        for number, line in enumerate(text(rel).splitlines(), 1):
            start = re.match(r"^\s*(?:#|\{#-?) ==== (?!end )([a-z-]+)", line)
            end = re.match(r"^\s*(?:#|\{#-?) ==== end ([a-z-]+)", line)
            if start:
                stack.append(start.group(1))
            elif end and (not stack or stack.pop() != end.group(1)):
                fail("markers", f"{rel}:{number}: section end {end.group(1)} doesn't match")
        if stack:
            fail("markers", f"{rel}: sections never closed: {stack}")


def makefile_targets():
    """The targets of the skill's Makefile, plus those of the Makefiles it builds on."""
    texts = [makefile_text()] + [read(os.path.join(SKILL, rel))
                                 for rel in CONFIG.get("builds_on", [])]
    return {t for body in texts for t in re.findall(r"^([a-z][a-z0-9-]*)::?(?!=)", body, re.M)}


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
        if words[0] == "make" and all(w in targets or w.startswith("-") or "=" in w
                                      for w in words[1:]):
            continue  # one of the skill's own make targets, which its scenarios run
        if command not in manifest:
            fail("commands", f"not in verified-commands.json (run it, then record how): "
                             f"{command}  [{', '.join(sorted(seen[command]))}]")
    for command in sorted(set(manifest) - set(seen)):
        fail("commands", f"verified-commands.json lists a command no doc gives any more: {command}")
    for command, entry in manifest.items():
        if entry.get("status") not in ("verified", "reference") or not entry.get("how"):
            fail("commands", f"needs a status of verified or reference, and a how: {command}")


# What the base's README.md "Tools, languages and libraries" allows in a skill: make, bash, Jinja
# (weaver uses it), and data or docs. Python is for the tests only.
ALLOWED_SUFFIXES = {".sh", ".j2", ".md", ".txt", ".json", ".json5", ".yaml", ".yml", ".env",
                    ".toml", ".rego"}
ALLOWED_NAMES = {"Makefile", ".gitignore", ".gitattributes"}


def check_languages():
    for rel in FILES:
        name = os.path.basename(rel)
        if name not in ALLOWED_NAMES and os.path.splitext(name)[1] not in ALLOWED_SUFFIXES:
            fail("languages", f"{rel}: not a language or file type a skill may hold")


# The skill and its tests carry no personal or test-run data: no dates, numbered test rounds, or
# paths from someone's machine. Evidence says how to reproduce a result, not when it was seen.
PRIVACY = {
    r"\b20\d\d-\d\d-\d\d\b": "a date",
    r"\brounds? \d+": "a numbered test round",
    # ~/.local/bin is where the install script installs weaver: a convention, not someone's machine.
    r"/Users/|/home/[a-z]|~/(?!\.local/bin)|/private/tmp|/tmp/": "a path from a machine",
}
# The patterns themselves, and the bad inputs that prove them.
PRIVACY_EXEMPT = ("check_skill.py", "self_test.py")


def check_privacy():
    for root, label in ((SKILL, "skill"), (TESTS, "tests")):
        for rel in files_under(root):
            if label == "tests" and rel in PRIVACY_EXEMPT:
                continue
            for number, line in enumerate(read(os.path.join(root, rel)).splitlines(), 1):
                for pattern, what in PRIVACY.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        fail("privacy", f"{label}/{rel}:{number}: {what}: {line.strip()[:80]}")


def check_line_lengths():
    long_lines = []
    for rel in FILES:
        for number, line in enumerate(text(rel).splitlines(), 1):
            if len(line) > 100 and not line.lstrip().startswith("|") and "http" not in line \
                    and "# renovate:" not in line and "uses: " not in line \
                    and not rel.endswith(".j2"):
                long_lines.append(f"{rel}:{number} ({len(line)})")
    print(f"   warning: {len(long_lines)} lines over 100 characters: {', '.join(long_lines)}")


def main():
    for check in (check_tokens, check_asset_paths, check_phrases, check_breadcrumbs,
                  check_markers, check_languages, check_commands, check_privacy,
                  check_line_lengths):
        check()
    for failure in failures:
        print("FAILED " + failure)
    print("check_skill: " + ("ok" if not failures else f"{len(failures)} failures"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
