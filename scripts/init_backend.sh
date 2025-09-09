#!/usr/bin/env bash
set -euo pipefail

# Initialize Terraform with Consul backend settings from environment variables.
# Required:
#   CONSUL_HTTP_ADDR (e.g., http://localhost:8500)
#   CONSUL_BACKEND_PATH (e.g., barkwave-flow/terraform.tfstate)
# Optional:
#   CONSUL_SCHEME (default: http)
#   CONSUL_HTTP_TOKEN

cd "$(dirname "$0")/../terraform"

address="${CONSUL_HTTP_ADDR:-}"
path="${CONSUL_BACKEND_PATH:-}"
scheme="${CONSUL_SCHEME:-http}"
token="${CONSUL_HTTP_TOKEN:-}"

if [ -z "$address" ] || [ -z "$path" ]; then
  echo "CONSUL_HTTP_ADDR and CONSUL_BACKEND_PATH are required" >&2
  exit 1
fi

args=(
  -backend-config="address=${address}"
  -backend-config="path=${path}"
  -backend-config="scheme=${scheme}"
  -backend-config="lock=true"
)

if [ -n "$token" ]; then
  args+=( -backend-config="access_token=${token}" )
fi

terraform init "${args[@]}"

