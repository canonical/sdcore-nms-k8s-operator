# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import patch

from ops import testing
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from charm import SDCoreNMSOperatorCharm

FIVEG_N4_RELATION_NAME = "fiveg_n4"
TEST_FIVEG_N4_PROVIDER_APP_NAME = "fiveg_n4_provider_app"


class TestCharm(unittest.TestCase):
    @patch(
        "charm.KubernetesServicePatch",
        lambda charm, ports: None,
    )
    def setUp(self):
        self.harness = testing.Harness(SDCoreNMSOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_given_cant_connect_to_container_when_config_changed_then_status_is_waiting(self):
        self.harness.set_can_connect(container="nms", val=False)

        self.harness.update_config(
            key_values={"webui-endpoint": "banana"}
        )

        self.assertEqual(
            self.harness.model.unit.status, WaitingStatus("Waiting for container to be ready")
        )

    def test_given_fiveg_n4_relation_not_created_when_pebble_ready_then_status_is_blocked(self):
        self.harness.container_pebble_ready(container_name="nms")

        self.assertEqual(
            self.harness.model.unit.status,
            BlockedStatus(f"Waiting for `{FIVEG_N4_RELATION_NAME}` relation to be created")
        )

    def test_given_fiveg_n4_relation_not_created_when_config_changed_then_status_is_blocked(self):
        self.harness.set_can_connect(container="nms", val=True)

        self.harness.update_config(
            key_values={"webui-endpoint": "banana"}
        )

        self.assertEqual(
            self.harness.model.unit.status,
            BlockedStatus(f"Waiting for `{FIVEG_N4_RELATION_NAME}` relation to be created")
        )

    @patch("ops.model.Container.exists")
    def test_given_config_not_valid_when_config_changed_then_status_is_waiting(self, patch_exists):
        patch_exists.return_value = True
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )

        self.harness.update_config(key_values={"webui-endpoint": ""})

        self.assertEqual(
            self.harness.model.unit.status,
            BlockedStatus("Invalid `webui-endpoint` config value"),
        )

    def test_given_config_is_valid_and_fiveg_n4_relation_is_created_when_config_changed_then_pebble_plan_is_applied(  # noqa: E501
        self,
    ):
        test_upf_hostname = "some.host.name"
        test_upf_port = "1234"
        self.harness.set_can_connect(container="nms", val=True)
        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values={"upf_hostname": test_upf_hostname, "upf_port": test_upf_port}
        )

        self.harness.update_config(
            key_values={"webui-endpoint": "banana"}
        )

        expected_plan = {
            "services": {
                "sdcore-nms": {
                    "startup": "enabled",
                    "override": "replace",
                    "command": "/bin/bash -c 'cd /app && npm run start'",
                    "environment": {
                        "UPF_HOSTNAME": test_upf_hostname,
                        "UPF_PORT": int(test_upf_port),
                        "WEBUI_ENDPOINT": "banana",
                    },
                }
            }
        }
        updated_plan = self.harness.get_container_pebble_plan("nms").to_dict()

        self.assertEqual(expected_plan, updated_plan)

    def test_given_config_is_valid_and_fiveg_n4_relation_is_created_when_config_changed_then_status_is_active(  # noqa: E501
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
            key_values={"upf_hostname": "some.host.name", "upf_port": "1234"}
        )

        self.harness.update_config({"webui-endpoint": "banana"})

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())
