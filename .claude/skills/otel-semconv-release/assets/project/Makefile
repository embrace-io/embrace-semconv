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
