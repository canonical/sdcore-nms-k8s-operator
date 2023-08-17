#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the SD-Core Graphical User Interface."""

import logging

from charms.observability_libs.v1.kubernetes_service_patch import (  # type: ignore[import]
    KubernetesServicePatch,
)
from charms.traefik_k8s.v1.ingress import IngressPerAppRequirer  # type: ignore[import]
from lightkube.models.core_v1 import ServicePort
from ops.charm import CharmBase
from ops.framework import EventBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus
from ops.pebble import Layer

logger = logging.getLogger(__name__)

GUI_PORT = 3000


class SDCoreGUIOperatorCharm(CharmBase):
    """Main class to describe juju event handling for the SD-Core GUI operator."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container_name = "gui"
        self._service_name = "sdcore-gui"
        self._container = self.unit.get_container(self._container_name)
        self._service_patcher = KubernetesServicePatch(
            charm=self,
            ports=[
                ServicePort(name="gui", port=GUI_PORT),
            ],
        )
        self.ingress = IngressPerAppRequirer(
            charm=self,
            port=GUI_PORT,
            relation_name="ingress",
            strip_prefix=True,
        )

        self.framework.observe(self.on.gui_pebble_ready, self._configure_sdcore_gui)
        self.framework.observe(self.on.config_changed, self._configure_sdcore_gui)

    def _configure_sdcore_gui(self, event: EventBase) -> None:
        """Add Pebble layer and manages Juju unit status.

        Args:
            event (EventBase): Juju event.
        """
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for container to be ready")
            event.defer()
            return
        if not self._config_is_valid():
            self.unit.status = BlockedStatus("Config is not valid")
            event.defer()
            return
        self._configure_pebble()
        self.unit.status = ActiveStatus()

    def _config_is_valid(self) -> bool:
        """Return whether the config is valid."""
        if not self._webui_url_is_set():
            return False
        if not self._upf_hostname_is_set():
            return False
        if not self._upf_port_is_set():
            return False
        return True

    def _webui_url_is_set(self) -> bool:
        """Return whether the webui endpoint is set.

        Return:
            bool: Whether the webui endpoint is set.
        """
        return self.config.get("webui-endpoint", "") != ""

    def _upf_hostname_is_set(self) -> bool:
        """Return whether the UPF hostname is set.

        Return:
            bool: Whether the UPF hostname is set.
        """
        return self.config.get("upf-hostname", "") != ""

    def _upf_port_is_set(self) -> bool:
        """Return whether the UPF port is set.

        Return:
            bool: Whether the UPF port is set.
        """
        return self.config.get("upf-port", "") != ""

    def _configure_pebble(self, restart: bool = False) -> None:
        """Configure the Pebble layer.

        Args:
            restart (bool): Whether to restart the Pebble service. Defaults to False.
        """
        plan = self._container.get_plan()
        layer = self._pebble_layer
        if plan.services != layer.services or restart:
            self._container.add_layer(self._container_name, layer, combine=True)
            self._container.restart(self._service_name)

    @property
    def _pebble_layer(self) -> Layer:
        """Return pebble layer for the charm.

        Return:
            Layer: Pebble Layer.
        """
        return Layer(
            {
                "summary": "GUI layer",
                "description": "Pebble config layer for the GUI",
                "services": {
                    self._service_name: {
                        "override": "replace",
                        "startup": "enabled",
                        "command": "/bin/bash -c 'cd /app && npm run start'",
                        "environment": {
                            "WEBUI_ENDPOINT": self.config["webui-endpoint"],
                            "UPF_HOSTNAME": self.config["upf-hostname"],
                            "UPF_PORT": self.config["upf-port"],
                        },
                    },
                },
            }
        )


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreGUIOperatorCharm)
