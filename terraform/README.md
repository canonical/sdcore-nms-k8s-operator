# SD-Core NMS K8s Terraform Module

This SD-Core NMS K8s Terraform module aims to deploy the [sdcore-nms-k8s charm](https://charmhub.io/sdcore-nms-k8s) via Terraform.

## Getting Started

### Prerequisites

The following software and tools needs to be installed and should be running in the local environment. Please [set up your environment](https://discourse.charmhub.io/t/set-up-your-development-environment-with-microk8s-for-juju-terraform-provider/13109) before deployment.

- `microk8s`
- `juju 3.x`
- `terrafom`

### Module structure

- **main.tf** - Defines the Juju application to be deployed.
- **variables.tf** - Allows customization of the deployment. Except for exposing the deployment options (Juju model name, channel or application name) also models the charm configuration.
- **output.tf** - Responsible for integrating the module with other Terraform modules, primarily by defining potential integration endpoints (charm integrations), but also by exposing the application name.
- **terraform.tf** - Defines the Terraform provider.

## Using sdcore-nms-k8s base module in higher level modules

If you want to use `sdcore-nms-k8s` base module as part of your Terraform module, import it like shown below.

```text
module "sdcore-nms-k8s" {
  source                 = "git::https://github.com/canonical/sdcore-nms-k8s-operator//terraform"
  model_name             = "juju_model_name"  
  # Optional Configurations
  # channel                        = "put the Charm channel here" 
  # app_name                       = "put the application name here" 
}
```

Create the integrations, for instance:

```text
resource "juju_integration" "nms-sdcore-management" {
  model = var.model_name

  application {
    name     = module.nms.app_name
    endpoint = module.nms.sdcore_management_endpoint
  }

  application {
    name     = module.webui.app_name
    endpoint = module.webui.sdcore_management_endpoint
  }
}
```

Please check the available [integration pairs](https://charmhub.io/sdcore-nms-k8s/integrations).

[Terraform](https://www.terraform.io/)

[Terraform Juju provider](https://registry.terraform.io/providers/juju/juju/latest)
