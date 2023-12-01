# SD-Core NMS Operator (k8s)
[![CharmHub Badge](https://charmhub.io/sdcore-nms/badge.svg)](https://charmhub.io/sdcore-nms)

Charmed Operator for the SD-Core Network Management System (NMS).

## Usage

```bash
juju deploy sdcore-nms --channel=edge
```

## Integrate

```bash
juju deploy traefik-k8s --trust --config external_hostname=<your hostname> --config routing_mode=subdomain
juju deploy sdcore-upf --channel=edge --trust
juju deploy mongodb-k8s --trust --channel=5/edge
juju deploy sdcore-webui --channel=edge
juju deploy sdcore-gnbsim --trust --channel=edge
juju integrate mongodb-k8s sdcore-webui
juju integrate sdcore-nms:ingress traefik-k8s:ingress
juju integrate sdcore-nms:fiveg_n4 sdcore-upf:fiveg_n4
juju integrate sdcore-nms:sdcore-management sdcore-webui:sdcore-management
juju integrate sdcore-nms:fiveg_gnb_identity sdcore-gnbsim:fiveg_gnb_identity
```

You should now be able to access the NMS at `https://<model name>-sdcore-nms.<your hostname>`

## Image

**sdcore-nms**: ghcr.io/canonical/sdcore-nms:0.2.0
