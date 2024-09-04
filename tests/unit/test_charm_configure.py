# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import tempfile
from unittest.mock import call

import pytest
import scenario
from ops.pebble import Layer

from tests.unit.fixtures import (
    NMSUnitTestFixtures,
)
from webui import GnodeB, Upf

EXPECTED_CONFIG_FILE_PATH = "tests/unit/expected_webui_cfg.yaml"


class TestCharmConfigure(NMSUnitTestFixtures):
    def test_given_db_relations_do_not_exist_when_pebble_ready_then_webui_config_file_is_not_written(  # noqa: E501
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

            assert not os.path.exists(f"{tempdir}/webuicfg.conf")

    def test_given_common_db_resource_not_available_when_pebble_ready_then_webui_config_file_is_not_written(  # noqa: E501
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
                relations={common_database_relation, auth_database_relation},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert not os.path.exists(f"{tempdir}/webuicfg.conf")

    def test_given_auth_db_resource_not_available_when_pebble_ready_then_webui_config_file_is_not_written(  # noqa: E501
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
                relations={common_database_relation, auth_database_relation},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert not os.path.exists(f"{tempdir}/webuicfg.conf")

    def test_given_storage_attached_and_webui_config_file_does_not_exist_when_pebble_ready_then_config_file_is_written(  # noqa: E501
        self,
    ):
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
                relations={common_database_relation, auth_database_relation},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert os.path.exists(f"{tempdir}/webuicfg.conf")
            with open(f"{tempdir}/webuicfg.conf", "r") as f:
                assert f.read() == open(EXPECTED_CONFIG_FILE_PATH, "r").read()

    def test_given_container_is_ready_db_relations_exist_and_storage_attached_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
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
                relations={common_database_relation, auth_database_relation},
            )

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert state_out.get_container("nms").layers["nms"] == Layer(
                {
                    "summary": "NMS layer",
                    "description": "pebble config layer for the NMS",
                    "services": {
                        "nms": {
                            "startup": "enabled",
                            "override": "replace",
                            "command": "/bin/webconsole --webuicfg /nms/config/webuicfg.conf",
                            "environment": {
                                "GRPC_GO_LOG_VERBOSITY_LEVEL": "99",
                                "GRPC_GO_LOG_SEVERITY_LEVEL": "info",
                                "GRPC_TRACE": "all",
                                "GRPC_VERBOSITY": "debug",
                                "CONFIGPOD_DEPLOYMENT": "5G",
                                "WEBUI_ENDPOINT": "None:5000",
                            },
                        }
                    },
                }
            )

    def test_given_db_relations_do_not_exist_when_pebble_ready_then_pebble_plan_is_empty(self):
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

            state_out = self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            assert state_out.get_container("nms").layers == {}

    def test_given_storage_not_attached_when_pebble_ready_then_config_url_is_not_published_for_relations(  # noqa: E501
        self,
    ):
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
        container = scenario.Container(
            name="nms",
            can_connect=True,
        )
        state_in = scenario.State(
            leader=True,
            containers={container},
            relations={sdcore_config_relation, common_database_relation, auth_database_relation},
        )

        self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

        self.mock_set_webui_url_in_all_relations.assert_not_called()

    def test_given_webui_service_is_running_db_relations_are_not_joined_when_pebble_ready_then_config_url_is_not_published_for_relations(  # noqa: E501
        self,
    ):
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

    def test_given_webui_service_is_running_db_relations_are_joined_when_several_sdcore_config_relations_are_joined_then_config_url_is_set_in_all_relations(  # noqa: E501
        self,
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
                relations={
                    auth_database_relation,
                    common_database_relation,
                    sdcore_config_relation_1,
                    sdcore_config_relation_2,
                },
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_set_webui_url_in_all_relations.assert_called_with(
                webui_url="sdcore-nms-k8s:9876"
            )

    def test_given_webui_service_is_not_running_when_pebble_ready_then_config_url_is_not_set_in_the_relations(  # noqa: E501
        self,
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
                can_connect=False,
                mounts={
                    "config": config_mount,
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    auth_database_relation,
                    common_database_relation,
                    sdcore_config_relation,
                },
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_set_webui_url_in_all_relations.assert_not_called()

    @pytest.mark.parametrize("relation_name", [("fiveg_n4"), ("fiveg_gnb_identity")])
    def test_given_storage_not_attached_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
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

    @pytest.mark.parametrize("relation_name", [("fiveg_n4"), ("fiveg_gnb_identity")])
    def test_given_cannot_connect_to_container_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
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

    @pytest.mark.parametrize(
        "relation_name,relation_data",
        [
            pytest.param(
                "fiveg_gnb_identity",
                {"tac": "1234"},
                id="missing_gnb_name_in_gNB_config",
            ),
            pytest.param(
                "fiveg_gnb_identity",
                {"gnb_name": "some.gnb"},
                id="missing_tac_in_gNB_config",
            ),
            pytest.param(
                "fiveg_gnb_identity",
                {"tac": "", "gnb_name": ""},
                id="gnb_name_and_tac_are_empty_strings_in_gNB_config",
            ),
            pytest.param(
                "fiveg_gnb_identity",
                {"gnb_name": "something", "some": "key"},
                id="invalid_key_in_gNB_config",
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
    def test_given_incomplete_data_in_relation_when_pebble_ready_then_is_not_updated_in_webui_db(
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
            relation = scenario.Relation(
                endpoint=relation_name,
                interface=relation_name,
                remote_app_data=relation_data,
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
                relations={relation, auth_database_relation, common_database_relation},
                containers={container},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_add_gnb.assert_not_called()
            self.mock_add_upf.assert_not_called()
            self.mock_delete_gnb.assert_not_called()
            self.mock_delete_upf.assert_not_called()

    def test_given_no_db_relations_when_pebble_ready_then_webui_resources_are_not_updated(self):
        with tempfile.TemporaryDirectory() as tempdir:
            fiveg_gnb_identity_relation = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "1234",
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
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={fiveg_gnb_identity_relation, fiveg_n4_relation},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_add_gnb.assert_not_called()
            self.mock_delete_gnb.assert_not_called()
            self.mock_add_upf.assert_not_called()
            self.mock_delete_upf.assert_not_called()

    def test_given_db_relations_when_pebble_ready_then_webui_url_is_updated(
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
            fiveg_gnb_identity_relation = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "1234",
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
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_gnb_identity_relation,
                    fiveg_n4_relation,
                },
            )
            self.mock_check_output.return_value = "1.2.3.4".encode()

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_webui_set_url.assert_called_once_with("http://1.2.3.4:5000")

    def test_given_db_relations_when_pebble_ready_then_webui_upf_is_updated(
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
            fiveg_gnb_identity_relation = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "1234",
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
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_gnb_identity_relation,
                    fiveg_n4_relation,
                },
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            expected_upf = Upf(hostname="some.host.name", port=1234)
            self.mock_add_upf.assert_called_once_with(expected_upf)

    def test_given_db_relations_when_pebble_ready_then_webui_gnb_is_updated(
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
            fiveg_gnb_identity_relation = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "1234",
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
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_gnb_identity_relation,
                    fiveg_n4_relation,
                },
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            expected_gnb = GnodeB(name="some.gnb.name", tac=1234)
            self.mock_add_gnb.assert_called_once_with(expected_gnb)

    def test_given_multiple_n4_relations_when_pebble_ready_then_both_upfs_are_added_to_webui(
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
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_n4_relation_1,
                    fiveg_n4_relation_2,
                },
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            calls = [
                call(Upf(hostname="some.host.name", port=1234)),
                call(Upf(hostname="my_host", port=77)),
            ]
            self.mock_add_upf.assert_has_calls(calls)

    def test_given_multiple_gnb_relations_when_pebble_ready_then_both_gnbs_are_added_to_webui(
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
            fiveg_gnb_identity_relation_1 = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "1234",
                },
            )
            fiveg_gnb_identity_relation_2 = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "my_gnb",
                    "tac": "77",
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
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_gnb_identity_relation_1,
                    fiveg_gnb_identity_relation_2,
                },
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            calls = [
                call(GnodeB(name="some.gnb.name", tac=1234)),
                call(GnodeB(name="my_gnb", tac=77)),
            ]
            self.mock_add_gnb.assert_has_calls(calls)

    def test_given_upf_exist_in_webui_and_relation_matches_when_pebble_ready_then_webui_upfs_are_not_updated(  # noqa: E501
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
            self.mock_get_upfs.return_value = [Upf(hostname="some.host.name", port=1234)]
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
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "1234",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={common_database_relation, auth_database_relation, fiveg_n4_relation},
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_get_upfs.assert_called()
            self.mock_add_upf.assert_not_called()

    def test_given_gnb_exist_in_webui_and_relation_matches_when_pebble_ready_then_webui_gnbs_are_not_updated(  # noqa: E501
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
            existing_gnbs = [GnodeB(name="some.gnb.name", tac=1234)]
            self.mock_get_gnbs.return_value = existing_gnbs
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
            fiveg_gnb_identity_relation = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "1234",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_gnb_identity_relation,
                },
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_get_gnbs.assert_called()
            self.mock_add_gnb.assert_not_called()

    def test_given_no_upf_or_gnb_relation_or_db_when_pebble_ready_then_webui_resources_are_not_updated(  # noqa: E501
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
                relations=frozenset(),
            )

            self.ctx.run(self.ctx.on.pebble_ready(container), state_in)

            self.mock_add_gnb.assert_not_called()

    def test_given_upf_exists_in_webui_and_new_upf_relation_is_added_when_pebble_ready_then_second_upf_is_added_to_webui(  # noqa: E501
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
            existing_upf = Upf(hostname="some.host.name", port=1234)
            self.mock_get_upfs.return_value = [existing_upf]
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
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_n4_relation_1,
                    fiveg_n4_relation_2,
                },
            )

            self.ctx.run(self.ctx.on.relation_joined(fiveg_n4_relation_2), state_in)

            expected_upf = Upf(hostname="my_host", port=4567)
            self.mock_add_upf.assert_called_once_with(expected_upf)
            self.mock_delete_upf.assert_not_called()

    def test_given_gnb_exists_in_webui_and_new_gnb_relation_is_added_when_pebble_ready_then_second_gnb_is_added_to_webui(  # noqa: E501
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
            existing_gnbs = [GnodeB(name="some.gnb.name", tac=1234)]
            self.mock_get_gnbs.return_value = existing_gnbs
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
            fiveg_gnb_identity_relation_1 = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "1234",
                },
            )
            fiveg_gnb_identity_relation_2 = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "my_gnb",
                    "tac": "4567",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_gnb_identity_relation_1,
                    fiveg_gnb_identity_relation_2,
                },
            )

            self.ctx.run(self.ctx.on.relation_joined(fiveg_gnb_identity_relation_2), state_in)

            expected_gnb = GnodeB(name="my_gnb", tac=4567)
            self.mock_add_gnb.assert_called_once_with(expected_gnb)
            self.mock_delete_gnb.assert_not_called()

    def test_given_two_n4_relations_when_n4_relation_broken_then_upf_is_removed_from_webui(
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
            existing_upfs = [
                Upf(hostname="some.host.name", port=1234),
                Upf(hostname="some.host", port=22),
            ]
            self.mock_get_upfs.return_value = existing_upfs
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
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    fiveg_n4_relation_1,
                    fiveg_n4_relation_2,
                },
            )

            self.ctx.run(self.ctx.on.relation_broken(fiveg_n4_relation_1), state_in)

            self.mock_delete_upf.assert_called_once_with("some.host.name")
            self.mock_add_upf.assert_not_called()

    def test_given_two_gnb_identity_relations_when_relation_broken_then_gnb_is_removed_from_webui(  # noqa: E501
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
            existing_gnbs = [
                GnodeB(name="some.gnb.name", tac=1234),
                GnodeB(name="gnb.name", tac=333),
            ]
            self.mock_get_gnbs.return_value = existing_gnbs
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
            gnb_identity_relation_1 = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "1234",
                },
            )
            gnb_identity_relation_2 = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "gnb.name",
                    "tac": "333",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    gnb_identity_relation_1,
                    gnb_identity_relation_2,
                },
            )

            self.ctx.run(self.ctx.on.relation_broken(gnb_identity_relation_1), state_in)

            self.mock_delete_gnb.assert_called_once_with("some.gnb.name")
            self.mock_add_gnb.assert_not_called()

    def test_given_one_upf_in_webui_when_upf_is_modified_in_relation_then_webui_upfs_are_updated(  # noqa: E501
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
            existing_upfs = [
                Upf(hostname="some.host.name", port=1234),
            ]
            self.mock_get_upfs.return_value = existing_upfs
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
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "22",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={common_database_relation, auth_database_relation, fiveg_n4_relation},
            )

            self.ctx.run(self.ctx.on.relation_joined(fiveg_n4_relation), state_in)

            self.mock_delete_upf.assert_called_once_with("some.host.name")
            expected_upf = Upf(hostname="some.host.name", port=22)
            self.mock_add_upf.assert_called_once_with(expected_upf)

    def test_given_one_gnb_in_webui_when_gnb_is_modified_in_relation_then_webui_gnbs_are_updated(  # noqa: E501
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
            existing_gnbs = [
                GnodeB(name="some.gnb.name", tac=1234),
            ]
            self.mock_get_gnbs.return_value = existing_gnbs
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
            gnb_identity_relation = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "6789",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    gnb_identity_relation,
                },
            )

            self.ctx.run(self.ctx.on.relation_joined(gnb_identity_relation), state_in)

            self.mock_delete_gnb.assert_called_once_with("some.gnb.name")
            expected_gnb = GnodeB(name="some.gnb.name", tac=6789)
            self.mock_add_gnb.assert_called_once_with(expected_gnb)

    def test_given_one_upf_in_webui_when_new_upf_is_added_then_old_upf_is_removed_and_new_upf_is_added(  # noqa: E501
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
            existing_upfs = [
                Upf(hostname="old.name", port=1234),
            ]
            self.mock_get_upfs.return_value = existing_upfs
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
            fiveg_n4_relation = scenario.Relation(
                endpoint="fiveg_n4",
                interface="fiveg_n4",
                remote_app_data={
                    "upf_hostname": "some.host.name",
                    "upf_port": "22",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={common_database_relation, auth_database_relation, fiveg_n4_relation},
            )

            self.ctx.run(self.ctx.on.relation_joined(fiveg_n4_relation), state_in)

            self.mock_delete_upf.assert_called_once_with("old.name")
            expected_upf = Upf(hostname="some.host.name", port=22)
            self.mock_add_upf.assert_called_once_with(expected_upf)

    def test_given_one_gnb_in_webui_when_new_gnb_is_added_then_old_gnb_is_removed_and_new_gnb_is_added(  # noqa: E501
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
            existing_gnbs = [
                GnodeB(name="old.gnb.name", tac=1234),
            ]
            self.mock_get_gnbs.return_value = existing_gnbs
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
            gnb_identity_relation = scenario.Relation(
                endpoint="fiveg_gnb_identity",
                interface="fiveg_gnb_identity",
                remote_app_data={
                    "gnb_name": "some.gnb.name",
                    "tac": "6789",
                },
            )
            state_in = scenario.State(
                leader=True,
                containers={container},
                relations={
                    common_database_relation,
                    auth_database_relation,
                    gnb_identity_relation,
                },
            )

            self.ctx.run(self.ctx.on.relation_joined(gnb_identity_relation), state_in)

            self.mock_delete_gnb.assert_called_once_with("old.gnb.name")
            expected_gnb = GnodeB(name="some.gnb.name", tac=6789)
            self.mock_add_gnb.assert_called_once_with(expected_gnb)
