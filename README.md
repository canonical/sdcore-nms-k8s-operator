# sdcore-nms-operator

Charmed Operator for SD-Core's NMS.

## Usage

```bash
juju deploy sdcore-nms --channel=edge --config webui-endpoint=<webui endpoint>
```

## Integrate with ingress

```bash
juju deploy traefik-k8s --trust --config external_hostname=<your hostname> --config routing_mode=subdomain
juju deploy sdcore-upf --channel=edge --trust
juju integrate sdcore-nms:ingress traefik-k8s:ingress
juju integrate sdcore-nms:fiveg_n4 sdcore-upf:fiveg_n4
```

You should now be able to access the NMS at `https://<model name>-sdcore-nms.<your hostname>`

## Image

**sdcore-nms**: ghcr.io/canonical/sdcore-nms:0.1
