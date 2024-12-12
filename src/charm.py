#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the Aether SD-Core Graphical User Interface for K8s."""

import logging
import secrets
import socket
import string
from dataclasses import dataclass
from ipaddress import IPv4Address
from subprocess import CalledProcessError, check_output
from typing import List, Optional, cast

from charms.data_platform_libs.v0.data_interfaces import DatabaseRequires
from charms.loki_k8s.v1.loki_push_api import LogForwarder
from charms.sdcore_nms_k8s.v0.fiveg_core_gnb import FivegCoreGnbProvides, PLMNConfig
from charms.sdcore_nms_k8s.v0.sdcore_config import SdcoreConfigProvides
from charms.sdcore_upf_k8s.v0.fiveg_n4 import N4Requires
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from jinja2 import Environment, FileSystemLoader
from ops import (
    ActiveStatus,
    BlockedStatus,
    CollectStatusEvent,
    ModelError,
    SecretNotFoundError,
    WaitingStatus,
    main,
)
from ops.charm import CharmBase
from ops.framework import EventBase
from ops.pebble import Layer

from nms import NMS, GnodeB, Upf
from tls import CA_CERTIFICATE_NAME, Tls

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/nms/config"
CONFIG_FILE_NAME = "nmscfg.conf"
NMS_CONFIG_PATH = f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"
CERTS_MOUNT_PATH = "/support/TLS"
WORKLOAD_VERSION_FILE_NAME = "/etc/workload-version"
AUTH_DATABASE_RELATION_NAME = "auth_database"
COMMON_DATABASE_RELATION_NAME = "common_database"
WEBUI_DATABASE_RELATION_NAME = "webui_database"
FIVEG_N4_RELATION_NAME = "fiveg_n4"
FIVEG_CORE_GNB_RELATION_NAME = "fiveg_core_gnb"
LOGGING_RELATION_NAME = "logging"
SDCORE_CONFIG_RELATION_NAME = "sdcore_config"
AUTH_DATABASE_NAME = "authentication"
COMMON_DATABASE_NAME = "free5gc"
WEBUI_DATABASE_NAME = "webui"
GRPC_PORT = 9876
NMS_URL_PORT = 5000
NMS_LOGIN_SECRET_LABEL = "NMS_LOGIN"


@dataclass
class LoginSecret:
    """The format of the secret for the login details that are required to login to NMS."""

    username: str
    password: str
    token: str | None

    def to_dict(self) -> dict[str, str]:
        """Return a dict version of the secret."""
        return {
            "username": self.username,
            "password": self.password,
            "token": self.token if self.token else "",
        }


TLS_RELATION_NAME = "certificates"
MANDATORY_RELATIONS = [
    COMMON_DATABASE_RELATION_NAME,
    AUTH_DATABASE_RELATION_NAME,
    WEBUI_DATABASE_RELATION_NAME,
    TLS_RELATION_NAME,
]
CA_CERTIFICATE_CHARM_PATH = f"/var/lib/juju/storage/certs/0/{CA_CERTIFICATE_NAME}"


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
        self._tls = Tls(
            charm=self,
            relation_name=TLS_RELATION_NAME,
            container=self._container,
            domain_name=socket.getfqdn(),
            workload_storage_path=CERTS_MOUNT_PATH,
        )
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
        self._webui_database = DatabaseRequires(
            self,
            relation_name=WEBUI_DATABASE_RELATION_NAME,
            database_name=WEBUI_DATABASE_NAME,
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
        self._logging = LogForwarder(charm=self, relation_name=LOGGING_RELATION_NAME)
        self._fiveg_core_gnb_provider = FivegCoreGnbProvides(self, FIVEG_CORE_GNB_RELATION_NAME)
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
        self.framework.observe(self.on.fiveg_core_gnb_relation_changed, self._configure_sdcore_nms)
        self.framework.observe(self.on.fiveg_core_gnb_relation_broken, self._configure_sdcore_nms)
        self.framework.observe(self.fiveg_n4.on.fiveg_n4_available, self._configure_sdcore_nms)
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
        self.framework.observe(
            self.on["nms"].pebble_custom_notice, self._sync_network_config
        )

        self._nms = NMS(
            url=f"https://{socket.getfqdn()}:{NMS_URL_PORT}",
            ca_certificate_path=CA_CERTIFICATE_CHARM_PATH,
        )

    def _configure_sdcore_nms(self, event: EventBase) -> None:  # noqa: C901
        """Handle Juju events.

        Whenever a Juju event is emitted, this method performs a couple of checks to make sure that
        the workload is ready to be started. Then, it configures the NMS workload,
        runs the Pebble services and expose the service information through charm's interface.
        """
        if not self._container.can_connect():
            return
        if self._get_invalid_configs():
            return
        if not self._container.exists(path=BASE_CONFIG_PATH):
            return
        if not self._container.exists(path=CERTS_MOUNT_PATH):
            return
        for relation in MANDATORY_RELATIONS:
            if not self._relation_created(relation):
                return
        if not self._common_database_resource_is_available():
            return
        if not self._auth_database_resource_is_available():
            return
        if not self._webui_database_resource_is_available():
            return
        if not self._tls.certificate_is_available():
            logger.info("The TLS certificate is not available yet.")
            return
        self._configure_workload()
        self._configure_charm_authorization()
        self._publish_sdcore_config_url()
        self._sync_gnbs()
        self._sync_upfs()
        self._sync_network_config(event)

    def _sync_network_config(self, event: EventBase):
        """Synchronize network configuration between the Core and the RAN.

        Every time network configuration is updated (NetworkSlice configuration change in the NMS),
        the `webconsole` sends a custom Pebble notification. When it happens, this method fetches
        the current network setup and passes the configuration to the RAN part of the network
        through the relevant Juju integrations.
        """
        gnbs_config = self._get_gnbs_config()
        logger.error("========================================================================")
        logger.error(gnbs_config)
        logger.error("Relations: %s", list(self.model.relations))
        logger.error("========================================================================")
        for relation in self.model.relations.get(FIVEG_CORE_GNB_RELATION_NAME, []):
            logger.error("-----------------------------------------------------------")
            logger.error(relation)
            logger.error(relation.name)
            logger.error(relation.id)
            logger.error(relation.app)
            logger.error(relation.data)
            logger.error("-----------------------------------------------------------")
            if not relation.app:
                logger.warning(
                    "Application missing from the %s relation data",
                    FIVEG_CORE_GNB_RELATION_NAME,
                )
                continue
            relation_gnb_name = self._fiveg_core_gnb_provider.get_gnb_name(relation.id)
            logger.debug("Synchronizing config for %s", relation_gnb_name)
            if gnodeb := next((gnb for gnb in gnbs_config if gnb.name == relation_gnb_name), None):
                self._fiveg_core_gnb_provider.publish_gnb_config_information(
                    relation_id=relation.id,
                    tac=gnodeb.tac,
                    plmns=gnodeb.plmns,
                )

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
        if invalid_configs := self._get_invalid_configs():
            event.add_status(
                BlockedStatus(f"The following configurations are not valid: {invalid_configs}")
            )
            logger.info("The following configurations are not valid: %s", invalid_configs)
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
        if not self._webui_database_resource_is_available():
            event.add_status(WaitingStatus("Waiting for the webui database to be available"))
            logger.info("Waiting for the webui database to be available")
            return
        if not self._container.can_connect():
            event.add_status(WaitingStatus("Waiting for container to be ready"))
            logger.info("Waiting for container to be ready")
            return
        self.unit.set_workload_version(self._get_workload_version())

        if not self._container.exists(path=BASE_CONFIG_PATH) or not self._container.exists(
            path=CERTS_MOUNT_PATH
        ):
            event.add_status(WaitingStatus("Waiting for storage to be attached"))
            logger.info("Waiting for storage to be attached")
            return
        if not self._nms_config_file_exists():
            event.add_status(WaitingStatus("Waiting for NMS config file to be stored"))
            logger.info("Waiting for NMS config file to be stored")
            return
        if not self._tls.certificate_is_available():
            event.add_status(WaitingStatus("Waiting for certificates to be available"))
            logger.info("Waiting for certificates to be available")
        if not self._is_nms_service_running():
            event.add_status(WaitingStatus("Waiting for NMS service to start"))
            logger.info("Waiting for NMS service to start")
            return
        if not self._nms.is_api_available():
            event.add_status(WaitingStatus("NMS API not yet available"))
            return
        if not self._nms.is_initialized():
            event.add_status(WaitingStatus("NMS not yet initialized"))
            return
        event.add_status(ActiveStatus())

    def _create_admin_account_if_does_not_exist(self) -> None:
        """Create the first admin and store the credentials in a secret if it does not exist."""
        if not self._nms.is_api_available():
            return
        account = self._get_admin_account()
        if not account:
            username = _generate_username()
            password = _generate_password()
            account = LoginSecret(username, password, None)
            self.app.add_secret(
                label=NMS_LOGIN_SECRET_LABEL,
                content=account.to_dict(),
            )
            logger.info("admin account details saved to secrets.")
        if not self._nms.is_initialized():
            self._nms.create_first_user(account.username, account.password)

    def _get_admin_account(self) -> LoginSecret | None:
        """Get the NMS admin user credentials from secrets.

        Returns:
            Login details secret if they exist. None if the secret does not exist.
        """
        try:
            secret = self.model.get_secret(label=NMS_LOGIN_SECRET_LABEL)
            secret_content = secret.get_content(refresh=True)
            username = secret_content.get("username", "")
            password = secret_content.get("password", "")
            token = secret_content.get("token")
            return LoginSecret(username, password, token)
        except SecretNotFoundError:
            logger.info("NMS_LOGIN secret not found.")
            return None

    def _on_certificates_relation_broken(self, event: EventBase) -> None:
        """Delete TLS related artifacts."""
        if not self._container.can_connect():
            event.defer()
            return
        self._tls.clean_up_certificates()

    def _publish_sdcore_config_url(self) -> None:
        if not self._relation_created(SDCORE_CONFIG_RELATION_NAME):
            return
        if not self._is_nms_service_running():
            return
        self._sdcore_config.set_webui_url_in_all_relations(webui_url=self._nms_config_url)

    def _configure_workload(self):
        certificate_update_required = self._tls.check_and_update_certificate()
        desired_config_file = self._generate_nms_config_file()
        if (
            not self._is_config_file_update_required(desired_config_file)
            and not certificate_update_required
        ):
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

    def _configure_charm_authorization(self):
        """Create an admin user to manage NMS and log in."""
        self._create_admin_account_if_does_not_exist()
        login_details = self._get_admin_account()
        if not login_details:
            return
        if not login_details.token or not self._nms.token_is_valid(login_details.token):
            login_response = self._nms.login(login_details.username, login_details.password)
            if not login_response or not login_response.token:
                logger.warning(
                    "failed to login with the existing admin credentials."
                    " If you've manually modified the admin account credentials,"
                    " please update the charm's credentials secret accordingly."
                )
                return
            login_details.token = login_response.token
            login_details_secret = self.model.get_secret(label=NMS_LOGIN_SECRET_LABEL)
            login_details_secret.set_content(login_details.to_dict())

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
            webui_database_name=WEBUI_DATABASE_NAME,
            webui_database_url=self._get_webui_database_url(),
            tls_key_path=self._tls.private_key_workload_path,
            tls_certificate_path=self._tls.certificate_workload_path,
            log_level=self._get_log_level_config(),
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

    def _sync_gnbs(self) -> None:
        """Synchronize gNBs integrated through the `fiveg_core_gnb` relations with the NMS."""
        login_details = self._get_admin_account()
        if not login_details or not login_details.token:
            logger.warning("Failed to get admin account details")
            return
        nms_gnbs = self._nms.list_gnbs(token=login_details.token)
        integrated_gnbs = self._get_integrated_gnbs()
        for gnb in nms_gnbs:
            if gnb not in integrated_gnbs:
                self._nms.delete_gnb(name=gnb.name, token=login_details.token)
        for gnb in integrated_gnbs:
            if gnb not in nms_gnbs:
                self._nms.create_gnb(name=gnb.name, tac=gnb.tac, token=login_details.token)

    def _get_integrated_gnbs(self) -> List[GnodeB]:
        integrated_gnbs = []
        for relation in self.model.relations.get(FIVEG_CORE_GNB_RELATION_NAME, []):
            gnb_name = self._fiveg_core_gnb_provider.get_gnb_name(relation.id)
            if gnb_name:
                integrated_gnbs.append(GnodeB(name=gnb_name))
        return integrated_gnbs

    def _sync_upfs(self) -> None:
        """Align the UPFs from the `fiveg_n4` relations with the ones in nms."""
        login_details = self._get_admin_account()
        if not login_details or not login_details.token:
            logger.warning("Failed to get admin account details")
            return
        if not self.model.relations.get(FIVEG_N4_RELATION_NAME):
            logger.info("Relation %s not available", FIVEG_N4_RELATION_NAME)
        nms_upfs = self._nms.list_upfs(token=login_details.token)
        relation_upfs = self._get_upf_config_from_relations()
        for upf in nms_upfs:
            if upf not in relation_upfs:
                self._nms.delete_upf(hostname=upf.hostname, token=login_details.token)
        for upf in relation_upfs:
            if upf not in nms_upfs:
                self._nms.create_upf(
                    hostname=upf.hostname, port=upf.port, token=login_details.token
                )

    def _get_gnbs_config(self) -> List[GnodeB]:
        """Get configuration of all gNodeBs in the network.

        Returns:
            List: List of GnodeBs in the network
        """
        gnbs_config = []
        login_details = self._get_admin_account()
        if not login_details or not login_details.token:
            logger.warning("Failed to get admin account details")
            return []
        network_slices = self._nms.list_network_slices(token=login_details.token)
        for network_slice_name in network_slices:
            network_slice = self._nms.get_network_slice(
                slice_name=network_slice_name, token=login_details.token
            )
            if not network_slice:
                continue
            logger.debug("Fetched configuration for NetworkSlice: %s", network_slice_name)
            plmn_config = PLMNConfig(
                network_slice.mcc,
                network_slice.mnc,
                network_slice.sst,
                network_slice.sd
            )
            logger.debug(
                "PLMN configuration for %s NetworkSlice is: %s",
                network_slice_name,
                plmn_config.asdict(),
            )
            for gnodeb in network_slice.gnodebs:
                if existing_gnb := next(
                    (gnb for gnb in gnbs_config if gnb.name == gnodeb.name),
                    None,
                ):
                    existing_gnb.plmns.append(plmn_config)
                else:
                    gnodeb.plmns.append(plmn_config)
                    gnbs_config.append(gnodeb)
        return gnbs_config

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

    def _get_webui_database_url(self) -> str:
        if not self._common_database_resource_is_available():
            raise RuntimeError("Database `%s` is not available", WEBUI_DATABASE_NAME)
        return self._webui_database.fetch_relation_data()[self._webui_database.relations[0].id][
            "uris"
        ].split(",")[0]

    def _common_database_resource_is_available(self) -> bool:
        return bool(self._common_database.is_resource_created())

    def _auth_database_resource_is_available(self) -> bool:
        return bool(self._auth_database.is_resource_created())

    def _webui_database_resource_is_available(self) -> bool:
        return bool(self._webui_database.is_resource_created())

    def _get_workload_version(self) -> str:
        """Return the workload version.

        Checks for the presence of /etc/workload-version file
        and if present, returns the contents of that file. If
        the file is not present, an empty string is returned.

        Returns:
            string: A human-readable string representing the
            version of the workload
        """
        if self._container.exists(path=f"{WORKLOAD_VERSION_FILE_NAME}"):
            version_file_content = self._container.pull(
                path=f"{WORKLOAD_VERSION_FILE_NAME}"
            ).read()
            return version_file_content
        return ""

    def _get_invalid_configs(self) -> list[str]:
        """Return list of invalid configurations.

        Returns:
            list: List of strings matching config keys.
        """
        invalid_configs = []
        if not self._is_log_level_valid():
            invalid_configs.append("log-level")
        return invalid_configs

    def _get_log_level_config(self) -> Optional[str]:
        return cast(Optional[str], self.model.config.get("log-level"))

    def _is_log_level_valid(self) -> bool:
        log_level = self._get_log_level_config()
        return log_level in ["debug", "info", "warn", "error", "fatal", "panic"]

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
            "CONFIGPOD_DEPLOYMENT": "5G",
            "WEBUI_ENDPOINT": self._nms_endpoint,
        }


def _generate_password() -> str:
    """Generate a password for the NMS Account using the secrets library."""
    pw = []
    pw.append(secrets.choice(string.ascii_lowercase))
    pw.append(secrets.choice(string.ascii_uppercase))
    pw.append(secrets.choice(string.digits))
    pw.append(secrets.choice(string.punctuation))
    for i in range(8):
        pw.append(secrets.choice(string.ascii_letters + string.digits + string.punctuation))
    secrets.SystemRandom().shuffle(pw)
    return "".join(pw)


def _generate_username() -> str:
    """Generate a username for the NMS Account."""
    suffix = [secrets.choice(string.ascii_uppercase) for _ in range(4)]
    return "charm-admin-" + "".join(suffix)


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreNMSOperatorCharm)
