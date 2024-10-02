# SD-Core NMS K8s Terraform module

This folder contains a base [Terraform][Terraform] module for the sdcore-nms-k8s charm.

The module uses the [Terraform Juju provider][Terraform Juju provider] to model the charm deployment onto any Kubernetes environment managed by [Juju][Juju].

The base module is not intended to be deployed in separation (it is possible though), but should rather serve as a building block for higher level modules.

## Module structure

- **main.tf** - Defines the Juju application to be deployed.
- **variables.tf** - Allows customization of the deployment options (Juju model name, channel or application name).
- **output.tf** - Responsible for integrating the module with other Terraform modules, primarily by defining potential integration endpoints (charm integrations), but also by exposing the application name.
- **versions.tf** - Defines the Terraform provider.

## Using sdcore-nms-k8s base module in higher level modules

If you want to use `sdcore-nms-k8s` base module as part of your Terraform module, import it like shown below.

```text
data "juju_model" "my_model" {
  name = "my_model_name"
}

module "sdcore-nms-k8s" {
  source                 = "git::https://github.com/canonical/sdcore-nms-k8s-operator//terraform"
  model = juju_model.my_model.name
  # Optional Configurations
  # channel                        = "put the Charm channel here" 
  # app_name                       = "put the application name here" 
}
```

Create the integrations, for instance:

```text
resource "juju_integration" "nms-gnb" {
  model = var.model

  application {
    name     = module.nms.app_name
    endpoint = module.nms.requires.fiveg_gnb_identity
  }

  application {
    name     = module.gnbsim.app_name
    endpoint = module.gnbsim.provides.fiveg_gnb_identity
  }
}
```

The complete list of available integrations can be found [here][nms-integrations].

[Terraform]: https://www.terraform.io/
[Terraform Juju provider]: https://registry.terraform.io/providers/juju/juju/latest
[Juju]: https://juju.is
[nms-integrations]: https://charmhub.io/sdcore-nms-k8s/integrations
