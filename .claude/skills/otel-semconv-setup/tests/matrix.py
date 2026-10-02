"""Render registries with different collections, add a model to each, and run every make target.

Usage: matrix.py [SCENARIO ...] [--work DIR]
Prints one ok/FAILED line per step and exits non-zero on the first failure. Needs weaver, jq, opa
and network access (weaver fetches the core registry). `private-all` is render-only: it keeps the
workflows' private sections so parse_workflows.py can check them.
"""
import os
import shutil
import subprocess
import sys

from _common import FIXTURES, RENDER, run, work_dir

TOKENS = os.path.join(FIXTURES, "tokens")
MODELS = {
    # acme.refund sets no requirement_level, which weaver still accepts (with a warning): the
    # docs templates must render it.
    "events-only": ("events", """file_format: definition/2

events:
  - name: acme.checkout
    requirement_level: recommended
    stability: development
    brief: A checkout completed.
    attributes:
      - ref: session.id
        requirement_level: recommended
  - name: acme.refund
    stability: development
    brief: A refund was issued.
    attributes:
      - ref: session.id
"""),
    "groups-only": ("attribute-groups", """file_format: definition/2

attribute_groups:
  - id: registry.acme.session
    visibility: public
    stability: development
    brief: The session attributes Acme records.
    attributes:
      - ref: session.id
"""),
    "attributes-and-groups": ("attributes,attribute-groups", """file_format: definition/2

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
"""),
    "all-collections": ("attributes,attribute-groups,events,metrics,spans,entities",
                        """file_format: definition/2

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

events:
  - name: acme.checkout
    requirement_level: recommended
    stability: development
    brief: A checkout completed.
    attributes:
      - ref: acme.tenant.id
        requirement_level: recommended
"""),
    # Every field weaver lets a definition leave out, left out (or in its less common form), so
    # the docs templates must render valid definitions that set only what weaver requires:
    # single-value examples of each type, none at all, enum members without brief or stability,
    # signals without requirement_level, note or attributes, a group without attributes.
    "minimal-fields": ("attributes,attribute-groups,events,metrics,spans,entities",
                       """file_format: definition/2

attributes:
  - key: acme.name
    type: string
    stability: development
    brief: A name.
    examples: a
  - key: acme.count
    type: int
    stability: development
    brief: A count.
    examples: 3
  - key: acme.enabled
    type: boolean
    stability: development
    brief: Whether it is enabled.
    examples: true
  - key: acme.ratio
    type: double
    stability: development
    brief: A ratio, with no examples.
  - key: acme.mode
    type:
      members:
        - id: fast
          value: "fast"
    stability: development
    brief: A mode whose member sets neither brief nor stability.
  - key: acme.old_name
    type: string
    stability: development
    brief: Renamed without a note.
    deprecated:
      reason: renamed
      renamed_to: acme.name

attribute_groups:
  - id: registry.acme
    visibility: public
    stability: development
    brief: The acme attributes.
    attributes:
      - ref: acme.name
      - ref: acme.count
      - ref: acme.enabled
      - ref: acme.ratio
      - ref: acme.mode
      - ref: acme.old_name
  - id: registry.acme.empty
    visibility: public
    stability: development
    brief: A group with no attributes.

events:
  - name: acme.started
    stability: development
    brief: Started, with no requirement level or attributes.

metrics:
  - name: acme.count
    instrument: counter
    unit: "1"
    stability: development
    brief: A count, with no requirement level or attributes.

spans:
  - type: acme.work
    kind: internal
    name:
      note: The work's name.
    stability: development
    brief: Work, with no requirement level or attributes.

entities:
  - type: acme.host
    stability: development
    brief: A host, with no requirement level.
    identity:
      - ref: acme.name
"""),
}
RENDER_ONLY = {
    "private-all": ("registry,docs,release,codegen,private,attributes,attribute-groups",
                    "private-all.json"),
}
SCENARIOS = list(MODELS) + list(RENDER_ONLY) + ["dev-family"]
EXPECTED_URI = ("resolved_registry_uri: https://github.com/acme/acme-semconv/releases/"
                "download/v0.1.0-dev/resolved.yaml")


def check_markdown(name, dest):
    """Every generated markdown file ends with exactly one newline and has no double blank line."""
    problems = []
    for top in ("docs", os.path.join("templates_test", "golden")):
        for dirpath, _, names in os.walk(os.path.join(dest, top)):
            for fname in names:
                if not fname.endswith(".md"):
                    continue
                path = os.path.join(dirpath, fname)
                with open(path) as f:
                    text = f.read()
                rel = os.path.relpath(path, dest)
                if not text.endswith("\n") or text.endswith("\n\n"):
                    problems.append(f"{rel}: does not end with exactly one newline")
                if "\n\n\n" in text:
                    problems.append(f"{rel}: has a double blank line")
    for problem in problems:
        print("MARKDOWN PROBLEM: " + problem)
    print(("ok" if not problems else "FAILED") + f": {name}-markdown")
    return not problems


def fresh_repo(dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    subprocess.run(["git", "init", "-q", dest], check=True)
    subprocess.run(["git", "-C", dest, "remote", "add", "origin",
                    "git@github.com:acme/acme-semconv.git"], check=True)


def dev_family(work, dest):
    """A -dev family: with VERSION_SUFFIX := -dev, print-version (which the Release workflow
    reads) accepts 0.1.0-dev and refuses 0.1.0."""
    if not run(work, "dev-family-render",
               [sys.executable, RENDER, dest, "registry,release,attributes,attribute-groups",
                os.path.join(TOKENS, "acme.json")]):
        return False
    makefile = os.path.join(dest, "Makefile")
    with open(makefile) as f:
        text = f.read()
    with open(makefile, "w") as f:
        f.write(text.replace("\nVERSION_SUFFIX :=\n", "\nVERSION_SUFFIX := -dev\n", 1))
    accepted = subprocess.run(["make", "-s", "print-version"], cwd=dest, capture_output=True,
                              text=True)
    ok = accepted.returncode == 0 and accepted.stdout.strip() == "0.1.0-dev"
    print(("ok" if ok else "FAILED") + f": dev-family accepts 0.1.0-dev ({accepted.stdout.strip()})")
    manifest = os.path.join(dest, "model", "manifest.yaml")
    with open(manifest) as f:
        text = f.read()
    with open(manifest, "w") as f:
        f.write(text.replace("/acme/0.1.0-dev", "/acme/0.1.0", 1))
    refused = subprocess.run(["make", "-s", "print-version"], cwd=dest, capture_output=True,
                             text=True)
    refused_ok = refused.returncode != 0 and "VERSION_SUFFIX" in refused.stderr
    print(("ok" if refused_ok else "FAILED") + ": dev-family refuses 0.1.0")
    return ok and refused_ok


def scenario(work, name):
    dest = os.path.join(work, "matrix", name)
    fresh_repo(dest)
    if name == "dev-family":
        return dev_family(work, dest)
    if name in RENDER_ONLY:
        chosen, tokens = RENDER_ONLY[name]
        return run(work, f"{name}-render",
                   [sys.executable, RENDER, dest, chosen, os.path.join(TOKENS, tokens)])
    collections, model = MODELS[name]
    if name == "all-collections":
        # A CI credential pattern that puts a token in git's view of the URL: REPO_URL, and so the
        # published resolved_registry_uri, must not pick it up.
        subprocess.run(["git", "-C", dest, "config",
                        "url.https://x-access-token:FAKE@github.com/acme/acme-semconv.insteadOf",
                        "git@github.com:acme/acme-semconv"], check=True)
    if not run(work, f"{name}-render", [sys.executable, RENDER, dest,
                                        "registry,docs,release,renovate," + collections,
                                        os.path.join(TOKENS, "acme.json")]):
        return False
    os.makedirs(os.path.join(dest, "model", "acme"))
    with open(os.path.join(dest, "model", "acme", "registry.yaml"), "w") as f:
        f.write(model)
    for target in ["update-golden", "validate-registry", "generate-all", "test", "package"]:
        if not run(work, f"{name}-{target}", ["make", target], cwd=dest):
            return False
    if not check_markdown(name, dest):
        return False
    with open(os.path.join(dest, ".build", "package", "manifest.yaml")) as f:
        uri = [l for l in f.read().splitlines() if l.startswith("resolved_registry_uri:")][0]
    print(("ok" if uri == EXPECTED_URI else "FAILED") + f": {name}-resolved-uri ({uri})")
    return uri == EXPECTED_URI


def main():
    args = work_dir(__doc__)
    for name in args.names or SCENARIOS:
        if not scenario(args.work, name):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
