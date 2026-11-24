# Validation, generation and packaging for this project. The same targets run locally and in CI;
# `make help` lists them.
#
# Each part is a section from a `# ==== <name>` line (optionally followed by `: <description>`)
# to its `# ==== end <name>` line: `project`, `common`, `templates` and `codegen`, which may hold
# sections of their own. A section's settings are at its top, and a section only uses settings
# from sections above it. Requires GNU make 3.81 or later (macOS ships 3.81), so every multi-line
# recipe runs in a single shell via backslash continuations.

# ==== project
.PHONY: all

# Default: validate, then regenerate everything this project owns.
all: @@ALL_PREREQUISITES@@
# ==== end project

# ==== common: tool pins and installation, the weaver runner
SHELL := /usr/bin/env bash

# The tool versions (and any other pins the project's sections need) are in versions.env.
include versions.env

# The weaver every target runs: the one on PATH, or a path to the pinned one installed elsewhere
# (make <target> WEAVER=<dir>/weaver, after make install-weaver WEAVER_INSTALL_DIR=<dir>).
WEAVER := weaver
export WEAVER

# Extra flags for every weaver run, split on spaces.
WEAVER_FLAGS :=
# ==== private
# The source registry, or a registry it depends on, is in a private repository: without this flag,
# weaver's git operations can't use the machine's git credentials.
WEAVER_FLAGS += --allow-git-credentials
# ==== end private
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

# Where install-weaver puts weaver; empty means ~/.local/bin. Set it (make install-weaver
# WEAVER_INSTALL_DIR=<dir>) to keep a weaver other projects on the machine use, then run the
# targets with WEAVER=<dir>/weaver.
WEAVER_INSTALL_DIR :=

# Install the weaver version pinned in versions.env. CI installs the same version with weaver's
# setup-weaver action.
install-weaver:
	WEAVER_VERSION=$(WEAVER_VERSION) bash scripts/install-weaver.sh $(WEAVER_INSTALL_DIR)

# Fail if $(WEAVER) is not found; warn if it is not the version pinned in versions.env.
require-weaver:
	@command -v "$(WEAVER)" >/dev/null 2>&1 || { \
	  echo "error: $(WEAVER) not found. Run 'make install-weaver' to install the pinned" >&2; \
	  echo "version (with WEAVER_INSTALL_DIR=<dir> to install it where WEAVER points), or put a" >&2; \
	  echo "release binary from https://github.com/open-telemetry/weaver/releases on PATH." >&2; \
	  exit 1; \
	}
	@installed="$$("$(WEAVER)" --version | awk '{print $$2}')"; \
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

# Remove build output only. Generated code that is committed is left alone.
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
define RUN_WEAVER
set -e
name="$$1"
shift
mkdir -p .build
out=".build/$$name.json"
status=0
# WEAVER_FLAGS holds zero or more flags, so it is split on spaces on purpose.
"$${WEAVER:-weaver}" "$$@" $$WEAVER_FLAGS --diagnostic-format json --diagnostic-stdout=true \
  > "$$out" || status=$$?
if ! jq -e 'type == "array"' "$$out" > /dev/null 2>&1; then
  if [[ $$status -ne 0 ]]; then exit $$status; fi
  echo "error: weaver's diagnostics in $$out are not a JSON array." >&2
  exit 1
fi
jq -r "$$DIAGNOSTIC_DEFS $$PRINT_DIAGNOSTICS" "$$out" >&2
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

# jq definitions the programs below share, for weaver's JSON diagnostics.
define DIAGNOSTIC_DEFS
def policy: (.error | objects | .type?) == "policy_violation";
def unstable: [.error | objects | .FailToResolveDefinition? | objects | .UnstableFileFormat?
  | select(. != null)] | length > 0;
endef
export DIAGNOSTIC_DEFS

# jq program for RUN_WEAVER: one line per diagnostic. Policy findings print their id and message;
# the "definition/2 is not yet stable" warning weaver emits for every such file, the dependencies'
# included, collapses to one line.
define PRINT_DIAGNOSTICS
([.[] | select(unstable)] | length) as $$unstable
| [.[] | select(unstable | not)
    | if policy
      then "Policy \(.error.violation.level) [\(.error.violation.id)]: \(.error.violation.message)"
      else "\(.diagnostic.severity // "Error"): \(.diagnostic.message)"
        + (if .diagnostic.help then "\n  help: \(.diagnostic.help)" else "" end)
      end]
  + (if $$unstable > 0
     then ["Warning: \($$unstable) definition files, the dependencies' included, use file_format "
           + "definition/2, which weaver still reports as not yet stable."]
     else [] end)
| .[]
endef
export PRINT_DIAGNOSTICS

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

# ==== codegen: @@LANGUAGE@@ source code generated from a registry with this project's templates
# The registry the code is generated from: a remote registry pinned to a release, e.g. the core
# registry alone with https://github.com/open-telemetry/semantic-conventions@v1.44.0[model], or
# the path of a registry directory the project already has, when it defines conventions of its
# own or combines several registries. With Renovate, a pinned release gets a
# `# renovate: datasource=github-tags depName=<owner>/<repo> versioning=semver-coerced` line
# directly above it.
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
	case "$(strip $(GENERATED_DIR))" in \
	  ""|.|./|/|..|../|*/..|*/../|.build|.build/|./.build|./.build/) \
	    echo "error: GENERATED_DIR must name a directory that holds only generated code, not" >&2; \
	    echo "'$(GENERATED_DIR)'." >&2; \
	    exit 1;; \
	esac; \
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
