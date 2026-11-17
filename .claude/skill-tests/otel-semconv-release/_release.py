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
TOKENS = os.path.join(FIXTURES, "tokens", "release.json")
__all__ = ["ASSETS", "BASE_TESTS", "FIXTURES", "REGISTRY_TESTS", "SKILL", "TOKENS", "TESTS",
           "output", "read", "run", "work_dir", "render_project"]

MODEL = """file_format: definition/2

attribute_groups:
  - id: registry.acme
    visibility: public
    stability: development
    brief: Attributes in the `acme` namespace.
    attributes:
      - ref: acme.tenant.id

attributes:
  - key: acme.tenant.id
    type: string
    stability: development
    brief: Identifier of the tenant the telemetry belongs to.
    examples: ["t-123"]
"""


def render_project(work, label, dest, private=False, tokens=TOKENS):
    """The base's core, the registry part with attributes and groups and a registry, then the
    release part, as an agent following the three skills would set them up. Returns success."""
    collections = ["attributes", "attribute-groups"]
    if not _registry.render_project(work, label, dest, collections, private=private,
                                    tokens=tokens, policies="public-groups"):
        return False
    os.makedirs(os.path.join(dest, "model", "acme"))
    with open(os.path.join(dest, "model", "acme", "registry.yaml"), "w") as f:
        f.write(MODEL)
    keep = ["release"] + (["private"] if private else [])
    return run(work, f"{label}-add-release",
               [sys.executable, _registry.ADD_PART, dest, ASSETS, "release", ",".join(keep),
                tokens])
