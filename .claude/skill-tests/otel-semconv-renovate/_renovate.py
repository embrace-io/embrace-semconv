"""Paths shared by this skill's tests, and the base skill's test helpers they build on (the
registry skill's too, when it is installed alongside). The tests live outside the skill, in
`skill-tests/<skill>/` next to `skills/<skill>/`, and the tests they build on are expected next to
these. Not part of the instructions."""
import os
import re
import shutil
import subprocess
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
BASE_TESTS = os.path.join(os.path.dirname(TESTS), "otel-semconv-base")
REGISTRY_TESTS = os.path.join(os.path.dirname(TESTS), "otel-semconv-registry")
if not os.path.isdir(BASE_TESTS):
    raise SystemExit(f"the otel-semconv-base skill's tests aren't at {BASE_TESTS}")
sys.path.insert(1, BASE_TESTS)

from _common import output, read, run, skill_of, work_dir  # noqa: E402

SKILL = skill_of(TESTS)
ASSETS = os.path.join(SKILL, "assets")
RENDER = os.path.join(BASE_TESTS, "render.py")
ADD_PART = os.path.join(BASE_TESTS, "add_part.py")
BASE_TOKENS = os.path.join(BASE_TESTS, "fixtures", "tokens", "base.json")
# The registry part's pins are covered when the registry skill and its tests are installed here.
WITH_REGISTRY = (os.path.isdir(REGISTRY_TESTS)
                 and os.path.isdir(os.path.join(os.path.dirname(SKILL), "otel-semconv-registry")))
__all__ = ["ASSETS", "BASE_TESTS", "REGISTRY_TESTS", "SKILL", "TESTS", "WITH_REGISTRY", "output",
           "read", "run", "work_dir", "pinned_version", "render_project"]


def pinned_version():
    """The Renovate version the skill's versions.env section pins."""
    match = re.search(r"^RENOVATE_VERSION=(\S+)$",
                      read(os.path.join(ASSETS, "project", "versions.env")), re.M)
    if not match:
        raise SystemExit("versions.env: no RENOVATE_VERSION")
    return match.group(1)


def render_project(work, label, dest):
    """The base's core and templates parts, then the registry part with attributes, groups and
    its policies when WITH_REGISTRY, then this part: every pin those parts annotate. Returns
    success."""
    if WITH_REGISTRY:
        sys.path.insert(2, REGISTRY_TESTS)
        import _registry
        tokens = _registry.TOKENS
        ready = _registry.render_project(work, label, dest, ["attributes", "attribute-groups"],
                                         templates=True, policies="public-groups")
    else:
        tokens = BASE_TOKENS
        if os.path.exists(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        subprocess.run(["git", "init", "-q", dest], check=True)
        ready = run(work, f"{label}-render",
                    [sys.executable, RENDER, dest, "templates,attributes", tokens])
    return ready and run(work, f"{label}-add-renovate",
                         [sys.executable, ADD_PART, dest, ASSETS, "renovate", "renovate", tokens])
