# ==== codegen: @@LANGUAGE@@ source code generated from a registry with this project's templates
# The registry the code is generated from: a remote registry pinned to a release, e.g. the core
# registry alone with https://github.com/open-telemetry/semantic-conventions@v1.44.0[model], or
# this project's own registry ($(MODEL), with the registry section) when it defines conventions or
# combines several registries. With Renovate, a pinned release gets a
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
