#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the SD-Core Graphical User Interface."""

import logging

from charms.observability_libs.v1.kubernetes_service_patch import (  # type: ignore[import]
    KubernetesServicePatch,
)
from jinja2 import Environment, FileSystemLoader
from lightkube.models.core_v1 import ServicePort
from ops.charm import CharmBase
from ops.framework import EventBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus
from ops.pebble import Layer

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/etc/config"
CONFIG_FILE_NAME = "sdcoreConfig.ts"
GUI_PORT = 3000


def render_config_file(
    webui_endpoint: str,
    upf_hostname: str,
    upf_port: str,
) -> str:
    """Renders the SD-Core GUI configuration file content.

    Args:
        webui_endpoint: WebUI endpoint.
        upf_hostname: UPF hostname.
        upf_port: UPF port.

    Returns:
        str: Rendered configuration file content.
    """
    jinja2_env = Environment(loader=FileSystemLoader("src/templates"))
    template = jinja2_env.get_template(f"{CONFIG_FILE_NAME}.j2")
    return template.render(
        webui_endpoint=webui_endpoint,
        upf_hostname=upf_hostname,
        upf_port=upf_port,
    )


class SDCoreGUIOperatorCharm(CharmBase):
    """Main class to describe juju event handling for the SD-Core GUI operator."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container_name = self._service_name = "gui"
        self._container = self.unit.get_container(self._container_name)
        self._service_patcher = KubernetesServicePatch(
            charm=self,
            ports=[
                ServicePort(name="gui", port=GUI_PORT),
            ],
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
        if not self._storage_is_attached():
            self.unit.status = WaitingStatus("Waiting for the storage to be attached")
            event.defer()
            return
        if not self._config_is_valid():
            self.unit.status = BlockedStatus("Config is not valid")
            event.defer()
            return
        restart = self._update_config_file()
        self._configure_pebble(restart=restart)
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

    def _storage_is_attached(self) -> bool:
        """Return whether storage is attached to the workload container.

        Return:
            bool: Whether storage is attached.
        """
        return self._container.exists(path=BASE_CONFIG_PATH)

    def _update_config_file(self) -> bool:
        """Update config file.

        Write the config file if it does not exist or
        the content does not match.

        Return:
            bool: True if config file was updated, False otherwise.
        """
        content = render_config_file(
            webui_endpoint=self.config["webui-endpoint"],
            upf_hostname=self.config["upf-hostname"],
            upf_port=self.config["upf-port"],
        )
        if not self._config_file_is_written() or not self._config_file_content_matches(
            content=content
        ):
            self._write_config_file(content=content)
            return True
        return False

    def _write_config_file(self, content: str) -> None:
        """Write config file to workload.

        Args:
            content (str): Config file content.
        """
        self._container.push(
            path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}",
            source=content,
        )
        logger.info("Pushed: %s to workload.", CONFIG_FILE_NAME)

    def _config_file_is_written(self) -> bool:
        """Return whether the config file was written to the workload container.

        Returns:
            bool: Whether the config file was written.
        """
        return bool(self._container.exists(f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"))

    def _config_file_content_matches(self, content: str) -> bool:
        """Return whether the config file content matches the provided content.

        Args:
            content (str): Config file content.

        Return:
            bool: Whether the config file content matches.
        """
        existing_content = self._container.pull(path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}")
        return existing_content.read() == content

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
                        "command": "/bin/bash -c 'cd /client/standalone && node server.js'",
                    },
                },
            }
        )


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreGUIOperatorCharm)
