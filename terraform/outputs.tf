# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.nms.name
}

output "requires" {
  value = {
    auth_database      = "auth_database"
    common_database    = "common_database"
    certificates       = "certificates"
    fiveg_gnb_identity = "fiveg_gnb_identity"
    fiveg_n4           = "fiveg_n4"
    ingress            = "ingress"
    logging            = "logging"
  }
}

output "provides" {
  value = {
    sdcore_config = "sdcore_config"
  }
}
