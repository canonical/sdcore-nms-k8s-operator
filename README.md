<div align="center">
  <img src="./icon.svg" alt="ONF Icon" width="200" height="200">
</div>
<div align="center">
  <h1>SD-Core GUI Operator</h1>
</div>

# sdcore-gui-operator

Charmed Operator for SD-Core's Graphical User Interface.

## Usage

```bash
juju deploy sdcore-gui --channel=edge --config webui-endpoint=<webui endpoint>
```

## Integrate with ingress

```bash
juju deploy traefik-k8s --trust --config external_hostname=<your hostname> --config routing_mode=subdomain
juju integrate sdcore-gui:ingress traefik-k8s:ingress
```

You should now be able to access the GUI at `https://<model name>-sdcore-gui.<your hostname>`

## Image

**sdcore-gui**: ghcr.io/canonical/sdcore-gui:0.1
