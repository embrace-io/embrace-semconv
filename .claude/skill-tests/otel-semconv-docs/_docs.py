"""Paths shared by this skill's tests, and the base and registry skills' test helpers they build
on. The tests live outside the skill, in `skill-tests/<skill>/` next to `skills/<skill>/`, and the
base's and registry's tests are expected next to these. Not part of the instructions."""
import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
BASE_TESTS = os.path.join(os.path.dirname(TESTS), "otel-semconv-base")
REGISTRY_TESTS = os.path.join(os.path.dirname(TESTS), "otel-semconv-registry")
for required in (BASE_TESTS, REGISTRY_TESTS):
    if not os.path.isdir(required):
        raise SystemExit(f"the tests this skill builds on aren't at {required}")
sys.path.insert(1, BASE_TESTS)
sys.path.insert(2, REGISTRY_TESTS)

from _common import output, read, run, skill_of, work_dir  # noqa: E402
import _registry  # noqa: E402

SKILL = skill_of(TESTS)
ASSETS = os.path.join(SKILL, "assets")
FIXTURES = os.path.join(TESTS, "fixtures")
TOKENS = os.path.join(FIXTURES, "tokens", "docs.json")
ADD_PART = _registry.ADD_PART
__all__ = ["ASSETS", "BASE_TESTS", "FIXTURES", "REGISTRY_TESTS", "SKILL", "TOKENS", "TESTS",
           "output", "read", "run", "work_dir", "render_project"]


def render_project(work, label, dest, collections, private=False, tokens=TOKENS,
                   policies="none"):
    """The base's core and no-drift parts, the registry part with COLLECTIONS and its POLICIES
    choice, then the docs part, as an agent following the three skills would set them up.
    Returns success."""
    _registry.fresh_repo(dest)
    keep = ["docs"] + (["private"] if private else [])
    parts, registry_keep = _registry.registry_part(collections, policies, private=private)
    return (run(work, f"{label}-render", [sys.executable, _registry.RENDER, dest, "no-drift",
                                         tokens])
            and run(work, f"{label}-add-registry",
                    [sys.executable, ADD_PART, dest, _registry.ASSETS, ",".join(parts),
                     ",".join(registry_keep), tokens])
            and run(work, f"{label}-add-docs",
                    [sys.executable, ADD_PART, dest, ASSETS, "docs", ",".join(keep), tokens]))
