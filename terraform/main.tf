provider "datadog" {
  api_key = var.datadog_api_key
  app_key = var.datadog_app_key
}

locals {
  pipeline_files = fileset("${path.module}/../pipelines", "*.json")
  pipelines = { for file in local.pipeline_files :
    trimsuffix(basename(file), ".json") => jsondecode(file("${path.module}/../pipelines/${file}"))
  }
}

resource "datadog_logs_custom_pipeline" "pipeline" {
  for_each = local.pipelines

  name       = each.value.name
  is_enabled = true
  filter {
    query = each.value.filter
  }
  # Additional processors can be defined via each.value.processors if needed.
}

