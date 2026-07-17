#!/usr/bin/env bash
# Validates the registry by checking schema validity, whether upstream dependencies
# can be resolved and the policies adhered to.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Error out if the pinned upstream version isn't the same as the one declared in the manifest
if ! grep -q "semantic-conventions@${CORE_SEMCONV_VERSION}\[model\]" "${REPO_ROOT}/model/manifest.yaml"; then
  echo "error: model/manifest.yaml upstream registry_path does not match CORE_SEMCONV_VERSION=${CORE_SEMCONV_VERSION} in versions.env." >&2
  echo "Update whichever of the two is stale." >&2
  exit 1
fi

POLICY_DIR="${REPO_ROOT}/build/weaver-policies"
POLICY_STAMP="${POLICY_DIR}/.${POLICY_REPO_REF}"

if [[ ! -f "${POLICY_STAMP}" ]]; then
  rm -rf "${POLICY_DIR}"
  git init -q "${POLICY_DIR}"
  git -C "${POLICY_DIR}" remote add origin "${POLICY_REPO_URL}"
  git -C "${POLICY_DIR}" fetch -q --depth 1 origin "${POLICY_REPO_REF}"
  git -C "${POLICY_DIR}" checkout -q --detach FETCH_HEAD
  touch "${POLICY_STAMP}"
fi

weaver registry check \
  -r "${REPO_ROOT}/model" \
  --v2 \
  --policy "${POLICY_DIR}/policies/check" \
  --policy "${REPO_ROOT}/policies/check/public-attribute-groups"
