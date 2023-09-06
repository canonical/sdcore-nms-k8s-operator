<div align="center">
  <img src="./icon.svg" alt="ONF Icon" width="200" height="200">
</div>
<div align="center">
  <h1>SD-Core NMS Operator</h1>
</div>

# sdcore-nms-operator

Charmed Operator for SD-Core's NMS.

## Usage

```bash
juju deploy sdcore-nms --channel=edge --config webui-endpoint=<webui endpoint>
```

## Integrate with ingress

```bash
juju deploy traefik-k8s --trust --config external_hostname=<your hostname> --config routing_mode=subdomain
juju integrate sdcore-nms:ingress traefik-k8s:ingress
```

You should now be able to access the NMS at `https://<model name>-sdcore-nms.<your hostname>`

## Image

**sdcore-nms**: ghcr.io/canonical/sdcore-nms:0.1
