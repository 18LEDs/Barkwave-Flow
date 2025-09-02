terraform {
  required_version = ">= 1.0"
  backend "pg" {}
  required_providers {
    datadog = {
      source  = "DataDog/datadog"
      version = ">= 3.36.0"
    }
  }
}
