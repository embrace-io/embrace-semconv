"""Paths shared by this skill's tests, and the base skill's test helpers they build on. The tests
live outside the skill, in `skill-tests/<skill>/` next to `skills/<skill>/`, and the base skill's
tests are expected next to these. Not part of the instructions."""
import os
import shutil
import subprocess
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
TOKENS = os.path.join(FIXTURES, "tokens", "registry.json")
RENDER = os.path.join(BASE_TESTS, "render.py")
ADD_PART = os.path.join(BASE_TESTS, "add_part.py")
BASE_TEMPLATES = os.path.join(BASE_TESTS, "fixtures", "templates")
__all__ = ["ASSETS", "BASE_TESTS", "COLLECTIONS", "FIXTURES", "SKILL", "TOKENS", "TESTS",
           "output", "read", "run", "work_dir", "RENDER", "ADD_PART", "POLICIES",
           "registry_part", "render_project"]

# The registry's local policy choices (SKILL.md step 1): none, policies of its own (the `policies`
# section alone), or the public-attribute-groups policy (`public-groups`, which needs `policies`).
POLICIES = ("none", "own", "public-groups")


def registry_part(collections, policies="none", templates=False, private=False):
    """(asset directories to copy, sections to keep) for the registry part with these choices."""
    if policies not in POLICIES:
        raise ValueError(policies)
    chosen = {"none": [], "own": ["policies"], "public-groups": ["policies", "public-groups"]}
    sections = chosen[policies]
    parts = ["registry", *sections] + (["templates-case"] if templates else [])
    keep = ["registry", *collections, *sections] + (["private"] if private else [])
    return parts, keep


def fresh_repo(dest):
    """An empty git repo whose origin is the tokens' canonical repo."""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    subprocess.run(["git", "init", "-q", dest], check=True)
    subprocess.run(["git", "-C", dest, "remote", "add", "origin",
                    "git@github.com:acme/acme-semconv.git"], check=True)


def render_project(work, label, dest, collections, templates=False, private=False,
                   tokens=TOKENS, policies="none"):
    """A fresh repo with the base's core (and templates part), then the registry part with its
    collections and POLICIES choice, as an agent following both skills would set it up. Returns
    success."""
    fresh_repo(dest)
    base_parts = (["templates", *collections] if templates else [])
    parts, keep = registry_part(collections, policies, templates, private)
    if not (run(work, f"{label}-render",
                [sys.executable, RENDER, dest, ",".join(base_parts), tokens])
            and run(work, f"{label}-add-registry",
                    [sys.executable, ADD_PART, dest, ASSETS, ",".join(parts), ",".join(keep),
                     tokens])):
        return False
    if templates:
        shutil.copytree(BASE_TEMPLATES, os.path.join(dest, "templates"))
    return True
