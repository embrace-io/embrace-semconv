"""Set up registry projects with the docs part on the base layout, and generate their docs with
the shared templates.

Usage: scenarios.py [SCENARIO ...] [--work DIR]
Needs weaver at the pinned version, jq, opa, git, GNU make and network access (weaver fetches the
core registry, the shared policy pack and the shared templates).
- with-import: a registry that imports a core registry group. Its docs cover only its own
  namespace, link within DOCS_BASE_URL, and validate-registry and every test still pass.
- events-only: a registry of events that references core registry attributes.
- workaround-still-needed: the shared templates, run without the docs-import-only exclusion,
  still document the imported namespace. When this fails, the templates leave imported
  definitions out themselves, and the exclusion can go.
"""
import os
import re
import sys

from _docs import TOKENS, output, read, render_project, run, work_dir

ATTRIBUTES = """attribute_groups:
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

imports:
  attribute_groups:
    - registry.user_agent
"""
EVENTS = """events:
  - name: acme.checkout
    requirement_level: recommended
    stability: development
    brief: A checkout completed.
    attributes:
      - ref: session.id
        requirement_level: recommended
"""
BASE_URL = "https://github.com/acme/acme-semconv/blob/main/docs"


def project(work, name, collections, model):
    dest = os.path.join(work, "docs", name)
    if not render_project(work, name, dest, collections):
        return None
    os.makedirs(os.path.join(dest, "model", "acme"))
    with open(os.path.join(dest, "model", "acme", "registry.yaml"), "w") as f:
        f.write("file_format: definition/2\n\n" + model)
    return dest


def pages(dest):
    root = os.path.join(dest, "docs")
    return sorted(os.path.relpath(os.path.join(d, n), root)
                  for d, _, names in os.walk(root) for n in names)


def check_docs(name, dest, expected_pages):
    problems = []
    found = pages(dest)
    if found != sorted(expected_pages):
        problems.append(f"{name}: docs pages {found}, expected {sorted(expected_pages)}")
    for page in found:
        text = read(os.path.join(dest, "docs", page))
        for link in re.findall(r"\]\((/[^)]*|https?://[^)]*)\)", text):
            if link.startswith("/") or ("acme-semconv" in link and not link.startswith(BASE_URL)):
                problems.append(f"{name}: {page} links {link}, outside DOCS_BASE_URL")
    return problems


def with_import(work):
    name = "with-import"
    dest = project(work, name, ["attributes", "attribute-groups"], ATTRIBUTES)
    if not dest:
        return [f"{name}: render failed"]
    problems = []
    status, text = output(["make", "-C", dest, "help"])
    if "generate-docs" not in text:
        problems.append(f"{name}: make help lacks generate-docs")
    for target in ("generate-docs", "validate-registry", "test", ""):
        if not run(work, f"{name}-{target or 'all'}", ["make", target] if target else ["make"],
                   cwd=dest):
            problems.append(f"{name}: make {target or '(all)'} failed")
    problems += check_docs(name, dest, ["README.md", "acme/README.md"])
    readme = read(os.path.join(dest, "docs", "acme", "README.md")) if os.path.exists(
        os.path.join(dest, "docs", "acme", "README.md")) else ""
    if "acme.tenant.id" not in readme:
        problems.append(f"{name}: the acme page doesn't document acme.tenant.id")
    workflow = read(os.path.join(dest, ".github", "workflows", "ci-validation.yaml"))
    if "  validate-docs:" not in workflow or "- validate-docs # docs" not in workflow:
        problems.append(f"{name}: the CI workflow lacks validate-docs or its needs entry")
    return problems


def events_only(work):
    name = "events-only"
    dest = project(work, name, ["events"], EVENTS)
    if not dest:
        return [f"{name}: render failed"]
    problems = []
    for target in ("generate-docs", "validate-registry", "test"):
        if not run(work, f"{name}-{target}", ["make", target], cwd=dest):
            problems.append(f"{name}: make {target} failed")
    problems += check_docs(name, dest, ["README.md", "acme/README.md", "acme/events.md"])
    events = os.path.join(dest, "docs", "acme", "events.md")
    if os.path.exists(events) and "session.id" not in read(events):
        problems.append(f"{name}: the event page doesn't list the referenced session.id")
    return problems


UPSTREAM_DOCS = """
[template]
acronyms = ["ACME"]

[template.text_maps.upstream_docs]
"https://opentelemetry.io/schemas/1.44.0" = "https://github.com/open-telemetry/semantic-conventions/blob/v1.44.0/docs/registry/attributes/{namespace}.md"
"""


def upstream_docs(work):
    """part.md's `.weaver.toml` settings: a dependency's attributes link to its docs, and an
    acronym titles its namespace."""
    name = "upstream-docs"
    dest = project(work, name, ["events"], EVENTS)
    if not dest:
        return [f"{name}: render failed"]
    with open(os.path.join(dest, ".weaver.toml"), "a", encoding="utf-8") as f:
        f.write(UPSTREAM_DOCS)
    if not run(work, f"{name}-generate-docs", ["make", "generate-docs"], cwd=dest):
        return [f"{name}: make generate-docs failed"]
    link = ("https://github.com/open-telemetry/semantic-conventions/blob/v1.44.0/docs/registry/"
            "attributes/session.md")
    problems = []
    if link not in read(os.path.join(dest, "docs", "acme", "events.md")):
        problems.append(f"{name}: the event page doesn't link session.id to {link}")
    if "# ACME" not in read(os.path.join(dest, "docs", "acme", "README.md")):
        problems.append(f"{name}: the acronym doesn't title the acme namespace")
    return problems


def workaround_still_needed(work):
    name = "workaround-still-needed"
    dest = project(work, name, ["attributes", "attribute-groups"], ATTRIBUTES)
    if not dest:
        return [f"{name}: render failed"]
    status, text = output(["make", "-C", dest, "generate-docs", "DOCS_DIR=.build/unexcluded",
                           "DOCS_PARAMS=--param exclude_root_namespace=[]"])
    if status != 0:
        return [f"{name}: generate-docs without the exclusion failed:\n{text}"]
    if not os.path.exists(os.path.join(dest, ".build", "unexcluded", "user-agent", "README.md")):
        return [f"{name}: without the exclusion, the shared templates no longer document the "
                "imported user_agent namespace: the docs-import-only exclusion can go"]
    return []


SCENARIOS = {"with-import": with_import, "events-only": events_only,
             "upstream-docs": upstream_docs, "workaround-still-needed": workaround_still_needed}


def main():
    args = work_dir(__doc__)
    problems = []
    for name in args.names or list(SCENARIOS):
        found = SCENARIOS[name](args.work)
        print(("ok" if not found else "FAILED") + f": scenario {name}")
        problems += found
    for problem in problems:
        print("SCENARIO PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
