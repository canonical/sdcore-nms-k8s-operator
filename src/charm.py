#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the Aether SD-Core Graphical User Interface for K8s."""

import logging
import socket
from ipaddress import IPv4Address
from subprocess import CalledProcessError, check_output
from typing import List, Optional

from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.loki_k8s.v1.loki_push_api import LogForwarder
from charms.sdcore_gnbsim_k8s.v0.fiveg_gnb_identity import (
    GnbIdentityRequires,
)
from charms.sdcore_nms_k8s.v0.sdcore_config import (
    SdcoreConfigProvides,
)
from charms.sdcore_upf_k8s.v0.fiveg_n4 import N4Requires
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from jinja2 import Environment, FileSystemLoader
from ops import (
    ActiveStatus,
    BlockedStatus,
    CollectStatusEvent,
    ModelError,
    WaitingStatus,
    main,
)
from ops.charm import CharmBase
from ops.framework import EventBase
from ops.pebble import Layer

from nms import NMS, GnodeB, Upf
from tls import CERTIFICATE_PATH, PRIVATE_KEY_PATH, Tls

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/nms/config"
CONFIG_FILE_NAME = "nmscfg.conf"
NMS_CONFIG_PATH = f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"
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
NMS_URL_PORT = 5000
TLS_RELATION_NAME = "certificates"
MANDATORY_RELATIONS = [COMMON_DATABASE_RELATION_NAME, AUTH_DATABASE_RELATION_NAME, TLS_RELATION_NAME]  # noqa: E501
CA_PATH = "/var/lib/juju/storage/certs/0/ca.pem"

def _get_pod_ip() -> Optional[str]:
    """Return the pod IP using juju client."""
    try:
        ip_address = check_output(["unit-get", "private-address"])
        return str(IPv4Address(ip_address.decode().strip())) if ip_address else None
    except (CalledProcessError, ValueError):
        return None


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
        self._tls = Tls(self, self._container)
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
        self.unit.set_ports(GRPC_PORT, NMS_URL_PORT)
        self.ingress = IngressPerAppRequirer(
            charm=self,
            port=NMS_URL_PORT,
            relation_name="ingress",
            strip_prefix=True,
            scheme=lambda: "https",
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
            self._common_database.on.database_created, self._configure_sdcore_nms
        )
        self.framework.observe(self._auth_database.on.database_created, self._configure_sdcore_nms)
        self.framework.observe(
            self._common_database.on.endpoints_changed, self._configure_sdcore_nms
        )
        self.framework.observe(
            self._auth_database.on.endpoints_changed, self._configure_sdcore_nms
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
        self.framework.observe(self.on.certificates_relation_joined, self._configure_sdcore_nms)
        self.framework.observe(
            self.on.certificates_relation_broken, self._on_certificates_relation_broken
        )
        self.framework.observe(
            self._tls._certificates.on.certificate_available, self._configure_sdcore_nms
        )
        # Handling config changed event to publish the new url if the unit reboots and gets new IP
        self.framework.observe(self.on.config_changed, self._configure_sdcore_nms)
        self._nms = NMS(url=f"https://{socket.getfqdn()}:{NMS_URL_PORT}", ca_path=CA_PATH)

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
        for relation in MANDATORY_RELATIONS:
            if not self._relation_created(relation):
                return
        if not self._common_database_resource_is_available():
            return
        if not self._auth_database_resource_is_available():
            return
        if not self._tls.certificate_is_available():
            logger.info("The TLS certificate is not available yet.")
            return
        self._configure_workload()
        self._publish_sdcore_config_url()
        self._sync_gnbs()
        self._sync_upfs()

    def _on_collect_unit_status(self, event: CollectStatusEvent):  # noqa: C901
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
        for relation in MANDATORY_RELATIONS:
            if not self._relation_created(relation):
                event.add_status(BlockedStatus(f"Waiting for {relation} relation to be created"))
                logger.info("Waiting for %s relation to be created", relation)
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
        if not self._nms_config_file_exists():
            event.add_status(WaitingStatus("Waiting for nms config file to be stored"))
            logger.info("Waiting for nms config file to be stored")
            return
        if not self._tls.certificate_is_available():
            event.add_status(WaitingStatus("Waiting for certificates to be available"))
            logger.info("Waiting for certificates to be available")
        if not self._is_nms_service_running():
            event.add_status(WaitingStatus("Waiting for NMS service to start"))
            logger.info("Waiting for NMS service to start")
            return

        event.add_status(ActiveStatus())

    def _on_certificates_relation_broken(self, event: EventBase) -> None:
        """Delete TLS related artifacts and reconfigures workload."""
        if not self._container.can_connect():
            event.defer()
            return
        self._tls._delete_private_key()
        self._tls._delete_certificate()

    def _publish_sdcore_config_url(self) -> None:
        if not self._relation_created(SDCORE_CONFIG_RELATION_NAME):
            return
        if not self._is_nms_service_running():
            return
        self._sdcore_config.set_webui_url_in_all_relations(webui_url=self._nms_config_url)

    def _configure_workload(self):
        certificate_update_required = self._tls.check_and_update_certificate()
        desired_config_file = self._generate_nms_config_file()
        if (not self._is_config_file_update_required(desired_config_file)
            and not certificate_update_required):
            self._configure_pebble()
            return
        self._write_file_in_workload(NMS_CONFIG_PATH, desired_config_file)
        self._configure_pebble()
        self._container.restart(self._container_name)
        logger.info("Restarted container %s", self._container_name)

    def _configure_pebble(self) -> None:
        """Apply changes to Pebble layer if a change is detected."""
        plan = self._container.get_plan()
        if plan.services != self._pebble_layer.services:
            self._container.add_layer(self._container_name, self._pebble_layer, combine=True)
            self._container.replan()
            logger.info("New layer added: %s", self._pebble_layer)

    def _is_config_file_update_required(self, content: str) -> bool:
        if not self._nms_config_file_exists():
            return True
        existing_content = self._container.pull(path=NMS_CONFIG_PATH)
        return existing_content.read() != content

    def _nms_config_file_exists(self) -> bool:
        return bool(self._container.exists(NMS_CONFIG_PATH))

    def _generate_nms_config_file(self) -> str:
        """Render nms configuration file based on Jinja template."""
        jinja2_environment = Environment(loader=FileSystemLoader("src/templates/"))
        template = jinja2_environment.get_template("nmscfg.conf.j2")
        return template.render(
            common_database_name=COMMON_DATABASE_NAME,
            common_database_url=self._get_common_database_url(),
            auth_database_name=AUTH_DATABASE_NAME,
            auth_database_url=self._get_auth_database_url(),
            tls_key_path=PRIVATE_KEY_PATH,
            tls_certificate_path=CERTIFICATE_PATH,
        )

    def _is_nms_service_running(self) -> bool:
        if not self._container.can_connect():
            return False
        try:
            service = self._container.get_service(self._service_name)
        except ModelError:
            return False
        return service.is_running()

    def _get_upf_config_from_relations(self) -> List[Upf]:
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
                upf_host_port_list.append(Upf(hostname=hostname, port=int(port)))
        return upf_host_port_list

    def _get_gnb_config_from_relations(self) -> List[GnodeB]:
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
                gnb_name_tac_list.append(GnodeB(name=gnb_name, tac=int(gnb_tac)))
        return gnb_name_tac_list

    def _sync_gnbs(self) -> None:
        """Align the gNBs from the `fiveg_gnb_identity`relations with the ones in nms."""
        if not self.model.relations.get(GNB_IDENTITY_RELATION_NAME):
            logger.info("Relation %s not available", GNB_IDENTITY_RELATION_NAME)
        nms_gnbs = self._nms.list_gnbs()
        relation_gnbs = self._get_gnb_config_from_relations()
        for gnb in nms_gnbs:
            if gnb not in relation_gnbs:
                self._nms.delete_gnb(name=gnb.name)
        for gnb in relation_gnbs:
            if gnb not in nms_gnbs:
                self._nms.create_gnb(name=gnb.name, tac=gnb.tac)

    def _sync_upfs(self) -> None:
        """Align the UPFs from the `fiveg_n4` relations with the ones in nms."""
        if not self.model.relations.get(FIVEG_N4_RELATION_NAME):
            logger.info("Relation %s not available", FIVEG_N4_RELATION_NAME)
        nms_upfs = self._nms.list_upfs()
        relation_upfs = self._get_upf_config_from_relations()
        for upf in nms_upfs:
            if upf not in relation_upfs:
                self._nms.delete_upf(hostname=upf.hostname)
        for upf in relation_upfs:
            if upf not in nms_upfs:
                self._nms.create_upf(hostname=upf.hostname, port=upf.port)

    def _get_common_database_url(self) -> str:
        if not self._common_database_resource_is_available():
            raise RuntimeError("Database `%s` is not available", COMMON_DATABASE_NAME)
        return self._common_database.fetch_relation_data()[self._common_database.relations[0].id][
            "uris"
        ].split(",")[0]

    def _get_auth_database_url(self) -> str:
        if not self._auth_database_resource_is_available():
            raise RuntimeError("Database `%s` is not available", AUTH_DATABASE_NAME)
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
    def _nms_config_url(self) -> str:
        return f"{self.app.name}:{GRPC_PORT}"

    @property
    def _nms_endpoint(self) -> str:
        return f"{_get_pod_ip()}:{NMS_URL_PORT}"

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
                        "command": f"/bin/webconsole --cfg {NMS_CONFIG_PATH}",  # noqa: E501
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
            "WEBUI_ENDPOINT": self._nms_endpoint,
        }


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreNMSOperatorCharm)
