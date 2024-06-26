#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the SD-Core Graphical User Interface for K8s."""

import json
import logging
from typing import List, Tuple

from charms.loki_k8s.v1.loki_push_api import LogForwarder  # type: ignore[import]
from charms.sdcore_gnbsim_k8s.v0.fiveg_gnb_identity import (  # type: ignore[import]
    GnbIdentityRequires,
)
from charms.sdcore_upf_k8s.v0.fiveg_n4 import N4Requires  # type: ignore[import]
from charms.sdcore_webui_k8s.v0.sdcore_management import (  # type: ignore[import]
    SdcoreManagementRequires,
)
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer  # type: ignore[import]
from ops import (
    ActiveStatus,
    BlockedStatus,
    CollectStatusEvent,
    ModelError,
    WaitingStatus,
)
from ops.charm import CharmBase
from ops.framework import EventBase
from ops.main import main
from ops.pebble import Layer

logger = logging.getLogger(__name__)

FIVEG_N4_RELATION_NAME = "fiveg_n4"
GNB_IDENTITY_RELATION_NAME = "fiveg_gnb_identity"
NMS_PORT = 3000
SDCORE_MANAGEMENT_RELATION_NAME = "sdcore-management"
CONFIG_DIR_PATH = "/nms/config"
GNB_CONFIG_PATH = f"{CONFIG_DIR_PATH}/gnb_config.json"
UPF_CONFIG_PATH = f"{CONFIG_DIR_PATH}/upf_config.json"
LOGGING_RELATION_NAME = "logging"
WORKLOAD_VERSION_FILE_NAME = "/etc/workload-version"


class SDCoreNMSOperatorCharm(CharmBase):
    """Main class to describe juju event handling for the SD-Core NMS operator for K8s."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container_name = self._service_name = "nms"
        self._container = self.unit.get_container(self._container_name)
        self.fiveg_n4 = N4Requires(charm=self, relation_name=FIVEG_N4_RELATION_NAME)
        self._gnb_identity = GnbIdentityRequires(self, GNB_IDENTITY_RELATION_NAME)
        self._sdcore_management = SdcoreManagementRequires(self, SDCORE_MANAGEMENT_RELATION_NAME)
        self.unit.set_ports(NMS_PORT)
        self.ingress = IngressPerAppRequirer(
            charm=self,
            port=NMS_PORT,
            relation_name="ingress",
            strip_prefix=True,
        )
        self._logging = LogForwarder(charm=self, relation_name=LOGGING_RELATION_NAME)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)
        self.framework.observe(self.on.nms_pebble_ready, self._configure_sdcore_nms)
        self.framework.observe(self.on.update_status, self._configure_sdcore_nms)
        self.framework.observe(self.fiveg_n4.on.fiveg_n4_available, self._configure_sdcore_nms)
        self.framework.observe(
            self._sdcore_management.on.management_url_available,
            self._configure_sdcore_nms,
        )
        self.framework.observe(
            self._gnb_identity.on.fiveg_gnb_identity_available,
            self._configure_sdcore_nms,
        )
        self.framework.observe(
            self.on[GNB_IDENTITY_RELATION_NAME].relation_broken,
            self._configure_sdcore_nms,
        )
        self.framework.observe(
            self.on[FIVEG_N4_RELATION_NAME].relation_broken,
            self._configure_sdcore_nms,
        )

    def _configure_sdcore_nms(self, event: EventBase) -> None:
        """Add Pebble layer and manages Juju unit status.

        Args:
            event (EventBase): Juju event.
        """
        if not self._container.can_connect():
            return
        if not self._container.exists(path=CONFIG_DIR_PATH):
            return
        self._configure_upf_information()
        self._configure_gnb_information()
        if not self.model.relations.get(SDCORE_MANAGEMENT_RELATION_NAME):
            return
        if not self._sdcore_management.management_url:
            return
        self._configure_pebble()

    def _configure_pebble(self) -> None:
        """Configure the Pebble layer."""
        plan = self._container.get_plan()
        layer = self._pebble_layer
        if plan.services != layer.services:
            self._container.add_layer(self._container_name, layer, combine=True)
            self._container.restart(self._service_name)

    def _on_collect_unit_status(self, event: CollectStatusEvent):
        """Check the unit status and set to Unit when CollectStatusEvent is fired.

        Args:
            event: CollectStatusEvent
        """
        if not self._container.can_connect():
            event.add_status(WaitingStatus("Waiting for container to be ready"))
            logger.info("Waiting for container to be ready")
            return
        self.unit.set_workload_version(self._get_workload_version())
        if not self.model.relations.get(SDCORE_MANAGEMENT_RELATION_NAME):
            event.add_status(
                BlockedStatus(
                    f"Waiting for `{SDCORE_MANAGEMENT_RELATION_NAME}` relation to be created"
                )
            )
            logger.info(f"Waiting for `{SDCORE_MANAGEMENT_RELATION_NAME}` relation to be created")
            return
        if not self._sdcore_management.management_url:
            event.add_status(WaitingStatus("Waiting for webui management URL to be available"))
            logger.info("Waiting for webui management URL to be available")
            return
        if not self._container.exists(path=CONFIG_DIR_PATH):
            event.add_status(WaitingStatus("Waiting for storage to be attached"))
            logger.info("Waiting for storage to be attached")
            return
        if not self._container.exists(path=UPF_CONFIG_PATH):
            event.add_status(WaitingStatus("Waiting for UPF config file to be stored"))
            logger.info("Waiting for UPF config file to be stored")
            return
        if not self._container.exists(path=GNB_CONFIG_PATH):
            event.add_status(WaitingStatus("Waiting for GNB config file to be stored"))
            logger.info("Waiting for GNB config file to be stored")
            return
        if not self._nms_service_is_running():
            event.add_status(WaitingStatus("Waiting for NMS service to start"))
            logger.info("Waiting for NMS service to start")
            return

        event.add_status(ActiveStatus())

    def _nms_service_is_running(self) -> bool:
        """Check if the NMS service is running."""
        try:
            self._container.get_service(service_name=self._service_name)
        except ModelError:
            return False
        return True

    def _configure_upf_information(self) -> None:
        """Create the UPF config file.

        The config file is generated based on the various `fiveg_n4` relations and their content.
        """
        if not self.model.relations.get(FIVEG_N4_RELATION_NAME):
            logger.info("Relation %s not available", FIVEG_N4_RELATION_NAME)
        upf_existing_content = self._get_existing_config_file(path=UPF_CONFIG_PATH)
        upf_config_content = self._get_upf_config()
        if not upf_existing_content or not config_file_content_matches(
            existing_content=upf_existing_content,
            new_content=upf_config_content,
        ):
            self._push_upf_config_file_to_workload(upf_config_content)

    def _configure_gnb_information(self) -> None:
        """Create the GNB config file.

        The config file is generated based on the various `fiveg_gnb_identity` relations
        and their content.
        """
        if not self.model.relations.get(GNB_IDENTITY_RELATION_NAME):
            logger.info("Relation %s not available", GNB_IDENTITY_RELATION_NAME)
        gnb_existing_content = self._get_existing_config_file(path=GNB_CONFIG_PATH)
        gnb_config_content = self._get_gnb_config()
        if not gnb_existing_content or not config_file_content_matches(
            existing_content=gnb_existing_content,
            new_content=gnb_config_content,
        ):
            self._push_gnb_config_file_to_workload(gnb_config_content)

    def _get_existing_config_file(self, path: str) -> str:
        """Get the existing config file from the workload.

        Args:
            path (str): Path to the config file.

        Returns:
            str: Content of the config file.
        """
        if self._container.exists(path=path):
            existing_content_stringio = self._container.pull(path=path)
            return existing_content_stringio.read()
        return ""

    def _get_upf_host_port_list(self) -> List[Tuple[str, int]]:
        """Get the list of UPF hosts and ports from the `fiveg_n4` relation data bag.

        Returns:
            List[Tuple[str, int]]: List of UPF hostnames and ports.
        """
        upf_host_port_list = []
        for fiveg_n4_relation in self.model.relations.get(FIVEG_N4_RELATION_NAME, []):
            if not fiveg_n4_relation.app:
                logger.warning(
                    "Application missing from the %s relation data",
                    FIVEG_N4_RELATION_NAME,
                )
                continue
            port = fiveg_n4_relation.data[fiveg_n4_relation.app].get("upf_port", "")
            hostname = fiveg_n4_relation.data[fiveg_n4_relation.app].get("upf_hostname", "")
            if hostname and port:
                upf_host_port_list.append((hostname, int(port)))
        return upf_host_port_list

    def _get_gnb_name_tac_list(self) -> List[Tuple[str, int]]:
        """Get a list gnb_name and TAC from the `fiveg_gnb_identity` relation data bag.

        Returns:
            List[Tuple[str, int]]: List of gnb_name and TAC.
        """
        gnb_name_tac_list = []
        for gnb_identity_relation in self.model.relations.get(GNB_IDENTITY_RELATION_NAME, []):
            if not gnb_identity_relation.app:
                logger.warning(
                    "Application missing from the %s relation data",
                    GNB_IDENTITY_RELATION_NAME,
                )
                continue
            gnb_name = gnb_identity_relation.data[gnb_identity_relation.app].get("gnb_name", "")
            gnb_tac = gnb_identity_relation.data[gnb_identity_relation.app].get("tac", "")
            if gnb_name and gnb_tac:
                gnb_name_tac_list.append((gnb_name, int(gnb_tac)))
        return gnb_name_tac_list

    def _get_upf_config(self) -> str:
        """Get the UPF configuration for the NMS in a json.

        Returns:
            str: Json representation of list of dictionaries,
                each containing UPF hostname and port.
        """
        upf_host_port_list = self._get_upf_host_port_list()

        upf_config = []
        for upf_hostname, upf_port in upf_host_port_list:
            upf_config_entry = {
                "hostname": upf_hostname,
                "port": str(upf_port),
            }
            upf_config.append(upf_config_entry)
        return json.dumps(upf_config, sort_keys=True)

    def _get_gnb_config(self) -> str:
        """Get the GNB configuration for the NMS in a json format.

        Returns:
            str: Json representation of list of dictionaries,
                each containing GNB names and tac.
        """
        gnb_name_tac_list = self._get_gnb_name_tac_list()

        gnb_config = []
        for gnb_name, gnb_tac in gnb_name_tac_list:
            gnb_conf_entry = {"name": gnb_name, "tac": str(gnb_tac)}
            gnb_config.append(gnb_conf_entry)

        return json.dumps(gnb_config, sort_keys=True)

    def _get_workload_version(self) -> str:
        """Return the workload version.

        Checks for the presence of /etc/workload-version file
        and if present, returns the contents of that file. If
        the file is not present, an empty string is returned.

        Returns:
            string: A human readable string representing the
            version of the workload
        """
        if self._container.exists(path=f"{WORKLOAD_VERSION_FILE_NAME}"):
            version_file_content = self._container.pull(
                path=f"{WORKLOAD_VERSION_FILE_NAME}"
            ).read()
            return version_file_content
        return ""

    def _push_upf_config_file_to_workload(self, content: str):
        """Push the upf config files to the NMS workload."""
        self._container.push(path=UPF_CONFIG_PATH, source=content)
        logger.info("Pushed %s config file", UPF_CONFIG_PATH)

    def _push_gnb_config_file_to_workload(self, content: str):
        """Push the gnb config files to the NMS workload."""
        self._container.push(path=GNB_CONFIG_PATH, source=content)
        logger.info("Pushed %s config file", GNB_CONFIG_PATH)

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
        """Return environment variables for the nms service.

        Returns:
            dict: Environment variables.
        """
        return {
            "WEBUI_ENDPOINT": self._sdcore_management.management_url,
            "UPF_CONFIG_PATH": UPF_CONFIG_PATH,
            "GNB_CONFIG_PATH": GNB_CONFIG_PATH,
        }


def config_file_content_matches(existing_content: str, new_content: str) -> bool:
    """Return whether two config file contents match."""
    try:
        existing_content_list = json.loads(existing_content)
        new_content_list = json.loads(new_content)
        return existing_content_list == new_content_list
    except json.JSONDecodeError:
        return False


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreNMSOperatorCharm)
