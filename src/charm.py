#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the SD-Core Graphical User Interface."""

import logging

from charms.observability_libs.v1.kubernetes_service_patch import (  # type: ignore[import]
    KubernetesServicePatch,
)
from charms.sdcore_upf.v0.fiveg_n4 import N4Requires  # type: ignore[import]
from charms.traefik_k8s.v1.ingress import IngressPerAppRequirer  # type: ignore[import]
from lightkube.models.core_v1 import ServicePort
from ops.charm import CharmBase
from ops.framework import EventBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus
from ops.pebble import Layer

logger = logging.getLogger(__name__)

FIVEG_N4_RELATION_NAME = "fiveg_n4"
NMS_PORT = 3000


class SDCoreNMSOperatorCharm(CharmBase):
    """Main class to describe juju event handling for the SD-Core NMS operator."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container_name = "nms"
        self._service_name = "sdcore-nms"
        self._container = self.unit.get_container(self._container_name)
        self.fiveg_n4 = N4Requires(charm=self, relation_name=FIVEG_N4_RELATION_NAME)
        self._service_patcher = KubernetesServicePatch(
            charm=self,
            ports=[
                ServicePort(name="nms", port=NMS_PORT),
            ],
        )
        self.ingress = IngressPerAppRequirer(
            charm=self,
            port=NMS_PORT,
            relation_name="ingress",
            strip_prefix=True,
        )

        self.framework.observe(self.on.nms_pebble_ready, self._configure_sdcore_nms)
        self.framework.observe(self.on.config_changed, self._configure_sdcore_nms)
        self.framework.observe(self.fiveg_n4.on.fiveg_n4_available, self._configure_sdcore_nms)

    def _configure_sdcore_nms(self, event: EventBase) -> None:
        """Add Pebble layer and manages Juju unit status.

        Args:
            event (EventBase): Juju event.
        """
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for container to be ready")
            event.defer()
            return
        if not self.model.relations.get(FIVEG_N4_RELATION_NAME):
            self.unit.status = BlockedStatus(
                f"Waiting for `{FIVEG_N4_RELATION_NAME}` relation to be created"
            )
            return
        if not self._webui_url_is_set():
            self.unit.status = BlockedStatus("Invalid `webui-endpoint` config value")
            event.defer()
            return
        self._configure_pebble()
        self.unit.status = ActiveStatus()

    def _webui_url_is_set(self) -> bool:
        """Return whether the webui endpoint is set.

        Return:
            bool: Whether the webui endpoint is set.
        """
        return self.config.get("webui-endpoint", "") != ""

    def _configure_pebble(self) -> None:
        """Configure the Pebble layer."""
        plan = self._container.get_plan()
        layer = self._pebble_layer
        if plan.services != layer.services:
            self._container.add_layer(self._container_name, layer, combine=True)
            self._container.restart(self._service_name)

    def _get_upf_hostname(self) -> str:
        """Gets UPF hostname from the `fiveg_n4` relation data bag.

        Returns:
            str: UPF hostname
        """
        fiveg_n4_relation = self.model.get_relation(FIVEG_N4_RELATION_NAME)
        if not fiveg_n4_relation:
            raise RuntimeError(f"Relation {FIVEG_N4_RELATION_NAME} not available")
        if not fiveg_n4_relation.app:
            raise RuntimeError(
                f"Application missing from the {FIVEG_N4_RELATION_NAME} relation data"
            )
        return fiveg_n4_relation.data[fiveg_n4_relation.app]["upf_hostname"]

    def _get_upf_port(self) -> int:
        """Gets UPF's N4 port number from the `fiveg_n4` relation data bag.

        Returns:
            int: N4 port number
        """
        fiveg_n4_relation = self.model.get_relation(FIVEG_N4_RELATION_NAME)
        if not fiveg_n4_relation:
            raise RuntimeError(f"Relation {FIVEG_N4_RELATION_NAME} not available")
        if not fiveg_n4_relation.app:
            raise RuntimeError(
                f"Application missing from the {FIVEG_N4_RELATION_NAME} relation data"
            )
        return int(fiveg_n4_relation.data[fiveg_n4_relation.app]["upf_port"])

    @property
    def _pebble_layer(self) -> Layer:
        """Return pebble layer for the charm.

        Return:
            Layer: Pebble Layer.
        """
        return Layer(
            {
                "summary": "NMS layer",
                "description": "Pebble config layer for the NMS",
                "services": {
                    self._service_name: {
                        "override": "replace",
                        "startup": "enabled",
                        "command": "/bin/bash -c 'cd /app && npm run start'",
                        "environment": self._environment_variables,
                    },
                },
            }
        )

    @property
    def _environment_variables(self) -> dict:
        """Returns environment variables for the nms service.

        Returns:
            dict: Environment variables.
        """
        return {
            "WEBUI_ENDPOINT": self.config["webui-endpoint"],
            "UPF_HOSTNAME": self._get_upf_hostname(),
            "UPF_PORT": self._get_upf_port(),
        }


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreNMSOperatorCharm)
