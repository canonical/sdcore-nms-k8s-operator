# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


import tempfile

import scenario
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus
from ops.pebble import Layer, ServiceStatus

from tests.unit.fixtures import NMSUnitTestFixtures


class TestCharmCollectStatus(NMSUnitTestFixtures):
    def test_given_unit_is_not_leader_when_collect_unit_status_then_status_is_blocked(self):
        state_in = scenario.State(leader=False)

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus("Scaling is not implemented for this charm")

    def test_given_common_database_relation_not_created_when_collect_unit_status_then_status_is_blocked(  # noqa: E501
        self,
    ):
        auth_database_relation = scenario.Relation(
            endpoint="auth_database",
            interface="mongodb_client",
        )
        state_in = scenario.State(leader=True, relations={auth_database_relation})

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus(
            "Waiting for common_database relation to be created"
        )

    def test_given_auth_database_relation_not_created_when_collect_unit_status_then_status_is_blocked(  # noqa: E501
        self,
    ):
        common_database_relation = scenario.Relation(
            endpoint="common_database",
            interface="mongodb_client",
        )
        state_in = scenario.State(leader=True, relations={common_database_relation})

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == BlockedStatus(
            "Waiting for auth_database relation to be created"
        )

    def test_given_common_db_relation_is_created_but_not_available_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        auth_database_relation = scenario.Relation(
            endpoint="auth_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "apple",
                "password": "hamburger",
                "uris": "1.2.3.4:1234",
            },
        )
        common_database_relation = scenario.Relation(
            endpoint="common_database", interface="mongodb_client", remote_app_data={}
        )
        state_in = scenario.State(
            leader=True,
            relations={auth_database_relation, common_database_relation},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus(
            "Waiting for the common database to be available"
        )

    def test_given_auth_db_relation_is_created_but_not_available_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        auth_database_relation = scenario.Relation(
            endpoint="auth_database", interface="mongodb_client", remote_app_data={}
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
        state_in = scenario.State(
            leader=True,
            relations={auth_database_relation, common_database_relation},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus(
            "Waiting for the auth database to be available"
        )

    def test_given_storage_attached_but_cannot_connect_to_container_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        auth_database_relation = scenario.Relation(
            endpoint="auth_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "apple",
                "password": "hamburger",
                "uris": "1.2.3.4:1234",
            },
        )
        common_database_relation = scenario.Relation(
            endpoint="common_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "banana",
                "password": "pizza",
                "uris": "2.3.1.1:1234",
            },
        )
        container = scenario.Container(
            name="nms",
            can_connect=False,
        )
        state_in = scenario.State(
            leader=True,
            relations={auth_database_relation, common_database_relation},
            containers={container},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for container to be ready")

    def test_given_storage_not_attached_when_collect_unit_status_then_status_is_waiting(
        self,
    ):
        auth_database_relation = scenario.Relation(
            endpoint="auth_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "apple",
                "password": "hamburger",
                "uris": "1.8.11.4:1234",
            },
        )
        common_database_relation = scenario.Relation(
            endpoint="common_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "banana",
                "password": "pizza",
                "uris": "11.11.1.1:1234",
            },
        )

        container = scenario.Container(
            name="nms",
            can_connect=True,
            mounts={},
        )
        state_in = scenario.State(
            leader=True,
            relations={auth_database_relation, common_database_relation},
            containers={container},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.unit_status == WaitingStatus("Waiting for storage to be attached")

    def test_given_nms_config_file_does_not_exist_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "apple",
                    "password": "hamburger",
                    "uris": "1.8.11.4:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
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
                mounts={"config": config_mount},
            )
            state_in = scenario.State(
                leader=True,
                relations={auth_database_relation, common_database_relation},
                containers={container},
            )

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == WaitingStatus(
                "Waiting for nms config file to be stored"
            )

    def test_given_service_is_not_running_when_collect_unit_status_then_status_is_waiting(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "apple",
                    "password": "hamburger",
                    "uris": "1.2.3.4:1234",
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
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={"config": config_mount},
            )
            state_in = scenario.State(
                leader=True,
                relations={auth_database_relation, common_database_relation},
                containers={container},
            )
            with open(f"{tempdir}/nmscfg.conf", "w") as f:
                f.write("whatever config file content")

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == WaitingStatus("Waiting for NMS service to start")

    def test_given_nms_api_not_available_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        self.mock_is_api_available.return_value = False
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "apple",
                    "password": "hamburger",
                    "uris": "1.2.3.4:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={"config": config_mount},
                layers={"nms": Layer({"services": {"nms": {}}})},
                service_statuses={"nms": ServiceStatus.ACTIVE},
            )
            state_in = scenario.State(
                leader=True,
                relations={auth_database_relation, common_database_relation},
                containers={container},
            )
            with open(f"{tempdir}/nmscfg.conf", "w") as f:
                f.write("whatever config file content")

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == WaitingStatus("NMS API not yet available")

    def test_given_nms_not_initialized_when_collect_unit_status_then_status_is_waiting(  # noqa: E501
        self,
    ):
        self.mock_is_api_available.return_value = True
        self.mock_is_initialized.return_value = False
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "apple",
                    "password": "hamburger",
                    "uris": "1.2.3.4:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={"config": config_mount},
                layers={"nms": Layer({"services": {"nms": {}}})},
                service_statuses={"nms": ServiceStatus.ACTIVE},
            )
            state_in = scenario.State(
                leader=True,
                relations={auth_database_relation, common_database_relation},
                containers={container},
            )
            with open(f"{tempdir}/nmscfg.conf", "w") as f:
                f.write("whatever config file content")

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == WaitingStatus("NMS not yet initialized")

    def test_given_container_ready_db_relations_exist_storage_attached_and_config_files_exist_when_collect_unit_status_then_status_is_active(  # noqa: E501
        self,
    ):
        self.mock_is_api_available.return_value = True
        self.mock_is_initialized.return_value = True
        with tempfile.TemporaryDirectory() as tempdir:
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "apple",
                    "password": "hamburger",
                    "uris": "1.2.3.4:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                source=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={"config": config_mount},
                layers={"nms": Layer({"services": {"nms": {}}})},
                service_statuses={"nms": ServiceStatus.ACTIVE},
            )
            state_in = scenario.State(
                leader=True,
                relations={auth_database_relation, common_database_relation},
                containers={container},
            )
            with open(f"{tempdir}/nmscfg.conf", "w") as f:
                f.write("whatever config file content")

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.unit_status == ActiveStatus()

    def test_given_no_workload_version_file_when_collect_unit_status_then_workload_version_not_set(
        self,
    ):
        auth_database_relation = scenario.Relation(
            endpoint="auth_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "apple",
                "password": "hamburger",
                "uris": "1.2.3.4:1234",
            },
        )
        common_database_relation = scenario.Relation(
            endpoint="common_database",
            interface="mongodb_client",
            remote_app_data={
                "username": "banana",
                "password": "pizza",
                "uris": "1.1.1.1:1234",
            },
        )

        container = scenario.Container(
            name="nms",
            can_connect=True,
            layers={"nms": Layer({"services": {"nms": {}}})},
            service_statuses={"nms": ServiceStatus.ACTIVE},
        )
        state_in = scenario.State(
            leader=True,
            relations={auth_database_relation, common_database_relation},
            containers={container},
        )

        state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

        assert state_out.workload_version == ""

    def test_given_workload_version_file_when_collect_unit_status_then_workload_version_not_set(
        self,
    ):
        with tempfile.TemporaryDirectory() as tempdir:
            expected_version = "1.2.3"
            workload_version_mount = scenario.Mount(
                location="/etc",
                source=tempdir,
            )
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "apple",
                    "password": "hamburger",
                    "uris": "1.2.3.4:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={"workload-version": workload_version_mount},
            )
            state_in = scenario.State(
                leader=True,
                relations={auth_database_relation, common_database_relation},
                containers={container},
            )

            with open(f"{tempdir}/workload-version", "w") as f:
                f.write(expected_version)

            state_out = self.ctx.run(self.ctx.on.collect_unit_status(), state_in)

            assert state_out.workload_version == expected_version
