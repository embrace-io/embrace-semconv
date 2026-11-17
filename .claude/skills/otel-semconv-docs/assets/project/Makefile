# ==== docs: markdown docs for the registry's conventions, generated and committed
# Where the generated docs are written. Everything in it is replaced on each run, so it must hold
# only generated files.
DOCS_DIR := docs

# Where the docs are read, with no trailing slash: the generated pages link to each other with
# absolute URLs under it, so the links work wherever a page is viewed. For docs read on GitHub,
# the docs directory on the default branch, e.g. https://github.com/<owner>/<repo>/blob/main/docs.
DOCS_BASE_URL := @@DOCS_BASE_URL@@

# The shared markdown templates of opentelemetry-weaver-packages, at the commit versions.env pins
# for the shared policy pack, so one pin moves both.
DOCS_TEMPLATES := $(POLICY_REPO_URL)@$(POLICY_REPO_REF)[templates/docs]

# Extra flags for the docs templates, split on spaces, e.g. `--param humanize_headings=true`; the
# templates' README lists their params.
DOCS_PARAMS :=

.PHONY: generate-docs

# Regenerate the committed markdown under $(DOCS_DIR)/ from the registry. Needs network access. CI
# fails when the committed docs don't match what this generates, so run this before submitting
# registry changes and commit the result.
#
# The shared templates document every definition the registry resolves, the ones it only imports
# from a dependency included, as if the registry defined them. So the docs-import-only template
# first lists the root namespaces that hold only imported definitions, and the docs leave them out.
generate-docs: require-weaver require-jq
	@set -e; \
	if [[ -z "$(DOCS_DIR)" || "$(DOCS_DIR)" == . || "$(DOCS_DIR)" == / ]]; then \
	  echo "error: DOCS_DIR must name a directory that holds only generated docs." >&2; \
	  exit 1; \
	fi; \
	rm -rf .build/docs-import-only $(DOCS_DIR); \
	bash -c "$$RUN_WEAVER" run-weaver docs-import-only registry generate \
	  -r $(MODEL) --v2 --templates templates docs-import-only .build/docs-import-only; \
	excluded="$$(< .build/docs-import-only/namespaces.json)"; \
	bash -c "$$RUN_WEAVER" run-weaver generate-docs registry generate \
	  -r $(MODEL) --v2 --templates "$(DOCS_TEMPLATES)" markdown $(DOCS_DIR) \
	  --param "exclude_root_namespace=$$excluded" --param "registry_base_url=$(DOCS_BASE_URL)" \
	  $(DOCS_PARAMS)

generate-all:: generate-docs
	@:

help::
	@echo "generate-docs          regenerate the committed markdown under $(DOCS_DIR)/"
# ==== end docs
