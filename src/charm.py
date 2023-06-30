#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the SD-Core Graphical User Interface."""

import logging

from charms.traefik_k8s.v1.ingress import (  # type: ignore[import]
    IngressPerAppRequirer,
    IngressPerAppRevokedEvent,
)
from jinja2 import Environment, FileSystemLoader
from ops.charm import CharmBase
from ops.framework import EventBase
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus
from ops.pebble import Layer

logger = logging.getLogger(__name__)

WEBUI_RELATION_NAME = "webui-api"
BASE_CONFIG_PATH = "/etc/config"  # TODO: Change when properly tested.
CONFIG_FILE_NAME = "sdcoreConfig.ts"
APPLICATION_PORT = 3000
INGRESS_RELATION_NAME = "ingress"


class SDCoreGUIOperatorCharm(CharmBase):
    """Main class to describe juju event handling for the SD-Core GUI operator."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container_name = self._service_name = "gui"
        self._container = self.unit.get_container(self._container_name)

        self.ingress = IngressPerAppRequirer(
            self,
            relation_name=INGRESS_RELATION_NAME,
            port=APPLICATION_PORT,
            strip_prefix=True,
        )

        self.framework.observe(self.on.gui_pebble_ready, self._configure_sdcore_gui)
        self.framework.observe(self.on.config_changed, self._configure_sdcore_gui)

        self.framework.observe(self.ingress.on.ready, self._configure_sdcore_gui)
        self.framework.observe(self.ingress.on.revoked, self._on_ingress_revoked)

    def _configure_sdcore_gui(self, event: EventBase) -> None:
        """Add Pebble layer and manages Juju unit status.

        Args:
            event (EventBase): Juju event.
        """
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for container to be ready")
            return
        if not self._storage_is_attached():
            self.unit.status = WaitingStatus("Waiting for the storage to be attached")
            event.defer()
            return
        if not self._ingress_relation_is_created():
            self.unit.status = BlockedStatus("Waiting for `ingress` relation to be created")
            return
        restart = self._update_config_file()
        self._configure_pebble(restart=restart)
        self.unit.status = ActiveStatus()

    def _configure_pebble(self, restart: bool = False) -> None:
        """Configure the Pebble layer.

        Args:
            restart (bool): Whether to restart the Pebble service. Defaults to False.
        """
        self._container.add_layer(self._container_name, self._pebble_layer, combine=True)
        if restart:
            self._container.restart(self._service_name)
            logger.info("Restarted container %s", self._service_name)
            return
        self._container.replan()

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
        content = self._render_config_file(
            webui_endpoint=self.config["webui-endpoint"],
            plmn_id=self.config["plmn-id"],
            site_info=self.config["device-group-site-info"],
            ip_domain_name=self.config["device-group-ip-domain-name"],
            dnn=self.config["device-group-dnn"],
            ue_ip_pool=self.config["device-group-ue-ip-pool"],
            dns_primary=self.config["device-group-dns-primary"],
            mtu=self.config["device-group-mtu"],
            dnn_mbr_uplink=self.config["device-group-dnn-mbr-uplink"],
            dnn_mbr_downlink=self.config["device-group-dnn-mbr-downlink"],
            traffic_class_name=self.config["device-group-traffic-class-name"],
            arp=self.config["device-group-traffic-class-arp"],
            pdb=self.config["device-group-traffic-class-pdb"],
            pelr=self.config["device-group-traffic-class-pelr"],
            qci=self.config["device-group-traffic-class-qci"],
            network_slice_name=self.config["network-slice-name"],
            sst=self.config["network-slice-sst"],
            sd=self.config["network-slice-sd"],
            site_device_group=self.config["network-slice-device-group"],
            site_name=self.config["network-slice-site-name"],
            gnodeb_name=self.config["network-slice-gnb-name"],
            gnodeb_tac=self.config["network-slice-gnb-tac"],
            upf_name=self.config["network-slice-upf-name"],
            upf_port=self.config["network-slice-upf-port"],
        )
        if not self._config_file_is_written() or not self._config_file_content_matches(
            content=content
        ):
            self._write_config_file(content=content)
            return True
        return False

    def _render_config_file(
        self,
        *,
        webui_endpoint: str,
        plmn_id: str,
        site_info: str,
        ip_domain_name: str,
        dnn: str,
        ue_ip_pool: str,
        dns_primary: str,
        mtu: str,
        dnn_mbr_uplink: str,
        dnn_mbr_downlink: str,
        traffic_class_name: str,
        arp: str,
        pdb: str,
        pelr: str,
        qci: str,
        network_slice_name: str,
        sst: str,
        sd: str,
        site_device_group: str,
        site_name: str,
        gnodeb_name: str,
        gnodeb_tac: str,
        upf_name: str,
        upf_port: str,
    ) -> str:
        """Render the config file content.

        Args:
            config_dict (dict): Dictionary with all the necessary configuration parameters.

        Returns:
            str: Config file content.
        """
        jinja2_env = Environment(loader=FileSystemLoader("src/templates"))
        template = jinja2_env.get_template(f"{CONFIG_FILE_NAME}.j2")
        return template.render(
            webui_endpoint=webui_endpoint,
            plmn_id=plmn_id,
            site_info=site_info,
            ip_domain_name=ip_domain_name,
            dnn=dnn,
            ue_ip_pool=ue_ip_pool,
            dns_primary=dns_primary,
            mtu=mtu,
            dnn_mbr_uplink=dnn_mbr_uplink,
            dnn_mbr_downlink=dnn_mbr_downlink,
            traffic_class_name=traffic_class_name,
            arp=arp,
            pdb=pdb,
            pelr=pelr,
            qci=qci,
            network_slice_name=network_slice_name,
            sst=sst,
            sd=sd,
            site_device_group=site_device_group,
            site_name=site_name,
            gnodeb_name=gnodeb_name,
            gnodeb_tac=gnodeb_tac,
            upf_name=upf_name,
            upf_port=upf_port,
        )

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

    def _ingress_relation_is_created(self) -> bool:
        """Return whether ingress Juju relation was crated.

        Returns:
            bool: Whether the ingress relation was created.
        """
        return bool(self.model.get_relation(INGRESS_RELATION_NAME))

    def _on_ingress_revoked(self, event: IngressPerAppRevokedEvent):
        logger.info("This app no longer has ingress")

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
                        "command": "node server.js",
                    },
                },
            }
        )


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreGUIOperatorCharm)
