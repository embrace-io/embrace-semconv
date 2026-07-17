#!/usr/bin/env bash
# Regenerates the committed markdown documentation under docs/ from the model.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

rm -rf "${REPO_ROOT}/docs"
weaver registry generate \
  -r "${REPO_ROOT}/model" \
  --v2 \
  --templates "${REPO_ROOT}/templates" \
  markdown \
  "${REPO_ROOT}/docs"
echo "regenerated ${REPO_ROOT}/docs"
