# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


from fixtures import (
    AUTH_DATABASE_RELATION_NAME,
    COMMON_DATABASE_RELATION_NAME,
    CONTAINER,
    CONTAINER_CONFIG_FILE_PATH,
    NMSUnitTestFixtures,
)
from ops.model import ActiveStatus, BlockedStatus, ModelError, WaitingStatus


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
        (root / CONTAINER_CONFIG_FILE_PATH).write_text("something")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus("Waiting for NMS service to start")  # noqa: E501

    def test_given_container_ready_db_relations_exist_storage_attached_and_config_files_exist_when_evaluate_status_then_status_is_active(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / CONTAINER_CONFIG_FILE_PATH).write_text("something")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

    def test_given_container_ready_all_relations_exist_storage_attached_and_config_files_exist_when_evaluate_status_then_status_is_active(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        existing_gnbs = [{"name": "some.gnb.name", "tac": "1234"}]
        gnb_mock_response = self.get_inventory_mock_response(existing_gnbs)
        existing_upfs = [{"hostname": "some.host.name", "port": "1234"}]
        upf_mock_response = self.get_inventory_mock_response(existing_upfs)
        self.mock_request_get.side_effect = [gnb_mock_response, upf_mock_response]

        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / CONTAINER_CONFIG_FILE_PATH).write_text("something")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

    def test_given_charm_active_status_when_database_relation_breaks_then_status_is_blocked(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / CONTAINER_CONFIG_FILE_PATH).write_text("something")

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

        self.harness.remove_relation(common_database_relation_id)
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == BlockedStatus(
            "Waiting for common_database relation to be created"
        )
