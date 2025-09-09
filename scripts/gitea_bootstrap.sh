#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a Gitea repo and set Actions secrets for this project.
# Requirements:
#   - GITEA_BASE_URL (e.g., http://localhost:3000)
#   - GITEA_TOKEN (admin or user token with repo + actions scope)
#   - GITEA_OWNER (org or user name)
#   - GITEA_REPO (new or existing repo name)
# Optional:
#   - CREATE_REPO=1 (to create the repo if it doesn't exist)
#   - VISIBILITY=private|public (default: private)
#   - DEFAULT_BRANCH=main
#   - SECRETS: DATADOG_API_KEY, DATADOG_APP_KEY, CONSUL_HTTP_ADDR, CONSUL_SCHEME, CONSUL_BACKEND_PATH, CONSUL_HTTP_TOKEN

base="${GITEA_BASE_URL:?set GITEA_BASE_URL}"
token="${GITEA_TOKEN:?set GITEA_TOKEN}"
owner="${GITEA_OWNER:?set GITEA_OWNER}"
repo="${GITEA_REPO:?set GITEA_REPO}"
visibility="${VISIBILITY:-private}"
default_branch="${DEFAULT_BRANCH:-main}"

auth_header=( -H "Authorization: token ${token}" )

if [ "${CREATE_REPO:-0}" = "1" ]; then
  echo "Creating repository ${owner}/${repo} (if not exists)"
  curl -sf -X POST \
    -H 'Content-Type: application/json' \
    "${auth_header[@]}" \
    -d "{\"name\":\"${repo}\",\"private\":$([ "$visibility" = private ] && echo true || echo false),\"default_branch\":\"${default_branch}\"}" \
    "${base}/api/v1/orgs/${owner}/repos" || true
fi

echo "Setting Actions secrets"
set_secret() {
  local name="$1"; shift
  local value="$1"; shift
  if [ -z "$value" ]; then
    echo "Skipping empty secret: $name" >&2
    return 0
  fi
  curl -sf -X PUT \
    -H 'Content-Type: application/json' \
    "${auth_header[@]}" \
    -d "{\"data\":\"${value//\"/\\\"}\"}" \
    "${base}/api/v1/repos/${owner}/${repo}/actions/secrets/${name}"
  echo
}

set_secret DATADOG_API_KEY "${DATADOG_API_KEY:-}"
set_secret DATADOG_APP_KEY "${DATADOG_APP_KEY:-}"
set_secret CONSUL_HTTP_ADDR "${CONSUL_HTTP_ADDR:-}"
set_secret CONSUL_SCHEME "${CONSUL_SCHEME:-}"
set_secret CONSUL_BACKEND_PATH "${CONSUL_BACKEND_PATH:-}"
set_secret CONSUL_HTTP_TOKEN "${CONSUL_HTTP_TOKEN:-}"

echo "Done. Ensure a runner is registered and the repo contains .gitea/workflows/terraform.yml"

