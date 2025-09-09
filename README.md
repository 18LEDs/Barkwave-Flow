# Barkwave Flow

This project manages Datadog Observability Pipelines (OP) using Terraform. It ships with an API to edit pipeline files and optionally trigger Terraform apply.

## Structure

- `pipelines/` – JSON files defining each pipeline.
- `terraform/` – Terraform code that creates a `datadog_observability_pipeline` resource for every file in `pipelines/`.
- `api/` – Python FastAPI application offering endpoints to update pipelines and apply Terraform.
- `scripts/import_state.sh` – helper script to import existing Datadog pipelines into Terraform state.
- `scripts/fetch_pipelines.py` – fetches pipeline definitions from the Datadog API and stores them in `pipelines/`.

## Requirements

- Terraform >= 1.0
- Python 3.10+
- Datadog API and application keys exported as environment variables: `DATADOG_API_KEY` and `DATADOG_APP_KEY`.

## Usage

1. **Install dependencies**
   ```bash
   pip install -r api/requirements.txt
   ```
2. **Initialize Terraform**
   ```bash
   cd terraform
   terraform init
   ```
3. **Run the API**
   ```bash
   uvicorn api.main:app --reload
   ```

### Fetching Pipeline Configurations

Use `scripts/fetch_pipelines.py` to pull the latest pipeline configuration from
the Datadog API and save it under `pipelines/` as JSON. This allows the
configuration to be version controlled and consumed by Terraform.

```bash
DATADOG_API_KEY=xxx DATADOG_APP_KEY=yyy ./scripts/fetch_pipelines.py
```

Without arguments the script retrieves six Kubernetes related pipelines:
`k8-aws-nonprod`, `k8-azure-nonprod`, `k8-onprem-nonprod`, `k8-aws-prod`,
`k8-azure-prod`, and `k8-onprem-prod`. Individual pipeline names can be passed
as arguments to fetch a subset.

### API Endpoints

- `GET /pipelines` – List pipeline configs.
- `PUT /pipelines/{name}` – Replace the configuration for one pipeline. Body should be JSON in the same format as the files in `pipelines/`.
- `POST /apply` – Run `terraform apply` for all pipelines after validating the configuration.
- `POST /apply?pipelines=pipeline1,pipeline2` – Apply a subset of pipelines.

Processor-focused endpoints to ease edits (targets OP `config.processors`):

- `GET /pipelines/{name}/processors` – List processors
- `PUT /pipelines/{name}/processors` – Replace full processor array
- `PUT /pipelines/{name}/processors/{index}` – Replace one processor
- `PATCH /pipelines/{name}/processors/{index}` – Deep-merge update one processor (partial update)

### Importing Existing Pipelines

Run `scripts/import_state.sh` to import pipeline IDs into Terraform state. It supports Observability Pipelines by default (set `RESOURCE_TYPE=logs` to import logs pipelines). Edit the script to specify overrides if your JSON files don’t include `id`:

```bash
./scripts/import_state.sh
```

This script can be rerun at any time to refresh the state.

### State Storage and Locking

State is stored in Consul for server-side storage and locking. Initialize with
backend config values (address, path, scheme, token):

```bash
cd terraform
terraform init \
  -backend-config="address=http://localhost:8500" \
  -backend-config="path=barkwave-flow/terraform.tfstate" \
  -backend-config="scheme=http" \
  -backend-config="access_token=$CONSUL_HTTP_TOKEN" \
  -backend-config="lock=true"
```

You can run a local Consul via Docker using `docker-compose.yml` (service `consul`).

### Gitea + Actions (GitOps)

This repo includes a ready-to-run Gitea and runner in `docker-compose.yml` and
a workflow at `.gitea/workflows/terraform.yml`.

- Pushes and PRs to `main` run `terraform init/plan` for both `nonprod` and `prod`.
- Only pushes to `main` with commit message containing `[apply]` run `terraform apply` for both environments.
- Applies use `-parallelism=1` as recommended by Datadog for OP resources.

Secrets required in the repository (or org) settings (per environment):

- Nonprod: `DATADOG_API_KEY_NONPROD`, `DATADOG_APP_KEY_NONPROD`,
  `CONSUL_HTTP_ADDR_NONPROD`, `CONSUL_SCHEME_NONPROD`, `CONSUL_BACKEND_PATH_NONPROD`, `CONSUL_HTTP_TOKEN_NONPROD`
- Prod: `DATADOG_API_KEY_PROD`, `DATADOG_APP_KEY_PROD`,
  `CONSUL_HTTP_ADDR_PROD`, `CONSUL_SCHEME_PROD`, `CONSUL_BACKEND_PATH_PROD`, `CONSUL_HTTP_TOKEN_PROD`

Runner bootstrap via docker-compose requires `GITEA_RUNNER_REGISTRATION_TOKEN` in your shell
environment before `docker compose up -d`. Access Gitea at http://localhost:3000.

You can bootstrap a repo and set CI secrets with:

```bash
export GITEA_BASE_URL=http://localhost:3000
export GITEA_TOKEN=YOUR_GITEA_TOKEN
export GITEA_OWNER=your-org
export GITEA_REPO=barkwave-flow
export CREATE_REPO=1
export DATADOG_API_KEY=xxx
export DATADOG_APP_KEY=yyy
export CONSUL_HTTP_ADDR=http://consul:8500
export CONSUL_BACKEND_PATH=barkwave-flow/terraform.tfstate
./scripts/gitea_bootstrap.sh
```

### Importing State

`scripts/import_state.sh` supports Observability Pipelines and Logs Pipelines.
Set `RESOURCE_TYPE=observability` (default) or `RESOURCE_TYPE=logs`.
It reads an `id` field from each JSON (if present) and falls back to an
override map inside the script. Requires `jq`.

Examples:

```bash
# Import OP pipelines
RESOURCE_TYPE=observability ./scripts/import_state.sh

# Import Logs pipelines
RESOURCE_TYPE=logs ./scripts/import_state.sh
```

### OP JSON Schema (repo files -> Terraform)

Each file under `pipelines/` should contain a JSON object like:

```
{
  "name": "test pipeline",
  "config": {
    "sources": [
      { "type": "datadog_agent", "id": "agent-source-1" }
    ],
    "processors": [
      {"type": "filter", "id": "filter-1", "include": "service:nginx", "inputs": ["agent-source-1"]},
      {"type": "parse_json", "id": "parser-1", "field": "message", "inputs": ["filter-1"]},
      {"type": "sample", "id": "sampler-1", "rate": 0.1, "inputs": ["parser-1"]}
    ],
    "destinations": [
      {"type": "datadog_logs", "id": "sink-1", "inputs": ["sampler-1"]}
    ]
  },
  "id": "<optional: pipeline ID for import>"
}
```

Currently implemented in Terraform mapping:

- Sources: `datadog_agent`, `kafka` (with `tls`, `sasl`, `librdkafka_option`)
- Processors: `filter`, `parse_json`, `sample`
- Destinations: `datadog_logs`

Additional types can be added following the same pattern.

### Backend Init Convenience

Use `scripts/init_backend.sh` to standardize Consul backend initialization:

```bash
export CONSUL_HTTP_ADDR=http://localhost:8500
export CONSUL_BACKEND_PATH=barkwave-flow/terraform.tfstate
export CONSUL_HTTP_TOKEN=...
./scripts/init_backend.sh
```

The API also attempts to run `terraform init` automatically if needed, using the same env vars (`CONSUL_HTTP_ADDR`, `CONSUL_BACKEND_PATH`, `CONSUL_SCHEME`, `CONSUL_HTTP_TOKEN`). Set `TF_FORCE_INIT=1` to force reinit.

### Drift Detection

A scheduled workflow `.gitea/workflows/drift.yml` runs daily and fails when drift
is detected (Terraform plan exit code 2) for `nonprod` and `prod` independently.
You can also trigger it manually via the workflow_dispatch event.
