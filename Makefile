# Validation, docs generation and packaging for this registry. The same targets
# are run locally and in CI.

SHELL := /usr/bin/env bash

# Weaver and OPA versions, and the shared policy pack, are pinned in versions.env
include versions.env

# The registry this repo publishes, and the fixture registry the template regression test renders.
# test-validations overrides both to run the validations against the invalid registries under
# validations_test/.
MODEL := model
FIXTURE := templates_test/fixture

# Registries whose dependency trees validate-dependencies verifies.
REGISTRIES := $(MODEL) $(FIXTURE)

# This repo's GitHub URL, for release artifact URIs and the baseline: the origin remote's URL.
# Origin is read from git's raw config, not with `git remote get-url`, which applies `insteadOf`
# rewrites and could return a URL with a token in it; any user info left in the URL is dropped.
# When origin is a fork, set REPO_URL to https://github.com/embrace-io/embrace-semconv.
REPO_URL := $(shell git config --get remote.origin.url 2>/dev/null | sed -E \
	-e 's|^git@github\.com:|https://github.com/|' -e 's|^(https?://)[^/@]*@|\1|' -e 's|\.git$$||')

# The baseline validate-registry compares this registry with, to catch breaking changes. `auto`
# uses the highest vX.Y.Z release tag of REPO_URL, and validate-registry fails if it can't list
# them. Any other value is used as the baseline registry path, while an empty value skips the
# comparison.
BASELINE := auto

# Invalid registries that test-validations expects a make target to fail on:
# validations_test/<target>/<case>/.
VALIDATION_CASES := $(patsubst %/expected-error.txt,%,\
	$(wildcard validations_test/*/*/expected-error.txt))

.PHONY: all validate-registry validate-dependencies generate-docs generate-all print-version \
	package test test-templates test-policies test-validations update-golden install-weaver \
	install-opa require-weaver require-opa require-jq clean help

# Default: validate, then regenerate everything this repo owns.
all: validate-registry generate-all

# Validate the registry: its resolved dependency trees (validate-dependencies, run first), then the
# schema, then the shared OpenTelemetry policy pack (naming conventions, attribute type rules,
# stability requirements) plus this repo's local policies. Needs network access to fetch the
# dependencies pinned in model/manifest.yaml and the policy pack pinned in versions.env.
#
# A policy that loads but never runs (e.g. its `package` names no stage weaver runs) or no longer
# matches weaver's input passes silently, so validations_test/validate-registry/ holds an invalid
# registry for each policy set, which this target must fail on. An import that matches nothing
# fails it too (see RUN_WEAVER).
#
# The shared pack's backwards-compatibility policies only run against a baseline (see BASELINE):
# compared with the last release, no attribute or signal may be removed and nothing stable may
# change incompatibly. With no release tag there is no baseline, so they're skipped, and
# pre-release tags (e.g. v0.4.0-dev) are never baselines.
validate-registry: require-weaver require-jq validate-dependencies
	@set -e; \
	baseline="$(BASELINE)"; \
	if [[ "$$baseline" == auto ]]; then \
	  if ! tags="$$(git ls-remote --tags --refs "$(REPO_URL)" 'v*')"; then \
	    echo "error: could not list the release tags of '$(REPO_URL)' (REPO_URL) to find the" >&2; \
	    echo "baseline. When origin is a fork, set REPO_URL to the repo it was forked from;" >&2; \
	    echo "otherwise set BASELINE to a registry path, or empty to skip the comparison." >&2; \
	    exit 1; \
	  fi; \
	  tag="$$(awk "$$LATEST_RELEASE_TAG" <<< "$$tags")"; \
	  baseline="$${tag:+$(REPO_URL)@$$tag[$(MODEL)]}"; \
	fi; \
	baseline_args=(); \
	if [[ -n "$$baseline" ]]; then \
	  echo "Comparing against the baseline $$baseline"; \
	  baseline_args=(--baseline-registry "$$baseline"); \
	else \
	  echo "No baseline (BASELINE is empty, or $(REPO_URL) has no release tag): skipping the"; \
	  echo "backwards-compatibility policies"; \
	fi; \
	bash -c "$$RUN_WEAVER" run-weaver validate-registry registry check \
	  -r $(MODEL) \
	  --v2 \
	  --policy "$(POLICY_REPO_URL)@$(POLICY_REPO_REF)[policies/check]" \
	  --policy policies/check/public-attribute-groups \
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
#   otherwise go unnoticed, along with any version conflict it hides.
# The invalid registries under validations_test/validate-dependencies/ break each rule, and
# `make test-validations` confirms this target fails on them.
validate-dependencies: require-weaver
	@set -e; \
	rm -rf .build/dependencies; \
	mkdir -p .build/dependencies; \
	touch .build/dependencies/problems.txt; \
	for registry in $(REGISTRIES); do \
	  out=".build/dependencies/$$registry"; \
	  mkdir -p "$$out"; \
	  if ! weaver registry package -r "$$registry" --v2 --skip-policies \
	      --resolved-registry-uri unused -o "$$out" > "$$out/weaver.log" 2>&1; then \
	    cat "$$out/weaver.log" >&2; \
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

# Regenerate the committed markdown under docs/ from the registry. Needs network access. CI fails
# when the committed docs don't match what this generates, so run this before submitting registry
# or template changes and commit the result.
generate-docs: require-weaver
	rm -rf docs
	weaver registry generate -r $(MODEL) --v2 --templates templates markdown docs

# Every regeneration this repo owns. CI fails when the committed output doesn't match this.
generate-all: generate-docs

# Print this registry's version: the last segment of the schema_url in model/manifest.yaml. Fails
# unless that is a SemVer version, so a schema_url it cannot parse never reaches a package or a
# release tag. The Release workflow reads the version from here too.
print-version:
	@version="$$(awk '/^schema_url:/ { n = split($$2, parts, "/"); print parts[n]; exit }' \
	  $(MODEL)/manifest.yaml)"; \
	semver='^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$$'; \
	if [[ ! "$$version" =~ $$semver ]]; then \
	  echo "error: no SemVer version at the end of the schema_url in $(MODEL)/manifest.yaml" >&2; \
	  echo "(read '$$version')." >&2; \
	  exit 1; \
	fi; \
	echo "$$version"

# Produce the publication manifest and resolved registry under .build/package/. The resolved-
# registry URI baked into the artifacts points at the version's GitHub release (see print-version),
# which is where consumers fetch it from.
package: require-weaver
	@set -eu; \
	version="$$($(MAKE) --no-print-directory -s print-version)"; \
	rm -rf .build/package; \
	weaver registry package \
	  -r $(MODEL) \
	  --v2 \
	  --resolved-registry-uri "$(REPO_URL)/releases/download/v$$version/resolved.yaml" \
	  -o .build/package; \
	echo "packaged version $$version -> .build/package"

# Every test suite this repo owns. Used locally only, as CI runs these as separate jobs.
test: test-templates test-policies test-validations

# Regression test for the doc templates. Compare the docs generated from the fixture with the
# expected golden files, so any change in template output (including imported definitions leaking
# into the docs) shows up as a diff. Run `make update-golden` to update them when a deliberate
# change is made.
#
# A fixture import that matches nothing leaves the provenance filters untested, so it fails this
# test (see RUN_WEAVER): update the imports under the fixture to match what the pinned dependency
# exports.
test-templates: require-weaver require-jq
	@rm -rf .build/test-docs
	@bash -c "$$RUN_WEAVER" run-weaver test-templates registry generate \
	  -r $(FIXTURE) \
	  --v2 \
	  --templates templates \
	  markdown \
	  .build/test-docs
	@if ! git --no-pager diff --no-index --exit-code templates_test/golden .build/test-docs; then \
	  echo "" >&2; \
	  echo "error: generated docs do not match the golden files." >&2; \
	  echo "If the change is intended, refresh them with:" >&2; \
	  echo "    make update-golden" >&2; \
	  exit 1; \
	fi
	@echo "templates OK: fixture output matches templates_test/golden"

# Refresh templates_test/golden/ after a template change that intentionally alters the generated
# output, then review the diff under templates_test/golden/ before committing it.
update-golden: require-weaver
	rm -rf templates_test/golden
	weaver registry generate -r $(FIXTURE) --v2 --templates templates markdown templates_test/golden

# Unit-test the local rego policies under policies/ against policies_test/. Pure OPA: no weaver,
# no network. The cases worth covering involve definitions inherited from a dependency, which the
# real model never produces because it declares no `imports` block.
#
# `opa test` passes when it finds no tests at all, so a second run requires the tests to cover
# every line of rego, which fails for a missing or unloaded test file as well as for an untested
# rule. The coverage is compared here rather than with `--threshold`, as opa writes no report
# (and so no uncovered lines) when the threshold is missed.
test-policies: require-opa require-jq
	opa test --explain fails policies policies_test
	@mkdir -p .build
	@opa test --coverage --format json policies policies_test > .build/opa-coverage.json
	@if ! jq -e '.coverage == 100' .build/opa-coverage.json > /dev/null; then \
	  echo "error: the tests in policies_test/ must run every line of rego. Lines none runs:" >&2; \
	  jq -r "$$UNCOVERED_POLICY_LINES" .build/opa-coverage.json >&2; \
	  exit 1; \
	fi

# Regression test for the validations themselves: the make targets that fail on an invalid
# registry. Each case under validations_test/<target>/ is a registry that is invalid in one way,
# and `make <target>` must fail on it with an error containing the text in its
# expected-error.txt, so a validation that stops failing, or fails for another reason, shows up
# here. The case is passed as MODEL, FIXTURE and REGISTRIES, so it is the registry whichever
# target runs reads. BASELINE is empty unless the case has a baseline.txt naming a baseline
# registry. validations_test/registries/ holds dependencies and baselines that cases share, and is
# not a case itself. Needs network access.
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
	  if $(MAKE) --no-print-directory "$$target" MODEL="$$case" FIXTURE="$$case" \
	      REGISTRIES="$$case" BASELINE="$$baseline" > .build/test-validations.log 2>&1; then \
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

# Install the weaver version pinned in versions.env into ~/.local/bin.
install-weaver:
	.github/actions/setup-weaver/install-weaver.sh

# Install the OPA version pinned in versions.env into ~/.local/bin.
install-opa:
	.github/actions/setup-opa/install-opa.sh

# Fail if weaver is not on PATH; warn if it is not the version pinned in versions.env.
require-weaver:
	@command -v weaver >/dev/null 2>&1 || { \
	  echo "error: weaver not found on PATH. Run 'make install-weaver' to install the pinned" >&2; \
	  echo "version, or put a release binary from https://github.com/open-telemetry/weaver/releases on PATH." >&2; \
	  exit 1; \
	}
	@installed="$$(weaver --version | awk '{print $$2}')"; \
	if [[ "$$installed" != "$(WEAVER_VERSION:v%=%)" ]]; then \
	  echo "warning: weaver $$installed installed, but this repo pins $(WEAVER_VERSION:v%=%) (see versions.env)." >&2; \
	fi

# Fail if opa is not on PATH; warn if it is not the version pinned in versions.env.
require-opa:
	@command -v opa >/dev/null 2>&1 || { \
	  echo "error: opa not found on PATH. Run 'make install-opa' to install the pinned version." >&2; \
	  exit 1; \
	}
	@installed="$$(opa version | awk '/^Version:/ { print $$2 }')"; \
	if [[ "$$installed" != "$(OPA_VERSION:v%=%)" ]]; then \
	  echo "warning: opa $$installed installed, but this repo pins $(OPA_VERSION:v%=%) (see versions.env)." >&2; \
	fi

# Fail if jq is not on PATH. GitHub's runners have it preinstalled.
require-jq:
	@command -v jq >/dev/null 2>&1 || { \
	  echo "error: jq not found on PATH. Install it from https://jqlang.org/download/." >&2; \
	  exit 1; \
	}

# Remove build output only. docs/ is generated but committed, so it is left alone
clean:
	rm -rf .build

help:
	@echo "validate-registry      validate the registry (dependencies + schema + policies)"
	@echo "validate-dependencies  verify the resolved dependency trees match the manifests"
	@echo "generate-docs          regenerate committed markdown under docs/"
	@echo "generate-all           run every regeneration this repo owns"
	@echo "print-version          print the version at the end of model/manifest.yaml's schema_url"
	@echo "package                produce the publication artifacts under .build/package/"
	@echo "test                   run every test suite (templates + policies + validations)"
	@echo "test-templates         compare the docs rendered from the fixture with the golden files"
	@echo "test-policies          unit-test the local rego policies"
	@echo "test-validations       confirm validation fails on each registry in validations_test/"
	@echo "update-golden          refresh the golden files after an intended template change"
	@echo "install-weaver         install the weaver version pinned in versions.env"
	@echo "install-opa            install the OPA version pinned in versions.env"
	@echo "clean                  remove build output"

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

# Shell program that runs weaver: `bash -c "$$RUN_WEAVER" run-weaver <name> <weaver arguments>`.
# It asks weaver for JSON diagnostics, keeps them in .build/<name>.json, prints them unwrapped
# (weaver wraps its text output to the terminal width, which splits the messages
# test-validations looks for), and fails when weaver does or when any import matches nothing.
# Weaver only warns about the latter, and an import that matches nothing silently drops what the
# registry meant to include.
define RUN_WEAVER
set -e
name="$$1"
shift
mkdir -p .build
out=".build/$$name.json"
status=0
weaver "$$@" --diagnostic-format json --diagnostic-stdout=true > "$$out" || status=$$?
if ! jq -e 'type == "array"' "$$out" > /dev/null 2>&1; then
  if [[ $$status -ne 0 ]]; then exit $$status; fi
  echo "error: weaver's diagnostics in $$out are not a JSON array." >&2
  exit 1
fi
jq -r "$$PRINT_DIAGNOSTICS" "$$out" >&2
if [[ $$status -ne 0 ]]; then exit $$status; fi
unmatched="$$(jq -r "$$UNMATCHED_IMPORTS" "$$out")"
if [[ -n "$$unmatched" ]]; then
  echo "error: imports that match nothing in any dependency:" >&2
  echo "$$unmatched" >&2
  echo "Each import must match something a direct dependency exports." >&2
  exit 1
fi
endef
export RUN_WEAVER

# jq program for RUN_WEAVER: one line per diagnostic, with the "definition/2 is not yet stable"
# warning weaver emits for every such file, the dependencies' included, collapsed to one line.
define PRINT_DIAGNOSTICS
def unstable: [.error | objects | .FailToResolveDefinition? | objects | .UnstableFileFormat?
  | select(. != null)] | length > 0;
([.[] | select(unstable)] | length) as $$unstable
| [.[] | select(unstable | not) | .diagnostic | objects
    | "\(.severity // "Error"): \(.message)"
      + (if .help then "\n  help: \(.help)" else "" end)]
  + (if $$unstable > 0
     then ["Warning: \($$unstable) definition files, the dependencies' included, use file_format "
           + "definition/2, which weaver still reports as not yet stable."]
     else [] end)
| .[]
endef
export PRINT_DIAGNOSTICS

# jq program for RUN_WEAVER: one line per import that matched nothing, from weaver's JSON
# diagnostics.
define UNMATCHED_IMPORTS
.[] | .error | objects | .UnmatchedImport // empty | "  \(.signal): \(.pattern)"
endef
export UNMATCHED_IMPORTS

# jq program for test-policies: the lines of each rego file that no test runs, from the coverage
# report of `opa test --coverage`.
define UNCOVERED_POLICY_LINES
.files // {} | to_entries[] | select(.value.not_covered) |
  "  \(.key): lines \([.value.not_covered[].start.row] | unique | map(tostring) | join(", "))"
endef
export UNCOVERED_POLICY_LINES
