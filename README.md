# Aether SD-Core NMS Operator (k8s)
[![CharmHub Badge](https://charmhub.io/sdcore-nms-k8s/badge.svg)](https://charmhub.io/sdcore-nms-k8s)

Charmed Operator for the Aether SD-Core Network Management System (NMS) for K8s.

## Usage

```bash
juju deploy sdcore-nms-k8s --channel=1.5/edge
```

## Integrate

```bash
juju deploy traefik-k8s --trust --config external_hostname=<your hostname> --config routing_mode=subdomain
juju deploy sdcore-upf-k8s --channel=1.5/edge --trust
juju deploy mongodb-k8s --trust --channel=6/beta
juju deploy sdcore-gnbsim-k8s --trust --channel=1.5/edge
juju deploy grafana-agent-k8s --trust --channel=latest/stable
juju integrate sdcore-nms-k8s:common_database mongodb-k8s
juju integrate sdcore-nms-k8s:auth_database mongodb-k8s
juju integrate sdcore-nms-k8s:ingress traefik-k8s:ingress
juju integrate sdcore-nms-k8s:fiveg_n4 sdcore-upf-k8s:fiveg_n4
juju integrate sdcore-nms-k8s:fiveg_gnb_identity sdcore-gnbsim-k8s:fiveg_gnb_identity
juju integrate sdcore-nms-k8s:logging grafana-agent-k8s
```

You should now be able to access the NMS at `https://<model name>-sdcore-nms-k8s.<your hostname>`

## Image

**sdcore-nms**: ghcr.io/canonical/sdcore-nms:1.0.0
