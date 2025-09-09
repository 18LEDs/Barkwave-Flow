#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../terraform"

# Import helper: tries JSON first (pipelines/<name>.json -> .id), falls back to IDS map.
# Supports Observability Pipelines (default) and Logs Pipelines via RESOURCE_TYPE env.
# Requires: jq

# RESOURCE_TYPE: observability|logs (default: observability)
RESOURCE_TYPE="${RESOURCE_TYPE:-observability}"

case "$RESOURCE_TYPE" in
  observability)
    ADDRESS_PREFIX="datadog_observability_pipeline.pipeline"
    ;;
  logs)
    ADDRESS_PREFIX="datadog_logs_custom_pipeline.pipeline"
    ;;
  *)
    echo "Unsupported RESOURCE_TYPE: $RESOURCE_TYPE (use 'observability' or 'logs')" >&2
    exit 1
    ;;
esac

# Optional explicit map overrides (Format: ["pipeline_name"]="<pipeline_id>")
declare -A IDS=( )

# Build list of pipeline names from ../pipelines/*.json
mapfile -t PIPELINE_FILES < <(ls -1 ../pipelines/*.json 2>/dev/null || true)

if [ ${#PIPELINE_FILES[@]} -eq 0 ]; then
  echo "No pipeline JSON files found under ../pipelines" >&2
  exit 1
fi

for file in "${PIPELINE_FILES[@]}"; do
  name="$(basename "$file" .json)"
  id=""
  if command -v jq >/dev/null 2>&1; then
    id="$(jq -r 'try .id // empty' "$file")"
  fi
  if [ -z "$id" ]; then
    id="${IDS[$name]:-}"
  fi
  if [ -z "$id" ]; then
    echo "Skipping $name: no ID in JSON and no override provided" >&2
    continue
  fi
  echo "Importing $name -> $id"
  terraform import "${ADDRESS_PREFIX}[\"$name\"]" "$id"
done
