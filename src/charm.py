#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the Aether SD-Core Graphical User Interface for K8s."""

import logging
from ipaddress import IPv4Address
from subprocess import CalledProcessError, check_output
from typing import Optional

import requests  # type: ignore[import]
from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires  # type: ignore[import]
from charms.loki_k8s.v1.loki_push_api import LogForwarder  # type: ignore[import]
from charms.sdcore_gnbsim_k8s.v0.fiveg_gnb_identity import (  # type: ignore[import]
    GnbIdentityRequires,
)
from charms.sdcore_nms_k8s.v0.sdcore_config import (  # type: ignore[import]
    SdcoreConfigProvides,
)
from charms.sdcore_upf_k8s.v0.fiveg_n4 import N4Requires  # type: ignore[import]
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer  # type: ignore[import]
from jinja2 import Environment, FileSystemLoader
from ops import ActiveStatus, BlockedStatus, CollectStatusEvent, ModelError, WaitingStatus
from ops.charm import CharmBase, EventBase
from ops.main import main
from ops.pebble import Layer

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/nms/config" # "/nms/config"
CONFIG_FILE_NAME = "webuicfg.conf"
GNB_CONFIG_URL = "config/v1/inventory/gnb"
UPF_CONFIG_URL = "config/v1/inventory/upf"
WEBUI_CONFIG_PATH = f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"
WORKLOAD_VERSION_FILE_NAME = "/etc/workload-version"
AUTH_DATABASE_RELATION_NAME = "auth_database"
COMMON_DATABASE_RELATION_NAME = "common_database"
FIVEG_N4_RELATION_NAME = "fiveg_n4"
GNB_IDENTITY_RELATION_NAME = "fiveg_gnb_identity"
LOGGING_RELATION_NAME = "logging"
SDCORE_CONFIG_RELATION_NAME = "sdcore_config"
AUTH_DATABASE_NAME = "authentication"
COMMON_DATABASE_NAME = "free5gc"
GRPC_PORT = 9876
WEBUI_URL_PORT = 5000
WEBUI_SERVICE_NAME = "webui"
JSON_HEADER = {'Content-Type': 'application/json'}

def _get_pod_ip() -> Optional[str]:
    """Return the pod IP using juju client."""
    try:
        ip_address = check_output(["unit-get", "private-address"])
        return str(IPv4Address(ip_address.decode().strip())) if ip_address else None
    except (CalledProcessError, ValueError):
        return None


def render_config_file(
    common_database_name: str,
    common_database_url: str,
    auth_database_name: str,
    auth_database_url: str,
) -> str:
    """Render webui configuration file based on Jinja template."""
    jinja2_environment = Environment(loader=FileSystemLoader("src/templates/"))
    template = jinja2_environment.get_template("webuicfg.conf.j2")
    return template.render(
        common_database_name=common_database_name,
        common_database_url=common_database_url,
        auth_database_name=auth_database_name,
        auth_database_url=auth_database_url,
    )


class SDCoreNMSOperatorCharm(CharmBase):
    """Main class to describe juju event handling for the Aether SD-Core NMS operator for K8s."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.collect_unit_status, self._on_collect_unit_status)
        if not self.unit.is_leader():
            # NOTE: In cases where leader status is lost before the charm is
            # finished processing all teardown events, this prevents teardown
            # event code from running. Luckily, for this charm, none of the
            # teardown code is necessary to perform if we're removing the
            # charm.
            return
        self._container_name = self._service_name = "nms"
        self._container = self.unit.get_container(self._container_name)
        self._common_database = DatabaseRequires(
            self,
            relation_name=COMMON_DATABASE_RELATION_NAME,
            database_name=COMMON_DATABASE_NAME,
            extra_user_roles="admin",
        )
        self._auth_database = DatabaseRequires(
            self,
            relation_name=AUTH_DATABASE_RELATION_NAME,
            database_name=AUTH_DATABASE_NAME,
            extra_user_roles="admin",
        )
        self.unit.set_ports(GRPC_PORT, WEBUI_URL_PORT)
        self.ingress = IngressPerAppRequirer(
            charm=self,
            port=WEBUI_URL_PORT,
            relation_name="ingress",
            strip_prefix=True,
        )
        self.fiveg_n4 = N4Requires(charm=self, relation_name=FIVEG_N4_RELATION_NAME)
        self._gnb_identity = GnbIdentityRequires(self, GNB_IDENTITY_RELATION_NAME)
        self._logging = LogForwarder(charm=self, relation_name=LOGGING_RELATION_NAME)
        self._sdcore_config = SdcoreConfigProvides(self, SDCORE_CONFIG_RELATION_NAME)
        self.framework.observe(self.on.update_status, self._configure_sdcore_nms)
        self.framework.observe(self.on.nms_pebble_ready, self._configure_sdcore_nms)
        self.framework.observe(self.on.common_database_relation_joined, self._configure_sdcore_nms)
        self.framework.observe(self.on.auth_database_relation_joined, self._configure_sdcore_nms)
        self.framework.observe(
            self._common_database.on.database_created,
            self._configure_sdcore_nms
        )
        self.framework.observe(self._auth_database.on.database_created, self._configure_sdcore_nms)
        self.framework.observe(
            self._common_database.on.endpoints_changed,
            self._configure_sdcore_nms
        )
        self.framework.observe(
            self._auth_database.on.endpoints_changed,
            self._configure_sdcore_nms
        )
        self.framework.observe(self.on.sdcore_config_relation_joined, self._configure_sdcore_nms)
        self.framework.observe(self.fiveg_n4.on.fiveg_n4_available, self._configure_sdcore_nms)
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
        # Handling config changed event to publish the new url if the unit reboots and gets new IP
        self.framework.observe(self.on.config_changed, self._configure_sdcore_nms)

    def _configure_sdcore_nms(self, event: EventBase) -> None:
        """Handle Juju events.

        Whenever a Juju event is emitted, this method performs a couple of checks to make sure that
        the workload is ready to be started. Then, it configures the NMS workload,
        runs the Pebble services and expose the service information through charm's interface.
        """
        if not self._container.can_connect():
            return
        if not self._container.exists(path=BASE_CONFIG_PATH):
            return
        for relation in [COMMON_DATABASE_RELATION_NAME, AUTH_DATABASE_RELATION_NAME]:
            if not self._relation_created(relation):
                return
        if not self._common_database_resource_is_available():
            return
        if not self._auth_database_resource_is_available():
            return
        self._configure_gnbs()
        self._configure_upfs()
        desired_config_file = self._generate_webui_config_file()

        if config_update_required := self._is_config_update_required(desired_config_file):
            self._write_file_in_workload(WEBUI_CONFIG_PATH, desired_config_file)
        self._configure_workload(restart=config_update_required)
        self._publish_sdcore_config_url()

    def _on_collect_unit_status(self, event: CollectStatusEvent):   # noqa: C901
        """Check the unit status and set to Unit when CollectStatusEvent is fired.

        Also sets the workload version if present in rock.
        """
        if not self.unit.is_leader():
            # NOTE: In cases where leader status is lost before the charm is
            # finished processing all teardown events, this prevents teardown
            # event code from running. Luckily, for this charm, none of the
            # teardown code is necessary to perform if we're removing the
            # charm.
            event.add_status(BlockedStatus("Scaling is not implemented for this charm"))
            logger.info("Scaling is not implemented for this charm")
            return
        for relation in [COMMON_DATABASE_RELATION_NAME, AUTH_DATABASE_RELATION_NAME]:
            if not self._relation_created(relation):
                event.add_status(BlockedStatus(f"Waiting for {relation} relation to be created"))
                logger.info(f"Waiting for {relation} relation to be created")
                return
        if not self._common_database_resource_is_available():
            event.add_status(WaitingStatus("Waiting for the common database to be available"))
            logger.info("Waiting for the common database to be available")
            return
        if not self._auth_database_resource_is_available():
            event.add_status(WaitingStatus("Waiting for the auth database to be available"))
            logger.info("Waiting for the auth database to be available")
            return
        if not self._container.can_connect():
            event.add_status(WaitingStatus("Waiting for container to be ready"))
            logger.info("Waiting for container to be ready")
            return
        self.unit.set_workload_version(self._get_workload_version())

        if not self._container.exists(path=BASE_CONFIG_PATH):
            event.add_status(WaitingStatus("Waiting for storage to be attached"))
            logger.info("Waiting for storage to be attached")
            return
        if not self._webui_config_file_exists():
            event.add_status(WaitingStatus("Waiting for webui config file to be stored"))
            logger.info("Waiting for webui config file to be stored")
            return
        if not self._is_nms_service_running():
            event.add_status(WaitingStatus("Waiting for NMS service to start"))
            logger.info("Waiting for NMS service to start")
            return

        event.add_status(ActiveStatus())

    def _publish_sdcore_config_url(self) -> None:
        if not self._relation_created(SDCORE_CONFIG_RELATION_NAME):
            return
        if not self._is_nms_service_running():
            return
        self._sdcore_config.set_webui_url_in_all_relations(webui_url=self._webui_config_url)

    def _configure_workload(self, restart: bool = False) -> None:
        """Configure and restart the workload if required.

        This method detects the changes between the Pebble layer and the Pebble services.
        If a change is detected, it applies the desired configuration.
        Then, it restarts the workload if a restart is required.

        Args:
            restart (bool): Whether to restart the nms container.
        """
        plan = self._container.get_plan()
        if plan.services != self._pebble_layer.services:
            self._container.add_layer(self._container_name, self._pebble_layer, combine=True)
            self._container.replan()
            logger.info("New layer added: %s", self._pebble_layer)
        if restart:
            self._container.restart(self._service_name)
            logger.info("Restarted container %s", self._service_name)
            return

    def _is_config_update_required(self, content: str) -> bool:
        return not self._webui_config_file_exists() or not self._webui_config_file_content_matches(
            content=content)

    def _webui_config_file_content_matches(self, content: str) -> bool:
        if not self._webui_config_file_exists():
            return False
        existing_content = self._container.pull(path=WEBUI_CONFIG_PATH)
        return existing_content.read() == content

    def _webui_config_file_exists(self) -> bool:
        return bool(self._container.exists(WEBUI_CONFIG_PATH))

    def _generate_webui_config_file(self) -> str:
        return render_config_file(
            common_database_name=COMMON_DATABASE_NAME,
            common_database_url=self._get_common_database_url(),
            auth_database_name=AUTH_DATABASE_NAME,
            auth_database_url=self._get_auth_database_url(),
        )

    def _is_nms_service_running(self) -> bool:
        if not self._container.can_connect():
            return False
        try:
            service = self._container.get_service(self._service_name)
        except ModelError:
            return False
        return service.is_running()

    def _get_resources_from_inventory(self, inventory_url: str) -> list:
        try:
            response = requests.get(inventory_url)
            response.raise_for_status()
            resources = response.json()
            logger.info(f"Got {resources} from inventory")
            return resources
        except Exception as e:
            logger.error(f"Failed to get resource from inventory: {e}")
            return []

    def _get_upfs_from_inventory(self) -> list:
        inventory_url = f"{self._webui_endpoint}/{UPF_CONFIG_URL}"
        return self._get_resources_from_inventory(inventory_url)

    def _get_gnbs_from_inventory(self) -> list:
        inventory_url = f"{self._webui_endpoint}/{GNB_CONFIG_URL}"
        return self._get_resources_from_inventory(inventory_url)

    def _add_resource_to_inventory(self, url: str, resource_name: str, data: dict) -> None:
        try:
            response = requests.post(url, headers=JSON_HEADER, json=data)
            response.raise_for_status()
            logger.info(f"{resource_name} added to webui")
        except Exception as e:
            logger.error(f"Failed to add {resource_name} to webui: {e}")

    def _add_upf_to_inventory(self, upf: dict) -> None:
        upf_hostmane = upf["hostname"]
        inventory_url = f"{self._webui_endpoint}/{UPF_CONFIG_URL}/{upf_hostmane}"
        data = {"port": upf["port"]}
        self._add_resource_to_inventory(inventory_url, upf_hostmane, data)

    def _add_gnb_to_inventory(self, gnb: dict) -> None:
        gnb_name = gnb["name"]
        inventory_url = f"{self._webui_endpoint}/{GNB_CONFIG_URL}/{gnb_name}"
        data = {"tac": gnb["tac"]}
        self._add_resource_to_inventory(inventory_url, gnb_name, data)

    def _delete_resource_from_inventory(self, inventory_url: str, resource_name: str) -> None:
        try:
            response = requests.delete(inventory_url)
            response.raise_for_status()
            logger.info(f"{resource_name} removed from webui")
        except Exception as e:
            logger.error(f"Failed to remove {resource_name} from webui: {e}")

    def _delete_upf_from_inventory(self, upf_hostname: str) -> None:
        inventory_url = f"{self._webui_endpoint}/{UPF_CONFIG_URL}/{upf_hostname}"
        self._delete_resource_from_inventory(inventory_url, upf_hostname)

    def _delete_gnb_from_inventory(self, gnb_name: str) -> None:
        inventory_url = f"{self._webui_endpoint}/{GNB_CONFIG_URL}/{gnb_name}"
        self._delete_resource_from_inventory(inventory_url, gnb_name)

    def _configure_upfs(self) -> None:
        if not self.model.relations.get(FIVEG_N4_RELATION_NAME):
            logger.info("Relation %s not available", FIVEG_N4_RELATION_NAME)
        inventory_upf_config = self._get_upfs_from_inventory()
        relation_upf_config = self._get_upf_config_from_relations()
        self._sync_upfs(inventory_upfs=inventory_upf_config, relation_upfs=relation_upf_config)

    def _configure_gnbs(self) -> None:
        if not self.model.relations.get(GNB_IDENTITY_RELATION_NAME):
            logger.info("Relation %s not available", GNB_IDENTITY_RELATION_NAME)
        inventory_gnb_config = self._get_gnbs_from_inventory()
        relation_gnb_config = self._get_gnb_config_from_relations()
        self._sync_gnbs(inventory_gnbs=inventory_gnb_config, relation_gnbs=relation_gnb_config)

    def _get_upf_config_from_relations(self) -> list[dict[str, str]]:
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
                upf_host_port_list.append({"hostname": hostname, "port": str(port)})
        return upf_host_port_list

    def _get_gnb_config_from_relations(self) -> list[dict[str, str]]:
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
                gnb_name_tac_list.append({"name": gnb_name, "tac": gnb_tac})
        return gnb_name_tac_list

    def _sync_gnbs(self, inventory_gnbs: list, relation_gnbs: list) -> None:
        """Align the gNB from the `fiveg_gnb_identity` relations with the remote DB inventory."""
        db_gnb_dict = {gnb['name']: gnb for gnb in inventory_gnbs}
        relation_gnb_dict = {gnb['name']: gnb for gnb in relation_gnbs}

        for name, relation_gnb in relation_gnb_dict.items():
            if name not in db_gnb_dict or db_gnb_dict[name] != relation_gnb:
                self._add_gnb_to_inventory(relation_gnb)

        for name in db_gnb_dict:
            if name not in relation_gnb_dict:
                self._delete_gnb_from_inventory(name)

    def _sync_upfs(self, inventory_upfs: list, relation_upfs: list) -> None:
        """Align the gNB from the `fiveg_n4` relations with the remote DB inventory."""
        db_upf_dict = {upf['hostname']: upf for upf in inventory_upfs}
        relation_upf_dict = {upf['hostname']: upf for upf in relation_upfs}

        for hostname, relation_upf in relation_upf_dict.items():
            if hostname not in db_upf_dict or db_upf_dict[hostname] != relation_upf:
                self._add_upf_to_inventory(relation_upf)

        for hostname in db_upf_dict:
            if hostname not in relation_upf_dict:
                self._delete_upf_from_inventory(hostname)

    def _get_common_database_url(self) -> str:
        if not self._common_database_resource_is_available():
            raise RuntimeError(f"Database `{COMMON_DATABASE_NAME}` is not available")
        return self._common_database.fetch_relation_data()[self._common_database.relations[0].id][
            "uris"
        ].split(",")[0]

    def _get_auth_database_url(self) -> str:
        if not self._auth_database_resource_is_available():
            raise RuntimeError(f"Database `{AUTH_DATABASE_NAME}` is not available")
        return self._auth_database.fetch_relation_data()[self._auth_database.relations[0].id][
            "uris"
        ].split(",")[0]

    def _common_database_resource_is_available(self) -> bool:
        return bool(self._common_database.is_resource_created())

    def _auth_database_resource_is_available(self) -> bool:
        return bool(self._auth_database.is_resource_created())

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

    def _write_file_in_workload(self, path: str, content: str) -> None:
        self._container.push(path=path, source=content)
        logger.info("Pushed %s config file", path)

    def _relation_created(self, relation_name: str) -> bool:
        return bool(self.model.relations[relation_name])

    @property
    def _webui_config_url(self) -> str:
        return f"{WEBUI_SERVICE_NAME}:{GRPC_PORT}"

    @property
    def _webui_endpoint(self) -> str:
        return f"{_get_pod_ip()}:{WEBUI_URL_PORT}"

    @property
    def _pebble_layer(self) -> Layer:
        return Layer(
            {
                "summary": "NMS layer",
                "description": "pebble config layer for the NMS",
                "services": {
                    "nms": {
                        "override": "replace",
                        "startup": "enabled",
                        "command": f"/bin/webconsole --webuicfg {WEBUI_CONFIG_PATH}",  # noqa: E501
                        "environment": self._environment_variables,
                    },
                },
            }
        )

    @property
    def _environment_variables(self) -> dict:
        return {
            "GRPC_GO_LOG_VERBOSITY_LEVEL": "99",
            "GRPC_GO_LOG_SEVERITY_LEVEL": "info",
            "GRPC_TRACE": "all",
            "GRPC_VERBOSITY": "debug",
            "CONFIGPOD_DEPLOYMENT": "5G",
            "WEBUI_ENDPOINT": self._webui_endpoint,
        }


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreNMSOperatorCharm)
