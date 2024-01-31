output "nms_application_name" {
  description = "Name of the deployed application."
  value       = juju_application.nms.name
}