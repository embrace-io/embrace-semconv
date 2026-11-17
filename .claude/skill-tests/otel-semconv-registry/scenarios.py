"""Set up registry projects on the base layout, add a registry to each, and run every make target.

Usage: scenarios.py [SCENARIO ...] [--work DIR]
Needs weaver at the pinned version, jq, opa, git, GNU make and network access (weaver fetches the
core registry and the shared policy pack). Each scenario renders the base's core, adds the
registry part with its collections and local policy choice, writes a registry, and runs
validate-registry and the tests.
"""
import os
import sys

from _registry import output, read, render_project, run, work_dir

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
"""
# A policy of the registry's own, as SKILL.md step 3 has it: its directory in LOCAL_POLICIES, unit
# tests covering every line, and an invalid registry only it rejects.
OWN_POLICY = {
    "policies/check/acme-no-tmp/acme_no_tmp.rego": """package after_resolution

import rego.v1

deny contains finding if {
	some attr in object.get(input, ["registry", "attributes"], [])
	contains(attr.key, ".tmp")
	finding := {
		"id": "acme_tmp_key",
		"context": {"attribute_key": attr.key},
		"message": sprintf("Attribute '%s' is a temporary key.", [attr.key]),
		"level": "violation",
	}
}
""",
    "policies_test/acme_no_tmp_test.rego": """package after_resolution

import rego.v1

test_rejects_a_tmp_key if {
	count(deny) == 1 with input as {"registry": {"attributes": [{"key": "acme.tmp.id"}]}}
}

test_accepts_other_keys if {
	count(deny) == 0 with input as {"registry": {"attributes": [{"key": "acme.tenant.id"}]}}
}
""",
    "validations_test/validate-registry/own-policy-rejects-tmp-key/manifest.yaml":
        """schema_url: https://example.com/schemas/validations-test-case/0.0.0-dev
description: Case with an attribute that only the registry's own policy rejects.
stability: development
""",
    "validations_test/validate-registry/own-policy-rejects-tmp-key/registry.yaml":
        """file_format: definition/2

attributes:
  - key: acme.tmp.id
    type: string
    stability: development
    brief: A temporary key.
    examples: ["x"]
""",
    "validations_test/validate-registry/own-policy-rejects-tmp-key/expected-error.txt":
        "Attribute 'acme.tmp.id' is a temporary key.\n",
}

# name -> (collections, the registry's definitions, with the base's templates part?, local
# policies: "none", "own" or "public-groups")
MODELS = {
    # acme.refund sets no requirement_level, which weaver still accepts (with a warning).
    "events-only": (["events"], """events:
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
""", False, "none"),
    "groups-only": (["attribute-groups"], """attribute_groups:
  - id: registry.acme.session
    visibility: public
    stability: development
    brief: The session attributes Acme records.
    attributes:
      - ref: session.id
""", False, "none"),
    # Attributes in no group, as in a registry whose consumers take attributes from the registry
    # itself: valid without the public-groups policy.
    "attributes-only": (["attributes"], """attributes:
  - key: acme.tenant.id
    type: string
    stability: development
    brief: Identifier of the tenant the telemetry belongs to.
    examples: ["t-123"]
""", False, "none"),
    "attributes-and-groups": (["attributes", "attribute-groups"], ATTRIBUTES, False,
                              "public-groups"),
    # A policy of the registry's own, with the policies section but not public-groups.
    "own-policy": (["attributes", "attribute-groups"], ATTRIBUTES, False, "own"),
    # With the base's templates part: the fixture's dependency tree is verified too, and the
    # template test's case is copied and run.
    "with-templates": (["attributes", "attribute-groups", "events"], ATTRIBUTES + """
events:
  - name: acme.checkout
    requirement_level: recommended
    stability: development
    brief: A checkout completed.
    attributes:
      - ref: acme.tenant.id
        requirement_level: recommended
""", True, "public-groups"),
    # Every field weaver lets a definition leave out, left out.
    "minimal-fields": (["attributes", "attribute-groups", "events", "metrics", "spans",
                        "entities"], """attributes:
  - key: acme.name
    type: string
    stability: development
    brief: A name.
    examples: a
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
""", False, "public-groups"),
}


def add_own_policy(dest):
    """Write the registry's own policy and list it in LOCAL_POLICIES, as an agent would."""
    for rel, text in OWN_POLICY.items():
        path = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    makefile = os.path.join(dest, "Makefile")
    text = read(makefile)
    if "\nLOCAL_POLICIES :=\n" not in text:
        raise SystemExit("the registry section has no empty LOCAL_POLICIES to set")
    with open(makefile, "w", encoding="utf-8") as f:
        f.write(text.replace("\nLOCAL_POLICIES :=\n",
                             "\nLOCAL_POLICIES := policies/check/acme-no-tmp\n", 1))


def scenario(work, name):
    collections, model, templates, policies = MODELS[name]
    dest = os.path.join(work, "registry", name)
    problems = []
    if not render_project(work, name, dest, collections, templates=templates,
                          policies=policies):
        return [f"{name}: render failed"]
    os.makedirs(os.path.join(dest, "model", "acme"))
    with open(os.path.join(dest, "model", "acme", "registry.yaml"), "w") as f:
        f.write("file_format: definition/2\n\n" + model)
    if policies == "own":
        add_own_policy(dest)
    with_policies = policies != "none"
    status, text = output(["make", "-C", dest, "help"])
    wanted = ["validate-registry", "validate-dependencies", "test-validations"]
    if not all(t in text for t in wanted):
        problems.append(f"{name}: make help lacks a registry target:\n{text}")
    if with_policies != all(t in text for t in ("test-policies", "install-opa")):
        problems.append(f"{name}: make help's policy targets don't match {policies}:\n{text}")
    opa_action = os.path.exists(os.path.join(dest, ".github", "actions", "setup-opa"))
    if opa_action != with_policies:
        problems.append(f"{name}: setup-opa is {'' if opa_action else 'not '}there")
    public_groups = policies == "public-groups"
    if public_groups != os.path.exists(os.path.join(dest, "policies", "check",
                                                    "public-attribute-groups")):
        problems.append(f"{name}: the public-attribute-groups policy doesn't match {policies}")
    if public_groups != ("policies/check/public-attribute-groups" in read(
            os.path.join(dest, "Makefile"))):
        problems.append(f"{name}: LOCAL_POLICIES doesn't match {policies}")
    workflow = read(os.path.join(dest, ".github", "workflows", "ci-validation.yaml"))
    for job, wanted_job in (("validate-registry", True), ("test-validations", True),
                            ("test-policies", with_policies),
                            ("test-templates", templates)):
        has = f"  {job}:" in workflow and f"- {job} # " in workflow
        if has != wanted_job:
            problems.append(f"{name}: the CI workflow {'lacks' if wanted_job else 'has'} {job}")
    targets = (["update-golden"] if templates else []) + ["validate-registry", "test", ""]
    for target in targets:
        if not run(work, f"{name}-{target or 'all'}", ["make", target] if target else ["make"],
                   cwd=dest):
            problems.append(f"{name}: make {target or '(all)'} failed")
    log = read(os.path.join(work, "logs", f"{name}-test.log")) if os.path.exists(
        os.path.join(work, "logs", f"{name}-test.log")) else ""
    if templates and "ok: make test-templates fails on" not in log:
        problems.append(f"{name}: test-validations didn't run the template test's case")
    for case, wanted_case in (("local-policy-rejects-unexported-attribute", public_groups),
                              ("own-policy-rejects-tmp-key", policies == "own")):
        if (f"fails on validations_test/validate-registry/{case}" in log) != wanted_case:
            problems.append(f"{name}: test-validations {'never ran' if wanted_case else 'ran'} "
                            f"{case}")
    return problems


def main():
    args = work_dir(__doc__)
    problems = []
    for name in args.names or list(MODELS):
        found = scenario(args.work, name)
        print(("ok" if not found else "FAILED") + f": scenario {name}")
        problems += found
    for problem in problems:
        print("SCENARIO PROBLEM: " + problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
