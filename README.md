# Barkwave Flow

This project manages Datadog observability pipeline configurations using Terraform. It also exposes a small API that can modify pipeline configuration files and optionally trigger Terraform apply.

## Structure

- `pipelines/` – JSON files defining each pipeline.
- `terraform/` – Terraform code that creates a `datadog_logs_custom_pipeline` resource for every file in `pipelines/`.
- `api/` – Python FastAPI application offering endpoints to update pipelines and apply Terraform.
- `scripts/import_state.sh` – helper script to import existing Datadog pipelines into Terraform state.

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
