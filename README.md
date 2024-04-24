# SD-Core NMS Operator (k8s)
[![CharmHub Badge](https://charmhub.io/sdcore-nms-k8s/badge.svg)](https://charmhub.io/sdcore-nms-k8s)

Charmed Operator for the SD-Core Network Management System (NMS) for K8s.

## Usage

```bash
juju deploy sdcore-nms-k8s --channel=edge
```

## Integrate

```bash
juju deploy traefik-k8s --trust --config external_hostname=<your hostname> --config routing_mode=subdomain
juju deploy sdcore-upf-k8s --channel=1.4/edge --trust
juju deploy mongodb-k8s --trust --channel=6/beta
juju deploy sdcore-webui-k8s --channel=1.4/edge
juju deploy sdcore-gnbsim-k8s --trust --channel=1.4/edge
juju integrate mongodb-k8s sdcore-webui-k8s
juju integrate sdcore-nms-k8s:ingress traefik-k8s:ingress
juju integrate sdcore-nms-k8s:fiveg_n4 sdcore-upf-k8s:fiveg_n4
juju integrate sdcore-nms-k8s:sdcore-management sdcore-webui-k8s:sdcore-management
juju integrate sdcore-nms-k8s:fiveg_gnb_identity sdcore-gnbsim-k8s:fiveg_gnb_identity
```

You should now be able to access the NMS at `https://<model name>-sdcore-nms-k8s.<your hostname>`

## Image

**sdcore-nms**: ghcr.io/canonical/sdcore-nms:0.2.0

