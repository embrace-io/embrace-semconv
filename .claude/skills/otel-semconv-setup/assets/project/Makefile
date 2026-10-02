# Validation, generation and packaging for this project. The same targets run locally and in CI;
# `make help` lists them.
#
# Each part is a section from a `# ==== <name>` line (optionally followed by `: <description>`)
# to its `# ==== end <name>` line: `project`, `common` and `templates`, plus one for each feature
# and collection the project uses. A section's settings are at its top. Requires GNU make 3.81 or
# later (macOS ships 3.81), so every multi-line recipe runs in a single shell via backslash
# continuations.

# ==== project
.PHONY: all

# Default: validate, then regenerate everything this project owns.
all: @@ALL_PREREQUISITES@@
# ==== end project

# ==== common: tool pins and installation, the weaver runner
SHELL := /usr/bin/env bash

# The tool versions (and, with the registry section, the shared policy pack) are pinned in
# versions.env.
include versions.env

# Where the setup-* actions live: the repo root's .github/actions, found through git, so a project
# in a subdirectory of its repo needs no setting here. Their install scripts are shared with CI.
# Outside a git checkout it falls back to this directory's .github/actions. Set it by hand when
# the actions live elsewhere (a project inside a git submodule, say).
ACTIONS_DIR := $(or $(shell git rev-parse --show-toplevel 2>/dev/null),.)/.github/actions

# Extra flags for every weaver run, split on spaces. A registry that depends on, or compares with,
# a registry in a private repository needs --allow-git-credentials: without it, weaver's git
# operations can't use the machine's git credentials.
WEAVER_FLAGS :=
export WEAVER_FLAGS

.PHONY: test generate-all install-weaver require-weaver require-jq clean help

# Every test suite this project owns; each section adds its own. Used locally only, as CI runs the
# suites as separate jobs.
test::
	@:

# Every regeneration this project owns; each section adds its own. CI fails when the committed
# output doesn't match what this generates.
generate-all::
	@:

# Install the weaver version pinned in versions.env into ~/.local/bin.
install-weaver:
	WEAVER_VERSION=$(WEAVER_VERSION) bash "$(ACTIONS_DIR)/setup-weaver/install-weaver.sh"

# Fail if weaver is not on PATH; warn if it is not the version pinned in versions.env.
require-weaver:
	@command -v weaver >/dev/null 2>&1 || { \
	  echo "error: weaver not found on PATH. Run 'make install-weaver' to install the pinned" >&2; \
	  echo "version, or put a release binary from" >&2; \
	  echo "https://github.com/open-telemetry/weaver/releases on PATH." >&2; \
	  exit 1; \
	}
	@installed="$$(weaver --version | awk '{print $$2}')"; \
	if [[ "$$installed" != "$(WEAVER_VERSION:v%=%)" ]]; then \
	  echo "warning: weaver $$installed installed, but this project pins" >&2; \
	  echo "$(WEAVER_VERSION:v%=%) (see versions.env)." >&2; \
	fi

# Fail if jq is not on PATH. GitHub's runners have it preinstalled.
require-jq:
	@command -v jq >/dev/null 2>&1 || { \
	  echo "error: jq not found on PATH. Install it from https://jqlang.org/download/." >&2; \
	  exit 1; \
	}

# Remove build output only. Generated output that is committed is left alone.
clean:
	rm -rf .build

help::
	@echo "test                   run every test suite"
	@echo "generate-all           run every regeneration this project owns"
	@echo "install-weaver         install the weaver version pinned in versions.env"
	@echo "clean                  remove build output"

# Bash script every section runs weaver through, as `bash -c "$$RUN_WEAVER" run-weaver <name>
# <weaver arguments>`. It adds WEAVER_FLAGS, asks weaver for JSON diagnostics, keeps them in
# .build/<name>.json, prints them unwrapped (weaver wraps its text output to the terminal width,
# which breaks anything that reads it), and fails when weaver does or when any import matches
# nothing. Weaver only warns about the latter, and an import that matches nothing silently drops
# what the registry meant to include.
#
# When RUN_WEAVER_KNOWN_VIOLATIONS names a file (validate-registry sets it from KNOWN_VIOLATIONS),
# the policy violations it lists are accepted: weaver's failure is overridden when every failure is
# one of them, and a listed violation that no longer occurs is an error, so the list only shrinks.
define RUN_WEAVER
set -e
name="$$1"
shift
mkdir -p .build
out=".build/$$name.json"
status=0
# WEAVER_FLAGS holds zero or more flags, so it is split on spaces on purpose.
weaver "$$@" $$WEAVER_FLAGS --diagnostic-format json --diagnostic-stdout=true > "$$out" \
  || status=$$?
if ! jq -e 'type == "array"' "$$out" > /dev/null 2>&1; then
  if [[ $$status -ne 0 ]]; then exit $$status; fi
  echo "error: weaver's diagnostics in $$out are not a JSON array." >&2
  exit 1
fi
known_file="$${RUN_WEAVER_KNOWN_VIOLATIONS:-}"
known='[]'
if [[ -n "$$known_file" ]]; then
  if ! jq -e 'type == "array"' "$$known_file" > /dev/null 2>&1; then
    echo "error: $$known_file must be a JSON array of known policy violations." >&2
    exit 1
  fi
  known="$$(< "$$known_file")"
fi
jq -r --argjson known "$$known" --arg known_file "$$known_file" \
  "$$DIAGNOSTIC_DEFS $$PRINT_DIAGNOSTICS" "$$out" >&2
if [[ $$status -ne 0 ]]; then
  unknown="$$(jq --argjson known "$$known" "$$DIAGNOSTIC_DEFS $$UNKNOWN_FAILURES" "$$out")"
  if [[ -z "$$known_file" || "$$unknown" != 0 ]]; then exit $$status; fi
fi
if [[ -n "$$known_file" ]]; then
  stale="$$(jq -r --argjson known "$$known" "$$DIAGNOSTIC_DEFS $$STALE_KNOWN_VIOLATIONS" "$$out")"
  if [[ -n "$$stale" ]]; then
    echo "error: known violations in $$known_file that no longer occur:" >&2
    echo "$$stale" >&2
    echo "Remove them from $$known_file." >&2
    exit 1
  fi
fi
unmatched="$$(jq -r "$$UNMATCHED_IMPORTS" "$$out")"
if [[ -n "$$unmatched" ]]; then
  echo "error: imports that match nothing in any dependency:" >&2
  echo "$$unmatched" >&2
  echo "Each import must match something a direct dependency exports." >&2
  exit 1
fi
endef
export RUN_WEAVER

# jq definitions the programs below share, for weaver's JSON diagnostics. A failure is a policy
# violation at level `violation` or any other diagnostic of severity Error; a known violation is a
# policy violation whose id and context match an entry of $$known.
define DIAGNOSTIC_DEFS
def policy: (.error | objects | .type?) == "policy_violation";
def unstable: [.error | objects | .FailToResolveDefinition? | objects | .UnstableFileFormat?
  | select(. != null)] | length > 0;
def failure: if policy then .error.violation.level == "violation"
  else (.diagnostic.severity // "Error") == "Error" end;
def known: policy and (.error.violation as $$v
  | $$known | any(.id == $$v.id and .context == $$v.context));
endef
export DIAGNOSTIC_DEFS

# jq program for RUN_WEAVER: one line per diagnostic. Policy findings print their id and message;
# known violations collapse to one line, and so does the "definition/2 is not yet stable" warning
# weaver emits for every such file, the dependencies' included.
define PRINT_DIAGNOSTICS
([.[] | select(unstable)] | length) as $$unstable
| ([.[] | select(known)] | length) as $$accepted
| [.[] | select((unstable or known) | not)
    | if policy
      then "Policy \(.error.violation.level) [\(.error.violation.id)]: \(.error.violation.message)"
      else "\(.diagnostic.severity // "Error"): \(.diagnostic.message)"
        + (if .diagnostic.help then "\n  help: \(.diagnostic.help)" else "" end)
      end]
  + (if $$accepted > 0
     then ["Accepted \($$accepted) known policy violations listed in \($$known_file)."]
     else [] end)
  + (if $$unstable > 0
     then ["Warning: \($$unstable) definition files, the dependencies' included, use file_format "
           + "definition/2, which weaver still reports as not yet stable."]
     else [] end)
| .[]
endef
export PRINT_DIAGNOSTICS

# jq program for RUN_WEAVER: how many failures are not known violations.
define UNKNOWN_FAILURES
[.[] | select(failure and (known | not))] | length
endef
export UNKNOWN_FAILURES

# jq program for RUN_WEAVER: one line per known violation that weaver no longer reports.
define STALE_KNOWN_VIOLATIONS
[.[] | select(policy) | .error.violation | {id, context}] as $$found
| $$known[] | select(. as $$k | $$found | any(.id == $$k.id and .context == $$k.context) | not)
| "  \(.id) \(.context | tojson)"
endef
export STALE_KNOWN_VIOLATIONS

# jq program for RUN_WEAVER: one line per import that matched nothing.
define UNMATCHED_IMPORTS
.[] | .error | objects | .UnmatchedImport // empty | "  \(.signal): \(.pattern)"
endef
export UNMATCHED_IMPORTS
# ==== end common

# ==== templates: the template regression test
# The directory holding the templates, one subdirectory per target under registry/.
TEMPLATES := templates

# The template targets to test, i.e. the directories under $(TEMPLATES)/registry/. Set with `=`,
# not `:=`, so it can name a setting made further down (e.g. $(CODEGEN_TARGET)).
TEMPLATE_TARGETS = @@TEMPLATE_TARGETS@@

# The fixture registry the templates are rendered from. It is never published. It imports from a
# dependency so the provenance filters in the templates have something to filter out.
FIXTURE := templates_test/fixture

# The expected output, one subdirectory per template target.
GOLDEN := templates_test/golden

.PHONY: test-templates update-golden

# Render every template target from the fixture and compare with the golden files, so any change
# in template output (including definitions from a dependency leaking in) shows up as a diff. Run
# `make update-golden` after a deliberate change to the templates' output.
test-templates: require-weaver require-jq
	@set -e; \
	if [[ -z "$(strip $(TEMPLATE_TARGETS))" ]]; then \
	  echo "error: TEMPLATE_TARGETS is empty, so there is nothing to test." >&2; \
	  exit 1; \
	fi; \
	rm -rf .build/test-templates; \
	for target in $(TEMPLATE_TARGETS); do \
	  bash -c "$$RUN_WEAVER" run-weaver "test-templates-$$target" registry generate \
	    -r $(FIXTURE) --v2 --templates $(TEMPLATES) "$$target" ".build/test-templates/$$target"; \
	done
	@if ! git --no-pager diff --no-index --exit-code $(GOLDEN) .build/test-templates; then \
	  echo "" >&2; \
	  echo "error: the output rendered from the fixture does not match $(GOLDEN)/." >&2; \
	  echo "If the change is intended, refresh the golden files with:" >&2; \
	  echo "    make update-golden" >&2; \
	  exit 1; \
	fi
	@echo "templates OK: the fixture's output matches $(GOLDEN)/"

test:: test-templates
	@:

# Refresh the golden files after a template change that intentionally alters the output, then
# review the diff under $(GOLDEN)/ before committing it.
update-golden: require-weaver require-jq
	@set -e; \
	if [[ -z "$(strip $(TEMPLATE_TARGETS))" ]]; then \
	  echo "error: TEMPLATE_TARGETS is empty, so there is nothing to render." >&2; \
	  exit 1; \
	fi; \
	rm -rf $(GOLDEN); \
	for target in $(TEMPLATE_TARGETS); do \
	  bash -c "$$RUN_WEAVER" run-weaver "update-golden-$$target" registry generate \
	    -r $(FIXTURE) --v2 --templates $(TEMPLATES) "$$target" "$(GOLDEN)/$$target"; \
	done

help::
	@echo "test-templates         compare the templates' output from the fixture with the golden files"
	@echo "update-golden          refresh the golden files after an intended template change"
# ==== end templates

# ==== registry: a registry defined and validated in this project
# The registry directory. Its manifest.yaml sits directly inside it.
MODEL := model

# The registry directory's path within the repo, for the `[...]` part of the baseline's
# registry_path. It differs from MODEL only when the project lives in a subdirectory of its repo.
MODEL_REPO_PATH := $(MODEL)

# Registries whose dependency trees validate-dependencies verifies: the registry and the templates
# fixture.
REGISTRIES := $(MODEL) $(FIXTURE)

# This repo's canonical GitHub URL. The release artifacts' URLs and the baseline's release tags
# come from it. By default it is the origin remote's URL, so when origin isn't the canonical repo
# (a fork, or a contributor's fork as origin) set it to the canonical one. Origin is read from
# git's raw config, not with `git remote get-url`, which applies `insteadOf` rewrites and could
# return a URL with a token in it; any user info left in the URL is dropped.
REPO_URL := $(shell git config --get remote.origin.url 2>/dev/null | sed -E \
	-e 's|^git@github\.com:|https://github.com/|' -e 's|^(https?://)[^/@]*@|\1|' -e 's|\.git$$||')

# Invalid registries that test-validations expects a make target to fail on:
# validations_test/<target>/<case>/.
VALIDATION_CASES := $(patsubst %/expected-error.txt,%,\
	$(wildcard validations_test/*/*/expected-error.txt))

# The local policy directories validate-registry runs, besides the shared pack pinned in
# versions.env: registry-specific ones go here (with the attributes collection, its subsection
# adds the public-attribute-groups policy).
LOCAL_POLICIES :=

# The baseline validate-registry compares this registry with, to catch breaking changes:
# - `auto`: the highest vX.Y.Z release tag of REPO_URL. validate-registry fails if it can't list
#   REPO_URL's tags. Only for a registry released as this repo's vX.Y.Z tags.
# - a registry path, e.g. a git URL pinned to a tag or commit: for an unpublished registry, or one
#   in a repo whose v* tags belong to something else (an SDK's releases).
# - empty: no comparison.
BASELINE := @@BASELINE@@

# Shared policy pack violations this registry accepts, such as legacy keys that predate the
# naming rules and can't be renamed: a JSON array of {"id", "context", "reason"} entries, with id
# and context exactly as weaver reports them in .build/validate-registry.json. validate-registry
# still fails on any violation not listed, and on a listed one that no longer occurs, so the list
# only shrinks. Empty accepts none; by convention the file is known-violations.json, here.
KNOWN_VIOLATIONS :=

.PHONY: validate-registry validate-dependencies test-validations

# Validate the registry: its resolved dependency trees (validate-dependencies, run first), then the
# schema, then the shared OpenTelemetry policy pack (naming conventions, attribute type rules,
# stability requirements, backwards compatibility) plus the local policies. Needs network access
# to fetch the dependencies pinned in the registry's manifest and the policy pack pinned in
# versions.env.
#
# A policy that loads but never runs (e.g. its `package` names no stage weaver runs) or no longer
# matches weaver's input passes silently, so validations_test/validate-registry/ holds an invalid
# registry for each policy set, which this target must fail on.
#
# The shared pack's backwards-compatibility policies only run against a baseline (see BASELINE):
# compared with the last release, no attribute or signal may be removed and nothing stable may
# change incompatibly. Before the first release there is no baseline, so they're skipped, and
# pre-release tags (e.g. v0.4.0-dev) are never baselines. KNOWN_VIOLATIONS lists the violations
# the registry accepts.
validate-registry: require-weaver require-jq validate-dependencies
	@set -e; \
	baseline="$(BASELINE)"; \
	if [[ "$$baseline" == auto ]]; then \
	  if ! tags="$$(git ls-remote --tags --refs "$(REPO_URL)" 'v*')"; then \
	    echo "error: could not list the release tags of '$(REPO_URL)' (REPO_URL) to find" >&2; \
	    echo "the baseline. A private repo needs git credentials, in CI too; a fork sets" >&2; \
	    echo "REPO_URL to the repo it was forked from; a repo not yet on GitHub runs" >&2; \
	    echo "'make validate-registry BASELINE=' until it is. Otherwise set BASELINE to a" >&2; \
	    echo "registry path, or empty." >&2; \
	    exit 1; \
	  fi; \
	  tag="$$(awk "$$LATEST_RELEASE_TAG" <<< "$$tags")"; \
	  baseline="$${tag:+$(REPO_URL)@$$tag[$(MODEL_REPO_PATH)]}"; \
	fi; \
	baseline_args=(); \
	if [[ -n "$$baseline" ]]; then \
	  echo "Comparing against the baseline $$baseline"; \
	  baseline_args=(--baseline-registry "$$baseline"); \
	elif [[ "$(BASELINE)" == auto ]]; then \
	  echo "No baseline: $(REPO_URL) has no vX.Y.Z release tag yet, so the"; \
	  echo "backwards-compatibility policies are skipped."; \
	else \
	  echo "No baseline: BASELINE is empty, so the backwards-compatibility policies are skipped."; \
	fi; \
	RUN_WEAVER_KNOWN_VIOLATIONS="$(KNOWN_VIOLATIONS)" \
	bash -c "$$RUN_WEAVER" run-weaver validate-registry registry check \
	  -r $(MODEL) \
	  --v2 \
	  --policy "$(POLICY_REPO_URL)@$(POLICY_REPO_REF)[policies/check]" \
	  $(foreach policy,$(LOCAL_POLICIES),--policy $(policy)) \
	  "$${baseline_args[@]}"

# Verify the dependency tree weaver actually resolves for each of REGISTRIES, rather than what their
# manifests declare. The resolved registry that `weaver registry package` writes lists every
# registry in the tree, each under the schema_url in its own manifest. Two things must hold there:
# - No registry is in the tree at more than one version. When two registries request different
#   versions of one (e.g. this registry and one of its dependencies both depend on the core
#   registry), weaver uses the highest, so some registry runs against a version it was not
#   validated with. Weaver warns only when the dropped version is the one the root requested.
# - Every schema_url a manifest declares is in the tree. A dependency's registry_path is what
#   weaver fetches, and weaver keys the registry by the declared schema_url without checking it
#   against the fetched registry's own. A schema_url naming another version or registry (a typo in
#   its path included: `opentelemetry.io/cool-schemas` is not `opentelemetry.io/schemas`) would
#   otherwise pass, at most with a warning, along with any version conflict it hides.
# The invalid registries under validations_test/validate-dependencies/ break each rule, and
# `make test-validations` confirms this target fails on them.
validate-dependencies: require-weaver require-jq
	@set -e; \
	rm -rf .build/dependencies; \
	mkdir -p .build/dependencies; \
	touch .build/dependencies/problems.txt; \
	for registry in $(REGISTRIES); do \
	  out=".build/dependencies/$$registry"; \
	  mkdir -p "$$out"; \
	  if ! bash -c "$$RUN_WEAVER" run-weaver "dependencies/$$registry/weaver" registry package \
	      -r "$$registry" --v2 --skip-policies --resolved-registry-uri unused -o "$$out"; then \
	    echo "error: weaver could not resolve $$registry (see above)." >&2; \
	    exit 1; \
	  fi; \
	  awk -v registry="$$registry" "$$DEPENDENCY_PROBLEMS" \
	    "$$out/manifest.yaml" "$$out/resolved.yaml" >> .build/dependencies/problems.txt; \
	done; \
	if [[ -s .build/dependencies/problems.txt ]]; then \
	  echo "error: the resolved dependency trees do not match the manifests:" >&2; \
	  cat .build/dependencies/problems.txt >&2; \
	  echo "Make every registry in a tree request the same version of each dependency, and keep" >&2; \
	  echo "each schema_url naming the registry and version that its registry_path fetches." >&2; \
	  exit 1; \
	fi

# Regression test for the validations themselves: the make targets that fail on an invalid
# registry. Each case under validations_test/<target>/ is a registry that is invalid in one way,
# and `make <target>` must fail on it with an error containing the text in its
# expected-error.txt, so a validation that stops failing, or fails for another reason, shows up
# here. The case is passed as MODEL, FIXTURE and REGISTRIES, so it is the registry whichever
# target runs reads. BASELINE is empty unless the case has a baseline.txt naming a baseline
# registry, and KNOWN_VIOLATIONS is empty unless the case has a known-violations.json.
# validations_test/registries/ holds dependencies and baselines that cases share, and is not a
# case itself. Needs network access.
test-validations: require-weaver
	@set -e; \
	if [[ -z "$(VALIDATION_CASES)" ]]; then \
	  echo "error: no cases found under validations_test/." >&2; \
	  exit 1; \
	fi; \
	mkdir -p .build; \
	for case in $(VALIDATION_CASES); do \
	  target="$${case#validations_test/}"; \
	  target="$${target%%/*}"; \
	  baseline=""; \
	  if [[ -f "$$case/baseline.txt" ]]; then baseline="$$(< "$$case/baseline.txt")"; fi; \
	  known=""; \
	  if [[ -f "$$case/known-violations.json" ]]; then known="$$case/known-violations.json"; fi; \
	  if $(MAKE) --no-print-directory "$$target" MODEL="$$case" FIXTURE="$$case" \
	      REGISTRIES="$$case" BASELINE="$$baseline" KNOWN_VIOLATIONS="$$known" \
	      > .build/test-validations.log 2>&1; then \
	    echo "error: make $$target passed on the invalid registry $$case." >&2; \
	    exit 1; \
	  fi; \
	  if ! grep -qF -f "$$case/expected-error.txt" .build/test-validations.log; then \
	    cat .build/test-validations.log >&2; \
	    echo "error: make $$target failed on $$case, but without the error in" >&2; \
	    echo "$$case/expected-error.txt." >&2; \
	    exit 1; \
	  fi; \
	  echo "ok: make $$target fails on $$case"; \
	done

test:: test-validations
	@:

help::
	@echo "validate-registry      validate the registry (dependencies + schema + policies)"
	@echo "validate-dependencies  verify the resolved dependency trees match the manifests"
	@echo "test-validations       confirm validation fails on each registry in validations_test/"

# awk program for validate-dependencies. Reads the manifest.yaml and resolved.yaml that
# `weaver registry package` wrote for one registry (named by -v registry) and prints one line per
# problem. Both files are weaver's own output, so their layout does not depend on how the source
# manifest was written. A registry's name is its schema_url minus the scheme and the last segment.
define DEPENDENCY_PROBLEMS
FNR == 1 { in_dependencies = 0 }
FILENAME ~ /manifest\.yaml$$/ && /^- schema_url:/ { declared[$$3] = 1; declared_count++; next }
FILENAME ~ /resolved\.yaml$$/ && /^dependencies:/ { in_dependencies = 1; next }
FILENAME ~ /resolved\.yaml$$/ && in_dependencies && /^- / { loaded[$$2] = 1; loaded_count++; next }
FILENAME ~ /resolved\.yaml$$/ { in_dependencies = 0 }
END {
  # Fail rather than pass vacuously if weaver's output stops matching the patterns above.
  if (loaded_count > 0 && declared_count == 0) {
    print "  " registry ": no declared dependencies found in weaver's package output"
  }
  for (url in loaded) {
    name = registry_name(url)
    versions[name] = (name in versions) ? versions[name] ", " url_version(url) : url_version(url)
    count[name]++
  }
  for (name in count) {
    if (count[name] > 1) {
      print "  " registry ": " name " is in the dependency tree at more than one version: " \
        versions[name]
    }
  }
  for (url in declared) {
    if (!(url in loaded)) {
      print "  " registry ": declares " url \
        ", but no registry in its dependency tree identifies as that"
    }
  }
}
function registry_name(url) { sub(/^[^:]*:\/\//, "", url); sub(/\/[^\/]*$$/, "", url); return url }
function url_version(url) { sub(/^.*\//, "", url); return url }
endef
export DEPENDENCY_PROBLEMS

# awk program for validate-registry: reads `git ls-remote --tags --refs` output and prints the
# highest vX.Y.Z tag. Tags with a pre-release or build suffix are not baselines.
define LATEST_RELEASE_TAG
{ tag = $$2; sub(/^refs\/tags\//, "", tag) }
tag ~ /^v[0-9]+\.[0-9]+\.[0-9]+$$/ {
  split(substr(tag, 2), part, ".")
  key = sprintf("%09d%09d%09d", part[1], part[2], part[3])
  if (key > best_key) { best_key = key; best = tag }
}
END { if (best != "") print best }
endef
export LATEST_RELEASE_TAG
# ==== attributes: the local policy for a registry that defines attributes, and its unit tests

# Every attribute the registry defines must be exported by one of its public attribute groups.
LOCAL_POLICIES += policies/check/public-attribute-groups

# The rego policies and their unit tests, for test-policies.
POLICIES_DIR := policies
POLICY_TESTS_DIR := policies_test

.PHONY: test-policies install-opa require-opa

# Unit-test the local rego policies against their tests. Pure OPA: no weaver, no network. The
# cases worth covering involve definitions inherited from a dependency, which a registry without an
# `imports` block never produces.
#
# `opa test` passes when it finds no tests at all, so a second run requires the tests to cover
# every line of rego, which fails for a missing or unloaded test file as well as for an untested
# rule. The coverage is compared here rather than with `--threshold`, as opa writes no report
# (and so no uncovered lines) when the threshold is missed.
test-policies: require-opa require-jq
	opa test --explain fails $(POLICIES_DIR) $(POLICY_TESTS_DIR)
	@mkdir -p .build
	@opa test --coverage --format json $(POLICIES_DIR) $(POLICY_TESTS_DIR) > .build/opa-coverage.json
	@if ! jq -e '.coverage == 100' .build/opa-coverage.json > /dev/null; then \
	  echo "error: the tests in $(POLICY_TESTS_DIR)/ must run every line of rego." >&2; \
	  echo "Lines none runs:" >&2; \
	  jq -r "$$UNCOVERED_POLICY_LINES" .build/opa-coverage.json >&2; \
	  exit 1; \
	fi

test:: test-policies
	@:

# Install the OPA version pinned in versions.env into ~/.local/bin.
install-opa:
	OPA_VERSION=$(OPA_VERSION) bash "$(ACTIONS_DIR)/setup-opa/install-opa.sh"

# Fail if opa is not on PATH; warn if it is not the version pinned in versions.env.
require-opa:
	@command -v opa >/dev/null 2>&1 || { \
	  echo "error: opa not found on PATH. Run 'make install-opa' to install the pinned version." >&2; \
	  exit 1; \
	}
	@installed="$$(opa version | awk '/^Version:/ { print $$2 }')"; \
	if [[ "$$installed" != "$(OPA_VERSION:v%=%)" ]]; then \
	  echo "warning: opa $$installed installed, but this project pins" >&2; \
	  echo "$(OPA_VERSION:v%=%) (see versions.env)." >&2; \
	fi

help::
	@echo "test-policies          unit-test the local rego policies"
	@echo "install-opa            install the OPA version pinned in versions.env"

# jq program for test-policies: the lines of each rego file that no test runs, from the coverage
# report of `opa test --coverage`.
define UNCOVERED_POLICY_LINES
.files // {} | to_entries[] | select(.value.not_covered) |
  "  \(.key): lines \([.value.not_covered[].start.row] | unique | map(tostring) | join(", "))"
endef
export UNCOVERED_POLICY_LINES
# ==== end attributes
# ==== end registry

# ==== docs: markdown docs for the conventions the registry defines, generated and committed
# Where the generated docs are written. Everything in it is replaced on each run, so it must hold
# only generated files.
DOCS_DIR := docs

.PHONY: generate-docs

# Regenerate the committed markdown under $(DOCS_DIR)/ from the registry. Needs network access. CI
# fails when the committed docs don't match what this generates, so run this before submitting
# registry or template changes and commit the result.
generate-docs: require-weaver require-jq
	@set -e; \
	if [[ -z "$(DOCS_DIR)" || "$(DOCS_DIR)" == . || "$(DOCS_DIR)" == / ]]; then \
	  echo "error: DOCS_DIR must name a directory that holds only generated docs." >&2; \
	  exit 1; \
	fi; \
	rm -rf $(DOCS_DIR); \
	bash -c "$$RUN_WEAVER" run-weaver generate-docs registry generate \
	  -r $(MODEL) --v2 --templates $(TEMPLATES) markdown $(DOCS_DIR)

generate-all:: generate-docs
	@:

help::
	@echo "generate-docs          regenerate the committed markdown under $(DOCS_DIR)/"
# ==== end docs

# ==== release: OTEP 4815 publication artifacts for a registry released as GitHub releases
# A pre-release suffix every version must end with, e.g. `-dev` for a registry that only ever
# publishes pre-releases (a `-dev` family): print-version, and so the Release workflow, refuses a
# version without it. Empty allows any SemVer version.
VERSION_SUFFIX :=

.PHONY: print-version package

# Print the registry's version: the last segment of the schema_url in $(MODEL)/manifest.yaml. Fails
# unless that is a SemVer version ending with VERSION_SUFFIX, so a schema_url it cannot parse, or a
# version the registry must never publish, never reaches a package or a release tag. The Release
# workflow reads the version from here too.
print-version:
	@version="$$(awk '/^schema_url:/ { n = split($$2, parts, "/"); print parts[n]; exit }' \
	  $(MODEL)/manifest.yaml)"; \
	semver='^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$$'; \
	if [[ ! "$$version" =~ $$semver ]]; then \
	  echo "error: no SemVer version at the end of the schema_url in $(MODEL)/manifest.yaml" >&2; \
	  echo "(read '$$version')." >&2; \
	  exit 1; \
	fi; \
	suffix='$(VERSION_SUFFIX)'; \
	if [[ -n "$$suffix" && "$$version" != *"$$suffix" ]]; then \
	  echo "error: version $$version doesn't end with '$$suffix' (VERSION_SUFFIX), and every" >&2; \
	  echo "version of this registry must." >&2; \
	  exit 1; \
	fi; \
	echo "$$version"

# Produce the publication manifest and resolved registry under .build/package/. The resolved-
# registry URI baked into the artifacts points at the version's GitHub release (see print-version),
# which is where consumers fetch it from.
package: require-weaver require-jq
	@set -eu; \
	if [[ ! "$(REPO_URL)" =~ ^https://[^/@]+/[^/@]+/[^/@]+$$ ]]; then \
	  echo "error: REPO_URL ('$(REPO_URL)') must be https://<host>/<owner>/<repo>, with no" >&2; \
	  echo "credentials in it: it is published in the release's manifest.yaml." >&2; \
	  exit 1; \
	fi; \
	version="$$($(MAKE) --no-print-directory -s print-version)"; \
	rm -rf .build/package; \
	bash -c "$$RUN_WEAVER" run-weaver package registry package \
	  -r $(MODEL) \
	  --v2 \
	  --resolved-registry-uri "$(REPO_URL)/releases/download/v$$version/resolved.yaml" \
	  -o .build/package; \
	echo "packaged version $$version -> .build/package"

help::
	@echo "print-version          print the version at the end of the registry's schema_url"
	@echo "package                produce the publication artifacts under .build/package/"
# ==== end release

# ==== codegen: @@LANGUAGE@@ source code generated from a registry with this project's templates
# The registry the code is generated from: a remote registry pinned to a release, e.g. the core
# registry alone with https://github.com/open-telemetry/semantic-conventions@v1.44.0[model], or
# this project's own registry ($(MODEL), with the registry section) when it defines conventions or
# combines several registries. With Renovate, a pinned release gets a `# renovate: datasource=github-tags
# depName=<owner>/<repo> versioning=semver-coerced` line directly above it.
SOURCE_REGISTRY := @@SOURCE_REGISTRY@@

# The template target under $(TEMPLATES)/registry/ to generate with.
CODEGEN_TARGET := @@CODEGEN_TARGET@@

# Where the generated code is written. It is emptied on every run, so it must hold only generated
# files: render any hand-written file that has to live there from a template of its own.
GENERATED_DIR := @@GENERATED_DIR@@

.PHONY: generate validate-generated package-generated

# Regenerate $(GENERATED_DIR)/ from $(SOURCE_REGISTRY). Needs network access for remote registries
# and dependencies. If the generated code is committed, this is its only generator, and CI fails
# when the committed code doesn't match what this generates. If a build tool generates the code at
# build time instead, it stays the generator: GENERATED_DIR then points under .build/, and
# validate-generated compares this output with the build tool's.
generate: require-weaver require-jq
	@set -e; \
	if [[ -z "$(GENERATED_DIR)" || "$(GENERATED_DIR)" == . || "$(GENERATED_DIR)" == / ]]; then \
	  echo "error: GENERATED_DIR must name a directory that holds only generated code." >&2; \
	  exit 1; \
	fi; \
	rm -rf $(GENERATED_DIR); \
	bash -c "$$RUN_WEAVER" run-weaver generate registry generate \
	  -r "$(SOURCE_REGISTRY)" --v2 --templates $(TEMPLATES) $(CODEGEN_TARGET) $(GENERATED_DIR)

generate-all:: generate
	@:

# Platform-specific, so implemented per project: prove the generated code is valid for
# @@LANGUAGE@@ (compile, type-check, lint, or run a test that uses it).
validate-generated: generate
	@echo "error: validate-generated is not implemented for this project yet." >&2; exit 1

test:: validate-generated
	@:

# Platform-specific, so implemented per project: build what consumers of the generated code
# install, under .build/package-generated/. When the code ships inside a package the project
# already builds, build that package here, or print why there is nothing extra to build.
package-generated: validate-generated
	@echo "error: package-generated is not implemented for this project yet." >&2; exit 1

help::
	@echo "generate               regenerate $(GENERATED_DIR)/ from $(SOURCE_REGISTRY)"
	@echo "validate-generated     validate the generated code for its platform"
	@echo "package-generated      build the package consumers of the generated code install"
# ==== end codegen
