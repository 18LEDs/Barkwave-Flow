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

resource "datadog_observability_pipeline" "pipeline" {
  for_each = local.pipelines

  name = each.value.name

  config {
    # SOURCES
    dynamic "sources" {
      for_each = length(try(each.value.config.sources, [])) > 0 ? [1] : []
      content {
        # datadog_agent source(s)
        dynamic "datadog_agent" {
          for_each = try([for s in each.value.config.sources : s if try(s.type, "") == "datadog_agent"], [])
          content {
            id = try(datadog_agent.value.id, null)
          }
        }

        # kafka source(s)
        dynamic "kafka" {
          for_each = try([for s in each.value.config.sources : s if try(s.type, "") == "kafka"], [])
          content {
            id       = try(kafka.value.id, null)
            group_id = try(kafka.value.group_id, null)
            topics   = try(kafka.value.topics, null)

            dynamic "tls" {
              for_each = try([kafka.value.tls], [])
              content {
                crt_file = try(tls.value.crt_file, null)
                key_file = try(tls.value.key_file, null)
                ca_file  = try(tls.value.ca_file, null)
              }
            }

            dynamic "sasl" {
              for_each = try([kafka.value.sasl], [])
              content {
                mechanism = try(sasl.value.mechanism, null)
                username  = try(sasl.value.username, null)
                password  = try(sasl.value.password, null)
              }
            }

            dynamic "librdkafka_option" {
              for_each = try(kafka.value.librdkafka_option, [])
              content {
                name  = try(librdkafka_option.value.name, null)
                value = try(librdkafka_option.value.value, null)
              }
            }
          }
        }
      }
    }

    # PROCESSORS
    dynamic "processors" {
      for_each = length(try(each.value.config.processors, [])) > 0 ? [1] : []
      content {
        # parse_json processor(s)
        dynamic "parse_json" {
          for_each = try([for p in each.value.config.processors : p if try(p.type, "") == "parse_json"], [])
          content {
            id      = try(parse_json.value.id, null)
            include = try(parse_json.value.include, null)
            field   = try(parse_json.value.field, null)
            inputs  = try(parse_json.value.inputs, null)
          }
        }

        # filter processor(s)
        dynamic "filter" {
          for_each = try([for p in each.value.config.processors : p if try(p.type, "") == "filter"], [])
          content {
            id      = try(filter.value.id, null)
            include = try(filter.value.include, null)
            exclude = try(filter.value.exclude, null)
            inputs  = try(filter.value.inputs, null)
          }
        }

        # sample processor(s)
        dynamic "sample" {
          for_each = try([for p in each.value.config.processors : p if try(p.type, "") == "sample"], [])
          content {
            id     = try(sample.value.id, null)
            rate   = try(sample.value.rate, null)
            inputs = try(sample.value.inputs, null)
          }
        }
      }
    }

    # DESTINATIONS
    dynamic "destinations" {
      for_each = length(try(each.value.config.destinations, [])) > 0 ? [1] : []
      content {
        dynamic "datadog_logs" {
          for_each = try([for d in each.value.config.destinations : d if try(d.type, "") == "datadog_logs"], [])
          content {
            id     = try(datadog_logs.value.id, null)
            inputs = try(datadog_logs.value.inputs, null)
          }
        }
      }
    }
  }
}
