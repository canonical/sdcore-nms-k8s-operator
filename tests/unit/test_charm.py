# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import patch

from ops import testing
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from charm import SDCoreNMSOperatorCharm


def read_file(path: str) -> str:
    """Reads a file and returns as a string.

    Args:
        path (str): path to the file.

    Returns:
        str: content of the file.
    """
    with open(path, "r") as f:
        content = f.read()
    return content


class TestCharm(unittest.TestCase):
    @patch(
        "charm.KubernetesServicePatch",
        lambda charm, ports: None,
    )
    def setUp(self):
        self.harness = testing.Harness(SDCoreNMSOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_given_cant_connect_to_container_when_config_changed_then_status_is_waiting(
        self,
    ):
        self.harness.set_can_connect(container="nms", val=False)

        self.harness.update_config(
            key_values={"webui-endpoint": "banana", "upf-hostname": "pizza", "upf-port": 1234}
        )

        self.assertEqual(
            self.harness.model.unit.status, WaitingStatus("Waiting for container to be ready")
        )

    @patch("ops.model.Container.exists")
    def test_given_config_not_valid_when_config_changed_then_status_is_waiting(self, patch_exists):
        patch_exists.return_value = True
        self.harness.set_can_connect(container="nms", val=True)

        self.harness.update_config(key_values={"webui-endpoint": ""})

        self.assertEqual(self.harness.model.unit.status, BlockedStatus("Config is not valid"))

    def test_given_can_connect_when_config_changed_then_pebble_plan_is_applied(
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)

        self.harness.update_config(
            key_values={"webui-endpoint": "banana", "upf-hostname": "upf", "upf-port": 1234}
        )

        expected_plan = {
            "services": {
                "sdcore-nms": {
                    "startup": "enabled",
                    "override": "replace",
                    "command": "/bin/bash -c 'cd /app && npm run start'",
                    "environment": {
                        "UPF_HOSTNAME": "upf",
                        "UPF_PORT": 1234,
                        "WEBUI_ENDPOINT": "banana",
                    },
                }
            }
        }
        updated_plan = self.harness.get_container_pebble_plan("nms").to_dict()

        self.assertEqual(expected_plan, updated_plan)

    def test_given_can_connect_when_config_changed_then_status_is_active(
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)

        self.harness.update_config({"webui-endpoint": "banana"})

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())
