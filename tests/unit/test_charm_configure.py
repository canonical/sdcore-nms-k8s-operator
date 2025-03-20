# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
import json
import os
import tempfile
from unittest.mock import call, patch

import pytest
import scenario
from charms.sdcore_nms_k8s.v0.fiveg_core_gnb import PLMNConfig
from ops.pebble import Layer

from nms import GnodeB, LoginResponse, NetworkSlice, Upf
from tests.unit.fixtures import NMSUnitTestFixtures

EXPECTED_CONFIG_FILE_PATH = "tests/unit/expected_nms_cfg.yaml"


class TestCharmConfigure(NMSUnitTestFixtures):
    def test_given_db_relations_do_not_exist_when_pebble_ready_then_nms_config_file_is_not_written(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert not os.path.exists(f"{tempdir}/nmscfg.conf")

    def test_given_common_db_resource_not_available_when_pebble_ready_then_nms_config_file_is_not_written(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "11.11.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    certificates_relation,
                },
            )
            self.mock_check_and_update_certificate.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert not os.path.exists(f"{tempdir}/nmscfg.conf")

    def test_given_auth_db_resource_not_available_when_pebble_ready_then_nms_config_file_is_not_written(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.2.3.4:5678",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    certificates_relation,
                },
            )
            self.mock_check_and_update_certificate.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert not os.path.exists(f"{tempdir}/nmscfg.conf")

    def test_given_certificates_relation_doesnt_exist_when_pebble_ready_then_nms_config_file_is_not_written(  # noqa: E501
        self,
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.9.11.4:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.8.11.4:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                },
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert not os.path.exists(f"{tempdir}/nmscfg.conf")

    def test_given_tls_certificate_not_available_when_pebble_ready_then_nms_config_file_is_not_written(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.2.3.4:5678",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "11.11.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    certificates_relation,
                },
            )
            self.mock_certificate_is_available.return_value = False

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert not os.path.exists(f"{tempdir}/nmscfg.conf")

    @pytest.mark.parametrize(
        "certificate_was_updated",
        [
            True,
            False,
        ],
    )
    def test_given_storage_attached_and_nms_config_file_does_not_exist_when_pebble_ready_then_config_file_is_written(  # noqa: E501
        self, certificate_was_updated
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.9.11.4:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.8.11.4:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                },
            )
            self.mock_check_and_update_certificate.return_value = certificate_was_updated

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert os.path.exists(f"{tempdir}/nmscfg.conf")
            with open(f"{tempdir}/nmscfg.conf", "r") as f:
                assert f.read() == open(EXPECTED_CONFIG_FILE_PATH, "r").read()

    def test_given_container_is_ready_db_relations_exist_and_storage_attached_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self,
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert state_out.get_container("nms").layers["nms"] == Layer(
                {
                    "summary": "NMS layer",
                    "description": "pebble config layer for the NMS",
                    "services": {
                        "nms": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/bin/webconsole --cfg /nms/config/nmscfg.conf",
                            "environment": {
                                "CONFIGPOD_DEPLOYMENT": "5G",
                                "WEBUI_ENDPOINT": "None:5000",
                            },
                        }
                    },
                }
            )

    @patch("charms.traefik_k8s.v2.ingress.IngressPerAppRequirer.url", "https://potato/")
    def test_given_container_is_ready_db_relations_exist_and_storage_attached_and_ingress_url_known_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self,
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert state_out.get_container("nms").layers["nms"] == Layer(
                {
                    "summary": "NMS layer",
                    "description": "pebble config layer for the NMS",
                    "services": {
                        "nms": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/bin/webconsole --cfg /nms/config/nmscfg.conf",
                            "environment": {
                                "CONFIGPOD_DEPLOYMENT": "5G",
                                "WEBUI_ENDPOINT": "potato",
                            },
                        }
                    },
                }
            )

    @pytest.mark.parametrize("url", ["/banana", "https://$&*$&[%/"])
    def test_given_container_is_ready_db_relations_exist_and_storage_attached_and_ingress_url_no_netloc_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self,
        url
    ):
        with patch("charms.traefik_k8s.v2.ingress.IngressPerAppRequirer.url", url):
            self.mock_nms_login.return_value = None
            with tempfile.TemporaryDirectory() as tempdir:
                common_database_relation = scenario.Relation(
                    endpoint="common_database",
                    interface="mongodb_client",
                    remote_app_data={
                        "username": "banana",
                        "password": "pizza",
                        "uris": "1.1.1.1:1234",
                    },
                )
                auth_database_relation = scenario.Relation(
                    endpoint="auth_database",
                    interface="mongodb_client",
                    remote_app_data={
                        "username": "banana",
                        "password": "pizza",
                        "uris": "2.2.2.2:1234",
                    },
                )
                webui_database_relation = scenario.Relation(
                    endpoint="webui_database",
                    interface="mongodb_client",
                    remote_app_data={
                        "username": "carrot",
                        "password": "hotdog",
                        "uris": "1.1.1.1:1234",
                    },
                )
                certificates_relation = scenario.Relation(
                    endpoint="certificates", interface="tls-certificates"
                )
                config_mount = scenario.Mount(
                    location="/nms/config",
                    source=tempdir,
                )
                certs_mount = scenario.Mount(
                    location="/support/TLS",
                    source=tempdir,
                )
                container = scenario.Container(
                    name="nms",
                    can_connect=True,
                    mounts={
                        "config": config_mount,
                        "certs": certs_mount,
                    },
                )
                state_in = scenario.State(
                    leader=True,
                    containers={container},
                    relations={
                        common_database_relation,
                        auth_database_relation,
                        webui_database_relation,
                        certificates_relation,
                    },
                )
                self.mock_certificate_is_available.return_value = True

                state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

                assert state_out.get_container("nms").layers["nms"] == Layer(
                    {
                        "summary": "NMS layer",
                        "description": "pebble config layer for the NMS",
                        "services": {
                            "nms": {
                                "startup": "enabled",
                                "override": "replace",
                                "command": "/bin/webconsole --cfg /nms/config/nmscfg.conf",
                                "environment": {
                                    "CONFIGPOD_DEPLOYMENT": "5G",
                                    "WEBUI_ENDPOINT": "None:5000",
                                },
                            }
                        },
                    }
                )

    def test_given_mandatory_relations_do_not_exist_when_pebble_ready_then_pebble_plan_is_empty(
        self,
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert state_out.get_container("nms").layers == {}

    def test_given_storage_not_attached_when_pebble_ready_then_config_url_is_not_published_for_relations(  # noqa: E501
        self,
    ):
        self.mock_nms_login.return_value = None
        sdcore_config_relation = scenario.Relation(
            endpoint="sdcore_config",
            interface="sdcore_config",
        )
        common_database_relation = scenario.Relation(
            endpoint="common_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "banana",
                "password": "pizza",
                "uris": "1.2.3.4:1234",
            },
        )
        auth_database_relation = scenario.Relation(
            endpoint="auth_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "banana",
                "password": "pizza",
                "uris": "2.1.1.1:1234",
            },
        )
        certificates_relation = scenario.Relation(
            endpoint="certificates", interface="tls-certificates"
        )
        container = scenario.Container(
            name="nms",
            can_connect=True,
        )
        state_in = scenario.State(
            leader=True,
            containers={container},
            relations={
                sdcore_config_relation,
                common_database_relation,
                auth_database_relation,
                certificates_relation,
            },
        )
        self.mock_certificate_is_available.return_value = True

        self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

        self.mock_set_webui_url_in_all_relations.assert_not_called()

    def test_given_nms_service_is_running_mandatory_relations_are_not_joined_when_pebble_ready_then_config_url_is_not_published_for_relations(  # noqa: E501
        self,
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            sdcore_config_relation = scenario.Relation(
                endpoint="sdcore_config",
                interface="sdcore_config",
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={sdcore_config_relation},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_set_webui_url_in_all_relations.assert_not_called()

    def test_given_nms_service_is_running_db_relations_are_joined_when_several_sdcore_config_relations_are_joined_then_config_url_is_set_in_all_relations(  # noqa: E501
        self,
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            sdcore_config_relation_1 = scenario.Relation(
                endpoint="sdcore_config",
                interface="sdcore_config",
            )
            sdcore_config_relation_2 = scenario.Relation(
                endpoint="sdcore_config",
                interface="sdcore_config",
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    auth_database_relation,
                    common_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    sdcore_config_relation_1,
                    sdcore_config_relation_2,
                },
            )
            self.mock_certificate_is_available.return_value = True
            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_set_webui_url_in_all_relations.assert_called_with(
                webui_url="sdcore-nms-k8s:9876"
            )

    def test_given_nms_service_is_not_running_when_pebble_ready_then_config_url_is_not_set_in_the_relations(  # noqa: E501
        self,
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            sdcore_config_relation = scenario.Relation(
                endpoint="sdcore_config",
                interface="sdcore_config",
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=False,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    auth_database_relation,
                    common_database_relation,
                    certificates_relation,
                    sdcore_config_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_set_webui_url_in_all_relations.assert_not_called()

    @pytest.mark.parametrize("relation_name", [("fiveg_n4"), ("fiveg_core_gnb")])
    def test_given_storage_not_attached_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
        self.mock_nms_login.return_value = None
        relation = scenario.Relation(
            endpoint=relation_name,
            interface=relation_name,
        )
        container = scenario.Container(
            name="nms",
            can_connect=True,
        )

        state_in = scenario.State(
            leader=True,
            relations={relation},
            containers={container},
        )

        self.ctx.run(self.ctx.on.relation_broken(relation), state_in)

    @pytest.mark.parametrize("relation_name", [("fiveg_n4"), ("fiveg_core_gnb")])
    def test_given_cannot_connect_to_container_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            relation = scenario.Relation(
                endpoint=relation_name,
                interface=relation_name,
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=False,
                mounts={
                    "config": config_mount,
                },
            )

            state_in = scenario.State(
                leader=True,
                relations={relation},
                containers={container},
            )

            self.ctx.run(self.ctx.on.relation_broken(relation), state_in)

    def test_given_login_secret_doesnt_exist_when_configure_then_login_secret_created(self):
        self.mock_is_api_available.return_value = True
        self.mock_is_initialized.return_value = False
        self.mock_nms_login.return_value = LoginResponse(token="test-token")
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    fiveg_core_gnb_relation,
                    fiveg_n4_relation,
                    auth_database_relation,
                    common_database_relation,
                    webui_database_relation,
                    certificates_relation,
                },
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

        secret = state_out.get_secret(label="NMS_LOGIN")
        assert secret.tracked_content["token"] == "test-token"

    @pytest.mark.parametrize(
        "relation_name,relation_data",
        [
            pytest.param(
                "fiveg_core_gnb",
                {},
                id="missing_gnb_name_in_gNB_config",
            ),
            pytest.param(
                "fiveg_core_gnb",
                {"gnb-name": ""},
                id="gnb_name_is_empty_strings_in_gNB_config",
            ),
            pytest.param(
                "fiveg_n4",
                {"upf_hostname": "some.host.name"},
                id="missing_upf_port_in_UPF_config",
            ),
            pytest.param(
                "fiveg_n4",
                {"upf_port": "1234"},
                id="missing_upf_hostname_in_UPF_config",
            ),
            pytest.param(
                "fiveg_n4",
                {"upf_hostname": "", "upf_port": ""},
                id="upf_hostname_and_upf_port_are_empty_strings_in_UPF_config",
            ),
            pytest.param(
                "fiveg_n4",
                {"some": "key"},
                id="invalid_key_in_UPF_config",
            ),
        ],
    )
    def test_given_incomplete_data_in_relation_when_pebble_ready_then_is_not_updated_in_nms_db(
        self,
        relation_name,
        relation_data,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            relation = scenario.Relation(
                endpoint=relation_name,
                interface=relation_name,
                remote_app_data=relation_data,
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                secrets={login_secret},
                relations={
                    relation,
                    auth_database_relation,
                    common_database_relation,
                    webui_database_relation,
                    certificates_relation,
                },
                containers={container},
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_create_gnb.assert_not_called()
            self.mock_create_upf.assert_not_called()
            self.mock_update_upf.assert_not_called()
            self.mock_delete_gnb.assert_not_called()
            self.mock_delete_upf.assert_not_called()

    def test_given_no_mandatory_relations_when_pebble_ready_then_nms_inventory_is_not_updated(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={fiveg_core_gnb_relation, fiveg_n4_relation},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_create_gnb.assert_not_called()
            self.mock_delete_gnb.assert_not_called()
            self.mock_create_upf.assert_not_called()
            self.mock_delete_upf.assert_not_called()

    def test_given_mandatory_relations_when_pebble_ready_then_nms_upf_is_updated(
        self,
    ):
        self.mock_nms_login.return_value = None
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation,
                    fiveg_n4_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_create_upf.assert_called_once_with(
                hostname="some.host.name", port=1234, token="test-token"
            )
            self.mock_update_upf.assert_not_called()
            self.mock_delete_upf.assert_not_called()

    def test_given_mandatory_relations_when_pebble_ready_then_nms_gnb_is_updated(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation,
                    fiveg_n4_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_create_gnb.assert_called_once_with(
                name="some.gnb.name", tac=None, token="test-token"
            )
            self.mock_delete_gnb.assert_not_called()

    def test_given_multiple_n4_relations_when_pebble_ready_then_both_upfs_are_added_to_nms(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            fiveg_n4_relation_1 = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            fiveg_n4_relation_2 = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "my_host",
                    "upf_port": "77",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_n4_relation_1,
                    fiveg_n4_relation_2,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            calls = [
                call(hostname="my_host", port=77, token="test-token"),
                call(hostname="some.host.name", port=1234, token="test-token"),
            ]
            self.mock_create_upf.assert_has_calls(calls, any_order=True)
            self.mock_update_upf.assert_not_called()
            self.mock_delete_upf.assert_not_called()

    def test_given_multiple_gnb_relations_when_pebble_ready_then_both_gnbs_are_added_to_nms(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            fiveg_core_gnb_relation_1 = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            fiveg_core_gnb_relation_2 = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "my_gnb",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation_1,
                    fiveg_core_gnb_relation_2,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            calls = [
                call(name="some.gnb.name", tac=None, token="test-token"),
                call(name="my_gnb", tac=None, token="test-token"),
            ]
            self.mock_create_gnb.assert_has_calls(calls, any_order=True)
            self.mock_delete_gnb.assert_not_called()

    def test_given_upf_exist_in_nms_and_relation_matches_when_pebble_ready_then_nms_upfs_are_not_updated(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            self.mock_list_upfs.return_value = [Upf(hostname="some.host.name", port=1234)]
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    fiveg_n4_relation,
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_list_upfs.assert_called()
            self.mock_create_upf.assert_not_called()
            self.mock_update_upf.assert_not_called()
            self.mock_delete_upf.assert_not_called()

    def test_given_gnb_exist_in_nms_and_relation_matches_when_pebble_ready_then_nms_gnbs_are_not_updated(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            existing_gnbs = [GnodeB(name="some.gnb.name")]
            self.mock_list_gnbs.return_value = existing_gnbs
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_list_gnbs.assert_called()
            self.mock_create_gnb.assert_not_called()
            self.mock_delete_gnb.assert_not_called()

    def test_given_no_upf_or_gnb_relation_or_db_when_pebble_ready_then_nms_resources_are_not_updated(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations=frozenset(),
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_create_gnb.assert_not_called()

    def test_given_upf_exists_in_nms_and_new_upf_relation_is_added_when_pebble_ready_then_second_upf_is_added_to_nms(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            existing_upf = Upf(hostname="some.host.name", port=1234)
            self.mock_list_upfs.return_value = [existing_upf]
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_n4_relation_1 = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            fiveg_n4_relation_2 = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "my_host",
                    "upf_port": "4567",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_n4_relation_1,
                    fiveg_n4_relation_2,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.relation_joined(fiveg_n4_relation_2), state_in)

            self.mock_create_upf.assert_called_once_with(
                hostname="my_host", port=4567, token="test-token"
            )
            self.mock_delete_upf.assert_not_called()
            self.mock_update_upf.assert_not_called()

    def test_given_gnb_exists_in_nms_and_new_fiveg_core_gnb_relation_is_added_when_pebble_ready_then_second_gnb_is_added_to_nms(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            existing_gnbs = [GnodeB(name="some.gnb.name", tac=1)]
            self.mock_list_gnbs.return_value = existing_gnbs
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_core_gnb_relation_1 = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={"gnb-name": "some.gnb.name"},
            )
            fiveg_core_gnb_relation_2 = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={"gnb-name": "my_gnb"},
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation_1,
                    fiveg_core_gnb_relation_2,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.relation_changed(fiveg_core_gnb_relation_2), state_in)

            self.mock_create_gnb.assert_called_once_with(
                name="my_gnb", tac=None, token="test-token"
            )
            self.mock_delete_gnb.assert_not_called()

    def test_given_two_n4_relations_when_n4_relation_broken_then_upf_is_removed_from_nms(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            existing_upfs = [
                Upf(hostname="some.host.name", port=1234),
                Upf(hostname="some.host", port=22),
            ]
            self.mock_list_upfs.return_value = existing_upfs
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_n4_relation_1 = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            fiveg_n4_relation_2 = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host",
                    "upf_port": "22",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_n4_relation_1,
                    fiveg_n4_relation_2,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.relation_broken(fiveg_n4_relation_1), state_in)

            self.mock_delete_upf.assert_called_once_with(
                hostname="some.host.name", token="test-token"
            )
            self.mock_create_upf.assert_not_called()
            self.mock_update_upf.assert_not_called()

    def test_given_two_fiveg_core_gnb_relations_when_relation_broken_then_gnb_is_removed_from_nms(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            existing_gnbs = [
                GnodeB(name="some.gnb.name"),
                GnodeB(name="gnb.name"),
            ]
            self.mock_list_gnbs.return_value = existing_gnbs
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_core_gnb_relation_1 = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            fiveg_core_gnb_relation_2 = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "gnb.name",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation_1,
                    fiveg_core_gnb_relation_2,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.relation_broken(fiveg_core_gnb_relation_1), state_in)

            self.mock_delete_gnb.assert_called_once_with(name="some.gnb.name", token="test-token")
            self.mock_create_gnb.assert_not_called()

    def test_given_one_upf_in_nms_when_upf_is_modified_in_relation_then_nms_upf_is_updated(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            existing_upfs = [
                Upf(hostname="some.host.name", port=1234),
            ]
            self.mock_list_upfs.return_value = existing_upfs
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "22",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_n4_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.relation_joined(fiveg_n4_relation), state_in)

            self.mock_delete_upf.assert_not_called()
            self.mock_create_upf.assert_not_called()
            self.mock_update_upf.assert_called_once_with(
                hostname="some.host.name", port=22, token="test-token"
            )

    def test_given_one_gnb_in_nms_when_gnb_is_added_in_relation_then_old_gnb_is_removed_and_new_is_created(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            existing_gnbs = [
                GnodeB(name="some.gnb.name"),
            ]
            self.mock_list_gnbs.return_value = existing_gnbs
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.new.gnb.name",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.relation_changed(fiveg_core_gnb_relation), state_in)

            self.mock_delete_gnb.assert_called_once_with(name="some.gnb.name", token="test-token")
            self.mock_create_gnb.assert_called_once_with(
                name="some.new.gnb.name", tac=None, token="test-token"
            )

    def test_given_one_upf_in_nms_when_new_upf_is_added_then_old_upf_is_removed_and_new_upf_is_created(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            existing_upfs = [
                Upf(hostname="old.name", port=1234),
            ]
            self.mock_list_upfs.return_value = existing_upfs
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "22",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_n4_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.relation_joined(fiveg_n4_relation), state_in)

            self.mock_delete_upf.assert_called_once_with(hostname="old.name", token="test-token")
            self.mock_update_upf.assert_not_called()
            self.mock_create_upf.assert_called_once_with(
                hostname="some.host.name", port=22, token="test-token"
            )

    def test_given_cannot_connect_to_container_when_certificates_relation_broken_then_certificates_are_not_removed(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            existing_gnbs = [
                GnodeB(name="old.gnb.name", tac=1234),
            ]
            self.mock_list_gnbs.return_value = existing_gnbs
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=False,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            self.ctx.run(self.ctx.on.relation_broken(certificates_relation), state_in)

    def test_given_gnb_in_nms_when_network_slice_config_for_gnb_changes_then_gnb_config_updated_in_fiveg_core_gnb_relation_data(  # noqa: E501
        self,
    ):
        test_pebble_notice = scenario.Notice("aetherproject.org/webconsole/networkslice/create")
        test_gnb_name = "some.gnb.name"
        test_mcc = "123"
        test_mnc = "98"
        test_sst = 1
        test_sd = 102030
        test_plmn_config = PLMNConfig(test_mcc, test_mnc, test_sst, test_sd)
        test_tac = 1
        expected_local_app_data = {"tac": '1', "plmns": json.dumps([test_plmn_config.asdict()])}
        with (tempfile.TemporaryDirectory() as tempdir):
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            self.mock_list_gnbs.return_value = [GnodeB(name=test_gnb_name, tac=test_tac)]
            self.mock_list_network_slices.return_value = ["default"]
            self.mock_get_network_slice.return_value = NetworkSlice(
                mcc=test_mcc,
                mnc=test_mnc,
                sst=test_sst,
                sd=test_sd,
                gnodebs=[GnodeB(name=test_gnb_name, tac=test_tac)],
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
                notices=[test_pebble_notice]
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            state_out = self.ctx.run(
                self.ctx.on.pebble_custom_notice(container, test_pebble_notice),
                state_in,
            )

            assert state_out.get_relation(
                fiveg_core_gnb_relation.id
            ).local_app_data == expected_local_app_data

    def test_given_two_gnbs_in_nms_when_network_slice_config_for_gnb_1_changes_then_gnb_2_config_is_not_updated_in_fiveg_core_gnb_relation_data(  # noqa: E501
        self,
    ):
        test_pebble_notice = scenario.Notice("aetherproject.org/webconsole/networkslice/create")
        test_gnb_name = "some.gnb.name"
        test_gnb_2_name = "some.other.gnb.name"
        test_mcc = "123"
        test_mnc = "98"
        test_sst = 1
        test_sd = 102030
        with tempfile.TemporaryDirectory() as tempdir:
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            self.mock_list_gnbs.return_value = [
                GnodeB(name=test_gnb_name),
                GnodeB(name=test_gnb_2_name),
            ]
            self.mock_list_network_slices.return_value = ["default"]
            self.mock_get_network_slice.return_value = NetworkSlice(
                mcc=test_mcc,
                mnc=test_mnc,
                sst=test_sst,
                sd=test_sd,
                gnodebs=[GnodeB(name=test_gnb_name, tac=1)],
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
                notices=[test_pebble_notice]
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": test_gnb_name,
                },
            )
            fiveg_core_gnb_relation_2 = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": test_gnb_2_name,
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation,
                    fiveg_core_gnb_relation_2,
                },
            )
            self.mock_certificate_is_available.return_value = True

            state_out = self.ctx.run(
                self.ctx.on.pebble_custom_notice(container, test_pebble_notice),
                state_in,
            )

            assert state_out.get_relation(fiveg_core_gnb_relation_2.id).local_app_data == {}

    def test_given_gnb_belongs_to_two_network_slices_when_network_slice_config_changes_then_fiveg_core_gnb_relation_data_contains_two_plmns(  # noqa: E501
        self,
    ):
        test_pebble_notice = scenario.Notice("aetherproject.org/webconsole/networkslice/create")
        test_gnb_name = "some.gnb.name"
        test_mcc = "123"
        test_mcc_2 = "321"
        test_mnc = "98"
        test_mnc_2 = "89"
        test_sst = 1
        test_sst_2 = 2
        test_sd = 102030
        test_sd_2 = 301020
        test_tac = 1
        test_plmn_config = PLMNConfig(test_mcc, test_mnc, test_sst, test_sd)
        test_plmn_2_config = PLMNConfig(test_mcc_2, test_mnc_2, test_sst_2, test_sd_2)
        expected_local_app_data = {
            "tac": '1',
            "plmns": json.dumps([test_plmn_config.asdict(), test_plmn_2_config.asdict()]),
        }
        with (tempfile.TemporaryDirectory() as tempdir):
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "2.2.2.2:1234",
                },
            )
            webui_database_relation = scenario.Relation(
                endpoint="webui_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "carrot",
                    "password": "hotdog",
                    "uris": "1.1.1.1:1234",
                },
            )
            certificates_relation = scenario.Relation(
                endpoint="certificates", interface="tls-certificates"
            )
            self.mock_list_gnbs.return_value = [GnodeB(name=test_gnb_name)]
            self.mock_list_network_slices.return_value = ["slice_one", "slice_two"]
            self.mock_get_network_slice.side_effect = [
                NetworkSlice(
                    test_mcc, test_mnc, test_sst, test_sd,
                    [GnodeB(name=test_gnb_name, tac=test_tac)]
                ),
                NetworkSlice(
                    test_mcc_2, test_mnc_2, test_sst_2, test_sd_2,
                    [GnodeB(name=test_gnb_name, tac=test_tac)]
                ),
            ]
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            certs_mount = scenario.Mount(
                location="/support/TLS",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={
                    "config": config_mount,
                    "certs": certs_mount,
                },
                notices=[test_pebble_notice]
            )
            fiveg_core_gnb_relation = scenario.Relation(
                endpoint="fiveg_core_gnb",
                interface="fiveg_core_gnb",
                remote_app_data={
                    "gnb-name": "some.gnb.name",
                },
            )
            login_secret = scenario.Secret(
                {"username": "hello", "password": "world", "token": "test-token"},
                id="1",
                label="NMS_LOGIN",
                owner="app",
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                secrets={login_secret},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    webui_database_relation,
                    certificates_relation,
                    fiveg_core_gnb_relation,
                },
            )
            self.mock_certificate_is_available.return_value = True

            state_out = self.ctx.run(
                self.ctx.on.pebble_custom_notice(container, test_pebble_notice),
                state_in,
            )

            assert state_out.get_relation(
                fiveg_core_gnb_relation.id
            ).local_app_data == expected_local_app_data
