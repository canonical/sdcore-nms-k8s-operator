# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
from fixtures import NMSUnitTestFixtures
from ops.model import ActiveStatus, BlockedStatus, ModelError, WaitingStatus

AUTH_DATABASE_RELATION_NAME = "auth_database"
COMMON_DATABASE_RELATION_NAME = "common_database"
CONTAINER = "nms"
GNB_CONFIG_FILE = "nms/config/gnb_config.json"
UPF_CONFIG_FILE = "nms/config/upf_config.json"
WEBUI_CONFIG_FILE_PATH = "nms/config/webuicfg.conf"


class TestCharmStatus(NMSUnitTestFixtures):

    def test_given_unit_is_not_leader_when_collect_status_then_status_is_blocked(self):
        self.harness.set_leader(is_leader=False)

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == BlockedStatus("Scaling is not implemented for this charm")  # noqa: E501

    def test_given_common_database_relation_not_created_when_collect_status_then_status_is_blocked(
        self, auth_database_relation_id
    ):
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == BlockedStatus("Waiting for common_database relation to be created")  # noqa: E501

    def test_given_auth_database_relation_not_created_when_collect_status_then_status_is_blocked(
        self, common_database_relation_id
    ):
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == BlockedStatus("Waiting for auth_database relation to be created")  # noqa: E501

    @pytest.mark.parametrize(
        "existing_file,missing_config",
        [
            pytest.param(UPF_CONFIG_FILE, "GNB", id="gNB_config_file_is_missing"),
            pytest.param(GNB_CONFIG_FILE, "UPF", id="UPF_config_file_is_missing"),
        ],
    )
    def test_given_config_file_not_available_when_evaluate_status_then_status_is_waiting(
        self, existing_file, missing_config, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.disable_hooks()
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / WEBUI_CONFIG_FILE_PATH).write_text("something")
        (root / existing_file).write_text("something")

        self.harness.enable_hooks()
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus(
            f"Waiting for {missing_config} config file to be stored"
        )

    def test_given_storage_not_attached_when_on_databases_are_created_then_status_is_waiting(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus(
            "Waiting for storage to be attached"
        )

    def test_given_storage_attached_but_cannot_connect_to_container_when_db_created_then_status_is_waiting(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=False)
        self.harness.add_storage("config", attach=True)

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus("Waiting for container to be ready")

    def test_given_common_db_relation_is_created_but_not_available_when_collect_status_then_status_is_waiting(  # noqa: E501
        self, auth_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.harness.add_relation(COMMON_DATABASE_RELATION_NAME, "mongodb")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus("Waiting for the common database to be available")  # noqa: E501

    def test_given_auth_db_relation_is_created_but_not_available_when_collect_status_then_status_is_waiting(  # noqa: E501
        self, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.harness.add_relation(AUTH_DATABASE_RELATION_NAME, "mongodb")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus("Waiting for the auth database to be available")  # noqa: E501

    def test_given_webui_config_file_does_not_exist_when_collect_status_then_status_is_waiting(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus("Waiting for webui config file to be stored")  # noqa: E501

    def test_given_service_is_not_running_when_collect_status_then_status_is_waiting(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.mock_get_service.side_effect = ModelError()
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / WEBUI_CONFIG_FILE_PATH).write_text("something")
        (root / UPF_CONFIG_FILE).write_text("some")
        (root / GNB_CONFIG_FILE).write_text("content")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus("Waiting for NMS service to start")  # noqa: E501

    def test_given_container_ready_db_relations_exist_storage_attached_and_config_files_exist_when_evaluate_status_then_status_is_active(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / WEBUI_CONFIG_FILE_PATH).write_text("something")
        (root / UPF_CONFIG_FILE).write_text("some")
        (root / GNB_CONFIG_FILE).write_text("content")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

    def test_given_container_ready_all_relations_exist_storage_attached_and_config_files_exist_when_evaluate_status_then_status_is_active(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / WEBUI_CONFIG_FILE_PATH).write_text("something")
        (root / UPF_CONFIG_FILE).write_text("some")
        (root / GNB_CONFIG_FILE).write_text("content")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

    def test_given_charm_active_status_when_database_relation_breaks_then_status_is_blocked(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / WEBUI_CONFIG_FILE_PATH).write_text("something")
        (root / UPF_CONFIG_FILE).write_text("some")
        (root / GNB_CONFIG_FILE).write_text("content")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

        self.harness.remove_relation(common_database_relation_id)
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == BlockedStatus(
            "Waiting for common_database relation to be created"
        )
