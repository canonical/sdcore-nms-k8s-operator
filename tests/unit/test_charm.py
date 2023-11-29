# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from unittest.mock import Mock, patch

from ops import testing
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from charm import SDCoreNMSOperatorCharm

FIVEG_N4_RELATION_NAME = "fiveg_n4"
TEST_FIVEG_N4_PROVIDER_APP_NAME = "fiveg_n4_provider_app"
SDCORE_MANAGEMENT_RELATION_NAME = "sdcore-management"
TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME = "sdcore_management_provider_app"
GNB_IDENTITY_RELATION_NAME = "fiveg_gnb_identity"
TEST_GNB_IDENTITY_PROVIDER_APP_NAME = "fiveg_gnb_identity_provider_app"
TEST_UPF_CONFIG_PATH = "/nms/config/upf_config.json"
TEST_GNB_CONFIG_PATH = "/nms/config/gnb_config.json"
TEST_GNB_STORAGE = TEST_GNB_CONFIG_PATH[1:]
TEST_UPF_STORAGE = TEST_UPF_CONFIG_PATH[1:]


class TestCharm(unittest.TestCase):
    @patch(
        "charm.KubernetesServicePatch",
        lambda charm, ports: None,
    )
    def setUp(self):
        self.harness = testing.Harness(SDCoreNMSOperatorCharm)
        self.harness.add_storage("config", attach=True)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def _add_mandatory_integrations(self):
        sdcore_management_relation_id = self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=sdcore_management_relation_id,
            app_or_unit=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
            key_values={"management_url": "http://10.0.0.1:5000"},
        )

    def test_given_cant_connect_to_container_when_configure_sdcore_nms_then_status_is_waiting(
        self,
    ):
        self.harness.charm._configure_sdcore_nms(event=Mock())
        self.assertEqual(
            self.harness.model.unit.status, WaitingStatus("Waiting for container to be ready")
        )

    def test_given_sdcore_management_relation_not_created_when_pebble_ready_then_status_is_blocked(
        self,
    ):
        self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.container_pebble_ready("nms")
        self.assertEqual(
            self.harness.model.unit.status,
            BlockedStatus(
                f"Waiting for `{SDCORE_MANAGEMENT_RELATION_NAME}` relation to be created"
            ),
        )

    def test_given_management_url_not_available_when_pebble_ready_then_status_is_waiting(self):
        self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.container_pebble_ready("nms")
        self.assertEqual(
            self.harness.model.unit.status,
            WaitingStatus("Waiting for webui management url to be available"),
        )

    def test_given_management_url_available_when_pebble_ready_then_status_is_active(self):
        sdcore_management_relation_id = self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=sdcore_management_relation_id,
            app_or_unit=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
            key_values={"management_url": "http://10.0.0.1:5000"},
        )
        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_given_n4_information_not_available_when_pebble_ready_then_status_is_active(self):
        self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_given_gnb_identity_information_not_available_when_pebble_ready_then_status_is_active(
        self,
    ):
        self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_given_gnb_identity_gnb_name_not_available_when_pebble_ready_then_status_is_active(
        self,
    ):
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"tac": "1234"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_given_gnb_identity_tac_not_available_when_pebble_ready_then_status_is_active(self):
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_given_all_relations_created_when_pebble_ready_then_pebble_plan_is_applied(self):
        test_upf_hostname = "some.host.name"
        test_upf_port = "1234"
        test_management_url = "http://10.0.0.1:5000"
        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": test_upf_hostname, "upf_port": test_upf_port},
        )

        sdcore_management_relation_id = self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=sdcore_management_relation_id,
            app_or_unit=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
            key_values={"management_url": test_management_url},
        )

        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb", "tac": "1234"},
        )

        expected_plan = {
            "services": {
                "sdcore-nms": {
                    "startup": "enabled",
                    "override": "replace",
                    "command": "/bin/bash -c 'cd /app && npm run start'",
                    "environment": {
                        "UPF_CONFIG_PATH": TEST_UPF_CONFIG_PATH,
                        "GNB_CONFIG_PATH": TEST_GNB_CONFIG_PATH,
                        "WEBUI_ENDPOINT": test_management_url,
                    },
                }
            }
        }
        self.harness.container_pebble_ready("nms")
        updated_plan = self.harness.get_container_pebble_plan("nms").to_dict()

        self.assertEqual(expected_plan, updated_plan)

    def test_given_required_relations_created_without_fiveg_n4_relation_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self,
    ):
        test_management_url = "http://10.0.0.1:5000"

        sdcore_management_relation_id = self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=sdcore_management_relation_id,
            app_or_unit=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
            key_values={"management_url": test_management_url},
        )

        expected_plan = {
            "services": {
                "sdcore-nms": {
                    "startup": "enabled",
                    "override": "replace",
                    "command": "/bin/bash -c 'cd /app && npm run start'",
                    "environment": {
                        "UPF_CONFIG_PATH": TEST_UPF_CONFIG_PATH,
                        "GNB_CONFIG_PATH": TEST_GNB_CONFIG_PATH,
                        "WEBUI_ENDPOINT": test_management_url,
                    },
                }
            }
        }
        self.harness.container_pebble_ready("nms")
        updated_plan = self.harness.get_container_pebble_plan("nms").to_dict()

        self.assertEqual(expected_plan, updated_plan)

    def test_given_environment_information_available_all_relations_created_when_pebble_ready_then_status_is_active(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": "some.host.name", "upf_port": "1234"},
        )
        sdcore_management_relation_id = self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=sdcore_management_relation_id,
            app_or_unit=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
            key_values={"management_url": "http://10.0.0.1:5000"},
        )
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb", "tac": "1234"},
        )

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    def test_given_n4_information_available_when_pebble_ready_then_upf_config_is_written_in_file(  # noqa: E501
        self,
    ):
        expected_upf_config = [{"hostname": "some.host.name", "port": "1234"}]
        self.harness.set_can_connect(container="nms", val=True)
        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": "some.host.name", "upf_port": "1234"},
        )

        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        self.assertEqual(file_content, expected_upf_config)

    def test_given_n4_information_without_port_when_pebble_ready_then_upf_config_is_not_added(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": "some.host.name"},
        )

        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        expected_upf_config = []
        self.assertEqual(file_content, expected_upf_config)

    def test_given_n4_information_without_hostname_when_pebble_ready_then_upf_config_is_not_added(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_port": "1234"},
        )

        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        expected_upf_config = []
        self.assertEqual(file_content, expected_upf_config)

    def test_given_gnb_identity_information_available_when_pebble_ready_then_gnb_config_is_written_in_file(  # noqa: E501
        self,
    ):
        expected_gnb_config = [{"name": "some.gnb", "tac": "1234"}]
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb", "tac": "1234"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_gnb_identity_information_without_tac_when_pebble_ready_then_gnb_config_is_not_added(  # noqa: E501
        self,
    ):
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        expected_gnb_config = []
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_gnb_identity_information_without_gnb_name_when_pebble_ready_then_gnb_config_is_not_added(  # noqa: E501
        self,
    ):
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"tac": "1234"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        expected_gnb_config = []
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_gnb_config_already_exists_when_pebble_ready_then_gnb_config_is_not_duplicated_in_file(  # noqa: E501
        self,
    ):
        expected_gnb_config = [{"name": "some.gnb", "tac": "1234"}]
        root = self.harness.get_filesystem_root("nms")
        (root / TEST_GNB_STORAGE).write_text(json.dumps(expected_gnb_config))

        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb", "tac": "1234"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_upf_config_already_exists_when_pebble_ready_then_upf_config_is_not_duplicated_in_file(  # noqa: E501
        self,
    ):
        expected_upf_config = [{"hostname": "some.host.name", "port": "1234"}]
        root = self.harness.get_filesystem_root("nms")
        (root / TEST_UPF_STORAGE).write_text(json.dumps(expected_upf_config))

        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": "some.host.name", "upf_port": "1234"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        self.assertEqual(file_content, expected_upf_config)

    def test_given_two_n4_relations_when_pebble_ready_then_upf_config_file_contains_two_upfs(self):
        upf_config_1 = {"hostname": "some.host.name", "port": "1234"}
        upf_config2 = {"hostname": "some.other.host.name", "port": "4567"}
        expected_upf_config = [upf_config_1, upf_config2]

        fiveg_n4_relation_1_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_1_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": "some.host.name", "upf_port": "1234"},
        )
        fiveg_n4_relation_2_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_2_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": "some.other.host.name", "upf_port": "4567"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        self.assertEqual(file_content, expected_upf_config)

    def test_given_two_gnb_identity_relations_when_pebble_ready_then_gnb_config_file_contains_two_gnbs(  # noqa: E501
        self,
    ):
        gnb_config_1 = {"name": "some.gnb.name", "tac": "1234"}
        gnb_config_2 = {"name": "some.other.gnb.name", "tac": "4567"}
        expected_gnb_config = [gnb_config_1, gnb_config_2]

        gnb_identity_relation_1_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_1_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb.name", "tac": "1234"},
        )

        gnb_identity_relation_2_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_2_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.other.gnb.name", "tac": "4567"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        self.assertCountEqual(file_content, expected_gnb_config)

    def test_given_n4_information_not_available_in_relation_data_when_pebble_ready_then_upf_config_file_contains_empty_list(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        expected_gnb_config = []
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_gnb_information_not_available_in_relation_data_when_pebble_ready_then_gnb_config_file_contains_empty_list(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        expected_gnb_config = []
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_no_gnb_identity_relation_when_pebble_ready_then_gnb_config_file_contains_empty_list(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        expected_gnb_config = []
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_no_n4_relation_when_pebble_ready_then_upf_config_file_contains_empty_list(self):
        self.harness.set_can_connect(container="nms", val=True)
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        expected_upf_config = []
        self.assertEqual(file_content, expected_upf_config)

    def test_given_upf_exists_when_n4_relation_does_not_exist_then_upf_config_is_removed_from_file(
        self,
    ):
        existing_upf_config = [{"hostname": "some.host.name", "port": "1234"}]
        root = self.harness.get_filesystem_root("nms")
        (root / TEST_UPF_STORAGE).write_text(json.dumps(existing_upf_config))

        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        expected_upf_config = []
        self.assertEqual(file_content, expected_upf_config)

    def test_given_gnb_config_exists_when_gnb_identity_relation_does_not_exist_then_gnb_config_is_removed_from_file(  # noqa: E501
        self,
    ):
        existing_gnb_config = [{"name": "some.gnb", "tac": "1234"}]
        root = self.harness.get_filesystem_root("nms")
        (root / TEST_GNB_STORAGE).write_text(json.dumps(existing_gnb_config))

        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        expected_gnb_config = []
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_gnb_config_contains_two_gnbs_when_relation_broken_then_gnb_config_file_contains_one_gnb(  # noqa: E501
        self,
    ):
        gnb_identity_relation_1_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_1_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb.name", "tac": "1234"},
        )

        gnb_identity_relation_2_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_2_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.other.gnb.name", "tac": "4567"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        self.harness.remove_relation(relation_id=gnb_identity_relation_1_id)
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_GNB_STORAGE).read_text())
        expected_gnb_config = [{"name": "some.other.gnb.name", "tac": "4567"}]
        self.assertEqual(file_content, expected_gnb_config)

    def test_given_upf_config_contains_two_upfs_when_relation_broken_then_upf_config_file_contains_one_upf(  # noqa: E501
        self,
    ):
        fiveg_n4_relation_1_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_1_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": "some.host.name", "upf_port": "1234"},
        )
        fiveg_n4_relation_2_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_2_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": "some.other.host.name", "upf_port": "4567"},
        )
        self._add_mandatory_integrations()
        self.harness.container_pebble_ready("nms")
        self.harness.remove_relation(relation_id=fiveg_n4_relation_2_id)
        root = self.harness.get_filesystem_root("nms")
        file_content = json.loads((root / TEST_UPF_STORAGE).read_text())
        expected_upf_config = [{"hostname": "some.host.name", "port": "1234"}]
        self.assertEqual(file_content, expected_upf_config)
