#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../terraform"

# Update the map below with Datadog pipeline IDs
# Format: ["pipeline_name"]="<pipeline_id>"
declare -A IDS=(
  ["pipeline1"]="PIPELINE_ID_1"
  ["pipeline2"]="PIPELINE_ID_2"
  # add remaining mappings
)

for name in "${!IDS[@]}"; do
  id="${IDS[$name]}"
  if [ "$id" = "" ]; then
    echo "Skipping $name, no ID defined" >&2
    continue
  fi
  terraform import "datadog_logs_custom_pipeline.pipeline[\"$name\"]" "$id"
done
