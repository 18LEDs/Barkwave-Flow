# Barkwave Flow

This project manages Datadog observability pipeline configurations using Terraform. It also exposes a small API that can modify pipeline configuration files and optionally trigger Terraform apply.

## Structure

- `pipelines/` – JSON files defining each pipeline.
- `terraform/` – Terraform code that creates a `datadog_logs_custom_pipeline` resource for every file in `pipelines/`.
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

### Importing Existing Pipelines

Run `scripts/import_state.sh` to import pipeline IDs into Terraform state. Edit the script to specify the pipeline ID for each pipeline before running it:

```bash
./scripts/import_state.sh
```

This script can be rerun at any time to refresh the state.

### State Storage and Locking

The Terraform configuration is set up to use the PostgreSQL backend which
provides server-side state storage and locking. Supply the connection details
when running `terraform init`:

```bash
cd terraform
terraform init -backend-config="conn_str=postgres://user:pass@postgres-server/terraform"
```

Ensure the PostgreSQL instance is hosted on-premises to keep the state within
your infrastructure.
