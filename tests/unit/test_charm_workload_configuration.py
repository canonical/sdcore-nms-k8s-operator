# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
from unittest.mock import call

import pytest
from fixtures import (
    AUTH_DATABASE_RELATION_NAME,
    COMMON_DATABASE_RELATION_NAME,
    CONTAINER,
    CONTAINER_CONFIG_FILE_PATH,
    FIVEG_N4_RELATION_NAME,
    GNB_IDENTITY_RELATION_NAME,
    REMOTE_APP_NAME,
    SDCORE_CONFIG_RELATION_NAME,
    NMSUnitTestFixtures,
)
from ops.model import ModelError

EXPECTED_CONFIG_FILE_PATH = "tests/unit/expected_webui_cfg.yaml"
POD_IP = "1.2.3.4"
WEBUI_ENDPOINT = f"{POD_IP}:5000"

def read_file_content(path: str) -> str:
    with open(path, "r") as f:
        content = f.read()
    return content


class TestCharmWorkloadConfiguration(NMSUnitTestFixtures):

    def test_given_db_relations_do_not_exist_when_pebble_ready_then_webui_config_file_is_not_written(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        with pytest.raises(FileNotFoundError):
            (root / CONTAINER_CONFIG_FILE_PATH).read_text()

    def test_given_common_db_resource_not_available_when_pebble_ready_then_webui_config_file_is_not_written(  # noqa: E501
        self,
    ):
        self.harness.add_relation(COMMON_DATABASE_RELATION_NAME, "mongodb")  # type:ignore
        self.harness.add_relation(AUTH_DATABASE_RELATION_NAME, "mongodb")  # type:ignore
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        with pytest.raises(FileNotFoundError):
            (root / CONTAINER_CONFIG_FILE_PATH).read_text()

    def test_given_auth_db_resource_not_available_when_pebble_ready_then_webui_config_file_is_not_written(  # noqa: E501
        self, common_database_relation_id
    ):
        self.harness.add_relation(AUTH_DATABASE_RELATION_NAME, "mongodb")  # type:ignore
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        with pytest.raises(FileNotFoundError):
            (root / CONTAINER_CONFIG_FILE_PATH).read_text()

    def test_given_storage_attached_and_webui_config_file_does_not_exist_when_pebble_ready_then_config_file_is_written(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        expected_config_file_content = read_file_content(EXPECTED_CONFIG_FILE_PATH)
        assert (root / CONTAINER_CONFIG_FILE_PATH).read_text() == expected_config_file_content

    def test_given_container_is_ready_db_relations_exist_and_storage_attached_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()
        self.harness.add_storage("config", attach=True)
        self.harness.container_pebble_ready(container_name=CONTAINER)

        expected_plan = {
            "services": {
                CONTAINER: {
                    "override": "replace",
                    "command": "/bin/webconsole --webuicfg /nms/config/webuicfg.conf",
                    "startup": "enabled",
                    "environment": {
                        "GRPC_GO_LOG_VERBOSITY_LEVEL": "99",
                        "GRPC_GO_LOG_SEVERITY_LEVEL": "info",
                        "GRPC_TRACE": "all",
                        "GRPC_VERBOSITY": "debug",
                        "CONFIGPOD_DEPLOYMENT": "5G",
                        "WEBUI_ENDPOINT": WEBUI_ENDPOINT,
                    },
                }
            },
        }
        updated_plan = self.harness.get_container_pebble_plan(CONTAINER).to_dict()
        assert expected_plan == updated_plan

    def test_given_container_is_ready_all_relations_exist_and_storage_attached_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready(container_name=CONTAINER)

        expected_plan = {
            "services": {
                CONTAINER: {
                    "override": "replace",
                    "command": "/bin/webconsole --webuicfg /nms/config/webuicfg.conf",
                    "startup": "enabled",
                    "environment": {
                        "GRPC_GO_LOG_VERBOSITY_LEVEL": "99",
                        "GRPC_GO_LOG_SEVERITY_LEVEL": "info",
                        "GRPC_TRACE": "all",
                        "GRPC_VERBOSITY": "debug",
                        "CONFIGPOD_DEPLOYMENT": "5G",
                        "WEBUI_ENDPOINT": WEBUI_ENDPOINT,
                    },
                }
            },
        }
        updated_plan = self.harness.get_container_pebble_plan(CONTAINER).to_dict()
        assert expected_plan == updated_plan

    def test_given_db_relations_do_not_exist_when_pebble_ready_then_pebble_plan_is_empty(self):
        self.harness.add_storage("config", attach=True)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        assert {} == self.harness.get_container_pebble_plan(CONTAINER).to_dict()

    def test_given_storage_not_attached_when_pebble_ready_then_config_url_is_not_published_for_relations(  # noqa: E501
        self, sdcore_config_relation_id, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=False)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        self.mock_set_webui_url_in_all_relations.assert_not_called()

    def test_given_webui_service_is_running_db_relations_are_not_joined_when_pebble_ready_then_config_url_is_not_published_for_relations(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        self.harness.add_storage("config", attach=True)
        self.mock_get_service.side_effect = None

        self.harness.container_pebble_ready(container_name=CONTAINER)

        self.mock_set_webui_url_in_all_relations.assert_not_called()

    def test_given_webui_service_is_running_db_relations_are_joined_when_several_sdcore_config_relations_are_joined_then_config_url_is_set_in_all_relations(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.mock_get_service.side_effect = None
        relation_id_1 = self.harness.add_relation(SDCORE_CONFIG_RELATION_NAME, "requirer1")
        self.harness.add_relation_unit(relation_id=relation_id_1, remote_unit_name="requirer1")
        relation_id_2 = self.harness.add_relation(SDCORE_CONFIG_RELATION_NAME, "requirer2")
        self.harness.add_relation_unit(relation_id=relation_id_2, remote_unit_name="requirer2")
        calls = [
            call.emit(webui_url="webui:9876"),
            call.emit(webui_url="webui:9876"),
        ]
        self.mock_set_webui_url_in_all_relations.assert_has_calls(calls)

    def test_given_webui_service_is_not_running_when_pebble_ready_then_config_url_is_not_set_in_the_relations(  # noqa: E501
        self, sdcore_config_relation_id, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_get_service.side_effect = ModelError()
        self.harness.add_storage("config", attach=True)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        self.mock_set_webui_url_in_all_relations.assert_not_called()

    @pytest.mark.parametrize(
        "relation_name", [(FIVEG_N4_RELATION_NAME), (GNB_IDENTITY_RELATION_NAME)]
    )
    def test_given_storage_not_attached_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.remove_relation(relation_id)

    @pytest.mark.parametrize(
        "relation_name", [(FIVEG_N4_RELATION_NAME), (GNB_IDENTITY_RELATION_NAME)]
    )
    def test_given_cannot_connect_to_container_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
        self.harness.add_storage("config", attach=True)
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container=CONTAINER, val=False)

        self.harness.remove_relation(relation_id)

    def test_given_no_workload_version_file_when_pebble_ready_then_workload_version_not_set(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.evaluate_status()

        version = self.harness.get_workload_version()
        assert version == ""

    def test_given_workload_version_file_when_pebble_ready_then_workload_version_set(
        self, auth_database_relation_id, common_database_relation_id
    ):
        expected_version = "1.2.3"
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        os.mkdir(f"{root}/etc")
        (root / "etc/workload-version").write_text(expected_version)
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.evaluate_status()

        version = self.harness.get_workload_version()
        assert version == expected_version
