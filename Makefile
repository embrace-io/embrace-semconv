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
# registry for each policy set, which this target must fail on.
validate-registry: require-weaver validate-dependencies
	@weaver registry check \
	  -r $(MODEL) \
	  --v2 \
	  --policy "$(POLICY_REPO_URL)@$(POLICY_REPO_REF)[policies/check]" \
	  --policy policies/check/public-attribute-groups

# Verify the dependency tree weaver actually resolves for each of REGISTRIES, rather than what their
# manifests declare. The resolved registry that `weaver registry package` writes lists every
# registry in the tree, each under the schema_url in its own manifest. Two things must hold there:
# - No registry is in the tree at more than one version. When two registries request different
#   versions of one (e.g. this registry and one of its dependencies both depend on core), weaver
#   uses the highest, so some registry runs against a version it was not validated with. Weaver
#   warns only when the dropped version is the one the root requested.
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

# Regenerate the committed markdown under docs/ from the model. Needs network access. CI fails
# when the committed docs don't match what this generates, so run this before submitting model or
# template changes and commit the result.
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
	repo_url="$$(git remote get-url origin)"; \
	repo_url="$${repo_url%.git}"; \
	case "$$repo_url" in \
	  git@github.com:*) repo_url="https://github.com/$${repo_url#git@github.com:}" ;; \
	esac; \
	rm -rf .build/package; \
	weaver registry package \
	  -r $(MODEL) \
	  --v2 \
	  --resolved-registry-uri "$$repo_url/releases/download/v$$version/resolved.yaml" \
	  -o .build/package; \
	echo "packaged version $$version -> .build/package"

# Every test suite this repo owns. Used locally only, as CI runs these as separate jobs.
test: test-templates test-policies test-validations

# Regression test for the doc templates. Compare the docs generated from the fixture with the
# expected golden files, so any change in template output (including imported definitions leaking
# into the docs) shows up as a diff. Run `make update-golden` to update them when a deliberate
# change is made.
#
# A fixture import that matches nothing leaves the provenance filters untested, and weaver only
# warns about it. Weaver wraps its text warnings to the terminal width, so the unmatched-import
# check reads the typed JSON diagnostics instead, and prints their text for humans.
test-templates: require-weaver require-jq
	@mkdir -p .build
	@rm -rf .build/test-docs
	@set -e; \
	status=0; \
	weaver registry generate \
	  -r $(FIXTURE) \
	  --v2 \
	  --templates templates \
	  --diagnostic-format json \
	  --diagnostic-stdout=true \
	  markdown \
	  .build/test-docs > .build/test-templates.json || status=$$?; \
	if ! jq -e 'type == "array"' .build/test-templates.json > /dev/null 2>&1; then \
	  if [[ $$status -ne 0 ]]; then exit $$status; fi; \
	  echo "error: weaver's diagnostics in .build/test-templates.json are not a JSON array." >&2; \
	  exit 1; \
	fi; \
	jq -r '.[] | .diagnostic.ansi_message // empty' .build/test-templates.json >&2; \
	if [[ $$status -ne 0 ]]; then exit $$status; fi; \
	unmatched="$$(jq -r "$$UNMATCHED_IMPORTS" .build/test-templates.json)"; \
	if [[ -n "$$unmatched" ]]; then \
	  echo "error: fixture imports match nothing in any dependency:" >&2; \
	  echo "$$unmatched" >&2; \
	  echo "The provenance filters are no longer exercised. Update the imports under" >&2; \
	  echo "$(FIXTURE)/ to match what the pinned dependency exports." >&2; \
	  exit 1; \
	fi
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
# target runs reads. validations_test/registries/ holds dependencies that cases share, and is not
# a case itself. Needs network access.
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
	  if $(MAKE) --no-print-directory "$$target" MODEL="$$case" FIXTURE="$$case" \
	      REGISTRIES="$$case" > .build/test-validations.log 2>&1; then \
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

# jq program for test-templates: one line per import that matched nothing, from weaver's JSON
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
