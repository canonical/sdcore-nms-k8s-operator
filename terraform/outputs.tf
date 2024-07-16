# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  description = "Name of the deployed application."
  value       = juju_application.sdcore-nms-k8s.name
}

# Required integration endpoints

output "ingress_endpoint" {
  description = "Name of the endpoint to integrate with ingress interface."
  value       = "ingress"
}

output "fiveg_gnb_identity_endpoint" {
  description = "Name of the endpoint to integrate with fiveg_gnb_identity interface."
  value       = "fiveg_gnb_identity"
}

output "fiveg_n4_endpoint" {
  description = "Name of the endpoint to integrate with fiveg_n4 interface."
  value       = "fiveg_n4"
}

output "common_database_endpoint" {
  description = "Name of the endpoint to integrate with MongoDB for common database using mongodb_client interface."
  value       = "common_database"
}

output "auth_database_endpoint" {
  description = "Name of the endpoint to integrate with MongoDB for authentication database using mongodb_client interface."
  value       = "auth_database"
}

output "logging_endpoint" {
  description = "Name of the endpoint used to integrate with the Logging provider."
  value       = "logging"
}

# Provided integration endpoints

output "sdcore_config_endpoint" {
  description = "Name of the endpoint to provide `sdcore_config` interface."
  value       = "sdcore-config"
}