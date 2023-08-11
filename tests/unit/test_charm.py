# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from io import StringIO
from unittest.mock import Mock, patch

from ops import testing
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from charm import SDCoreGUIOperatorCharm


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
        self.harness = testing.Harness(SDCoreGUIOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def test_given_cant_connect_to_container_when_config_changed_then_status_is_waiting(
        self,
    ):
        self.harness.set_can_connect(container="gui", val=False)

        self.harness.update_config(
            key_values={"webui-endpoint": "banana", "upf-hostname": "pizza", "upf-port": 1234}
        )

        self.assertEqual(
            self.harness.model.unit.status, WaitingStatus("Waiting for container to be ready")
        )

    @patch("ops.model.Container.exists")
    def test_given_storage_not_attached_when_config_changed_then_status_is_waiting(
        self, patch_exists
    ):
        patch_exists.return_value = False
        self.harness.set_can_connect(container="gui", val=True)

        self.harness.update_config(
            key_values={"webui-endpoint": "banana", "upf-hostname": "pizza", "upf-port": 1234}
        )

        self.assertEqual(
            self.harness.model.unit.status, WaitingStatus("Waiting for the storage to be attached")
        )

    @patch("ops.model.Container.exists")
    def test_given_config_not_valid_when_config_changed_then_status_is_waiting(self, patch_exists):
        patch_exists.return_value = True
        self.harness.set_can_connect(container="gui", val=True)

        self.harness.update_config(key_values={"webui-endpoint": ""})

        self.assertEqual(self.harness.model.unit.status, BlockedStatus("Config is not valid"))

    @patch("ops.model.Container.push")
    @patch("ops.model.Container.pull")
    @patch("ops.model.Container.exists")
    def test_given_config_file_not_pushed_when_config_changed_then_config_file_is_pushed(
        self, patch_exists, patch_pull, patch_push
    ):
        patch_pull.return_value = StringIO("whatever initial content")
        patch_exists.return_value = True
        self.harness.set_can_connect(container="gui", val=True)

        self.harness.update_config(
            key_values={"webui-endpoint": "banana", "upf-hostname": "pizza", "upf-port": 1234}
        )

        with open("tests/unit/expected_config.ts") as expected_config_file:
            expected_content = expected_config_file.read()
            patch_push.assert_called_with(
                path="/etc/config/sdcoreConfig.ts",
                source=expected_content.strip(),
            )

    @patch("ops.model.Container.push", new=Mock)
    @patch("ops.model.Container.pull")
    @patch("ops.model.Container.exists")
    def test_given_can_connect_when_config_changed_then_pebble_plan_is_applied(
        self, patch_exists, patch_pull
    ):
        patch_pull.return_value = StringIO("whatever initial content")
        patch_exists.return_value = True
        self.harness.set_can_connect(container="gui", val=True)

        self.harness.update_config({"webui-endpoint": "banana"})

        expected_plan = {
            "services": {
                "gui": {
                    "startup": "enabled",
                    "override": "replace",
                    "command": "/bin/bash -c 'cd /client/standalone && node server.js'",
                }
            }
        }
        updated_plan = self.harness.get_container_pebble_plan("gui").to_dict()
        self.assertEqual(expected_plan, updated_plan)

    @patch("ops.model.Container.push", new=Mock)
    @patch("ops.model.Container.pull")
    @patch("ops.model.Container.exists")
    def test_given_can_connect_when_config_changed_then_status_is_active(
        self, patch_exists, patch_pull
    ):
        patch_pull.return_value = StringIO("whatever initial content")
        patch_exists.return_value = True
        self.harness.set_can_connect(container="gui", val=True)

        self.harness.update_config({"webui-endpoint": "banana"})

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())
