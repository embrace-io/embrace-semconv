"""Paths shared by this skill's tests, and the base skill's test helpers they build on. The tests
live outside the skill, in `skill-tests/<skill>/` next to `skills/<skill>/`, and the base skill's
tests are expected next to these. Not part of the instructions."""
import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
BASE_TESTS = os.path.join(os.path.dirname(TESTS), "otel-semconv-base")
if not os.path.isdir(BASE_TESTS):
    raise SystemExit(f"the otel-semconv-base skill's tests aren't at {BASE_TESTS}")
sys.path.insert(1, BASE_TESTS)

from _common import COLLECTIONS, output, read, run, skill_of, work_dir  # noqa: E402

SKILL = skill_of(TESTS)
ASSETS = os.path.join(SKILL, "assets")
FIXTURES = os.path.join(TESTS, "fixtures")
TOKENS = os.path.join(FIXTURES, "tokens", "codegen.json")
RENDER = os.path.join(BASE_TESTS, "render.py")
ADD_PART = os.path.join(BASE_TESTS, "add_part.py")
__all__ = ["ASSETS", "BASE_TESTS", "COLLECTIONS", "FIXTURES", "SKILL", "TOKENS", "TESTS",
           "output", "read", "run", "work_dir", "RENDER", "ADD_PART", "render_project"]


def render_project(work, label, dest, base_parts, keep, tokens=TOKENS):
    """Render the base parts BASE_PARTS (and collections), then add the codegen part with KEEP
    sections. Returns success."""
    os.makedirs(dest, exist_ok=True)
    return (run(work, f"{label}-render", [sys.executable, RENDER, dest, ",".join(base_parts),
                                         tokens])
            and run(work, f"{label}-add-codegen", [sys.executable, ADD_PART, dest, ASSETS, "",
                                                   ",".join(keep), tokens]))
