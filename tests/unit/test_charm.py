# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import unittest
from io import StringIO
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


class TestCharm(unittest.TestCase):
    @patch(
        "charm.KubernetesServicePatch",
        lambda charm, ports: None,
    )
    def setUp(self):
        self.harness = testing.Harness(SDCoreNMSOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

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

    @patch("ops.model.Container.push")
    def test_given_n4_information_not_available_when_pebble_ready_then_status_is_active(
        self,
        _,
    ):
        sdcore_management_relation_id = self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=sdcore_management_relation_id,
            app_or_unit=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
            key_values={"management_url": "http://10.0.0.1:5000"},
        )

        self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )

        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    @patch("ops.model.Container.push")
    def test_given_gnb_identity_information_not_available_when_pebble_ready_then_status_is_active(
        self,
        _,
    ):
        sdcore_management_relation_id = self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=sdcore_management_relation_id,
            app_or_unit=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
            key_values={"management_url": "http://10.0.0.1:5000"},
        )

        self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )

        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    @patch("ops.model.Container.push")
    def test_given_gnb_identity_gnb_name_not_available_when_pebble_ready_then_status_is_active(
        self,
        _,
    ):
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
            key_values={"tac": "1234"},
        )

        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    @patch("ops.model.Container.push")
    def test_given_gnb_identity_tac_not_available_when_pebble_ready_then_status_is_active(
        self,
        _,
    ):
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
            key_values={"gnb_name": "some.gnb"},
        )

        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    @patch("ops.model.Container.push")
    def test_given_gnb_identity_information_not_available_in_one_relation_when_pebble_ready_then_status_is_active(  # noqa: E501
        self,
        _,
    ):
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

        second_gnb_identity_app = "some_app"
        self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=second_gnb_identity_app,
        )

        self.harness.container_pebble_ready("nms")
        self.assertEqual(self.harness.model.unit.status, ActiveStatus())

    @patch("ops.model.Container.push")
    def test_given_all_relations_created_when_pebble_ready_then_pebble_plan_is_applied(
        self,
        _,
    ):
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

    @patch("ops.model.Container.push")
    def test_given_required_relations_created_without_fiveg_n4_relation_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self,
        _,
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

    @patch("ops.model.Container.push")
    def test_given_environment_information_available_all_relations_created_when_pebble_ready_then_status_is_active(  # noqa: E501
        self,
        _,
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

    @patch("ops.model.Container.push")
    def test_given_n4_information_available_when_pebble_ready_then_upf_config_generated_and_pushed(  # noqa: E501
        self,
        patch_push,
    ):
        expected_upf_config = [
            {
                "hostname": "some.host.name",
                "port": "1234",
            },
            {
                "hostname": "some.other.host.name",
                "port": "4567",
            },
        ]
        self.harness.set_can_connect(container="nms", val=True)
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
        patch_push.assert_called_with(
            path=TEST_UPF_CONFIG_PATH, source=json.dumps(expected_upf_config)
        )

    @patch("ops.model.Container.push")
    def test_given_gnb_identity_information_available_when_pebble_ready_then_gnb_config_generated_and_pushed(  # noqa: E501
        self,
        patch_push,
    ):
        expected_gnb_config = [
            {
                "name": "some.gnb",
                "tac": "1234",
            }
        ]
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb", "tac": "1234"},
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
        self.harness.container_pebble_ready("nms")
        patch_push.assert_called_with(
            path=TEST_GNB_CONFIG_PATH, source=json.dumps(expected_gnb_config)
        )

    @patch("ops.model.Container.push")
    @patch("ops.model.Container.exists")
    @patch("ops.model.Container.pull")
    def test_given_gnb_config_already_pushed_and_content_matches_when_pebble_ready_then_gnb_config_is_not_pushed(  # noqa: E501
        self,
        patch_pull,
        patch_exists,
        patch_push,
    ):
        expected_gnb_config = [
            {
                "name": "some.gnb",
                "tac": "1234",
            }
        ]
        patch_exists.return_value = True
        patch_pull.return_value = StringIO(json.dumps(expected_gnb_config))

        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values={"gnb_name": "some.gnb", "tac": "1234"},
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
        self.harness.container_pebble_ready("nms")
        patch_push.assert_not_called()

    @patch("ops.model.Container.push")
    @patch("ops.model.Container.exists")
    @patch("ops.model.Container.pull")
    def test_given_upf_config_already_pushed_and_content_matches_when_pebble_ready_then_upf_config_is_not_pushed(  # noqa: E501
        self,
        patch_pull,
        patch_exists,
        patch_push,
    ):
        expected_upf_config = [
            {
                "hostname": "some.host.name",
                "port": "1234",
            }
        ]
        patch_exists.return_value = True
        patch_pull.return_value = StringIO(json.dumps(expected_upf_config))

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
        self.harness.container_pebble_ready("nms")
        patch_push.assert_not_called()

    @patch("ops.model.Container.push")
    @patch("ops.model.Container.exists")
    @patch("ops.model.Container.pull")
    def test_given_upf_config_already_pushed_and_content_changes_when_pebble_ready_then_upf_config_is_pushed(  # noqa: E501
        self,
        patch_pull,
        patch_exists,
        patch_push,
    ):
        existing_upf_config = [
            {
                "hostname": "some.host.name",
                "port": "1234",
            }
        ]
        expected_upf_config = [
            {
                "hostname": "some.host.name",
                "port": "1234",
            },
            {
                "hostname": "some.other.host.name",
                "port": "4567",
            },
        ]
        patch_exists.return_value = True
        patch_pull.return_value = StringIO(json.dumps(existing_upf_config))

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
        patch_push.assert_called_with(
            path=TEST_UPF_CONFIG_PATH, source=json.dumps(expected_upf_config)
        )

    @patch("ops.model.Container.push")
    @patch("ops.model.Container.exists")
    @patch("ops.model.Container.pull")
    def test_given_gnb_config_already_pushed_and_content_changes_when_pebble_ready_then_gnb_config_is_pushed(  # noqa: E501
        self,
        patch_pull,
        patch_exists,
        patch_push,
    ):
        existing_gnb_config = [
            {
                "name": "some.gnb.name",
                "tac": "1234",
            }
        ]
        expected_gnb_config = [
            {
                "name": "some.gnb.name",
                "tac": "1234",
            },
            {
                "name": "some.other.gnb.name",
                "tac": "4567",
            },
        ]
        patch_exists.return_value = True
        patch_pull.return_value = StringIO(json.dumps(existing_gnb_config))

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
        patch_push.assert_called_with(
            path=TEST_GNB_CONFIG_PATH, source=json.dumps(expected_gnb_config)
        )

    @patch("ops.model.Container.push")
    def test_given_n4_information_not_available_in_relation_data_when_pebble_ready_then_upf_config_not_pushed(  # noqa: E501
        self,
        patch_push,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
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
        self.harness.container_pebble_ready("nms")
        patch_push.assert_not_called()

    @patch("ops.model.Container.push")
    def test_given_gnb_information_not_available_in_relation_data_when_pebble_ready_then_gnb_config_not_pushed(  # noqa: E501
        self,
        patch_push,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
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
        self.harness.container_pebble_ready("nms")
        patch_push.assert_not_called()
