variable "model_name" {
  description = "Name of Juju model to deploy application to."
  type        = string
  default     = ""
}

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "1.3/edge"
}

variable "upf_application_name" {
  description = "The name of the UPF application."
  type        = string
  default     = ""
}

variable "traefik_application_name" {
  description = "Name of the Traefik application"
  type        = string
  default     = ""
}

variable "webui_application_name" {
  description = "The name of the WEBUI application."
  type        = string
  default     = ""
}

variable "gnb_application_name" {
  description = "The name of the GNB application."
  type        = string
  default     = ""
}
