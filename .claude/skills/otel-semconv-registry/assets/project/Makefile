# ==== registry: a registry defined and validated in this project
# The registry directory. Its manifest.yaml sits directly inside it.
MODEL := model

# The registry directory's path within the repo, for the `[...]` part of the baseline's
# registry_path. It differs from MODEL only when the project lives in a subdirectory of its repo.
MODEL_REPO_PATH := $(MODEL)

# Registries whose dependency trees validate-dependencies verifies: the registry, and the templates
# fixture when the project has the templates section (FIXTURE is empty without it).
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
# versions.env: registry-specific ones go here (the public-groups section adds the
# public-attribute-groups policy).
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
# ==== policies: unit tests for the registry's local rego policies, with OPA
# ==== public-groups: the policy that every attribute is exported by a public attribute group

# Every attribute the registry defines must be exported by one of its public attribute groups.
LOCAL_POLICIES += policies/check/public-attribute-groups
# ==== end public-groups

# The rego policies and their unit tests, for test-policies.
POLICIES_DIR := policies
POLICY_TESTS_DIR := policies_test

# Where the setup-opa action lives: the repo root's .github/actions, found through git, so a
# project in a subdirectory of its repo needs no setting here. Its install script is shared with
# CI. Outside a git checkout it falls back to this directory's .github/actions. Set it by hand when
# the action lives elsewhere (a project inside a git submodule, say).
ACTIONS_DIR := $(or $(shell git rev-parse --show-toplevel 2>/dev/null),.)/.github/actions

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
# ==== end policies
# ==== end registry
