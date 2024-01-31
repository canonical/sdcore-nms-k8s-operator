resource "juju_application" "nms" {
  name  = "nms"
  model = var.model_name

  charm {
    name    = "sdcore-nms-k8s"
    channel = var.channel
  }
  units = 1
  trust = true
}

resource "juju_integration" "nms-traefik" {
  model = var.model_name

  application {
    name     = juju_application.nms.name
    endpoint = "ingress"
  }

  application {
    name     = var.traefik_application_name
    endpoint = "ingress"
  }
}

resource "juju_integration" "nms-webui" {
  model = var.model_name

  application {
    name     = juju_application.nms.name
    endpoint = "sdcore-management"
  }

  application {
    name     = var.webui_application_name
    endpoint = "sdcore-management"
  }
}



