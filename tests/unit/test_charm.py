# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.


import logging
import unittest
from unittest.mock import Mock

import yaml
from ops import testing
from ops.model import BlockedStatus, WaitingStatus

from charm import INGRESS_RELATION_NAME, SDCoreGUIOperatorCharm

logger = logging.getLogger(__name__)


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.namespace = "whatever"
        self.metadata = self._get_metadata()
        self.container_name = list(self.metadata["containers"].keys())[0]
        self.harness = testing.Harness(SDCoreGUIOperatorCharm)
        self.harness.set_model_name(name=self.namespace)
        self.harness.set_leader(is_leader=True)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    def _get_metadata(self) -> dict:
        """Reads `metadata.yaml` and returns it as a dictionary.

        Returns:
            dics: metadata.yaml as a dictionary.
        """
        with open("metadata.yaml", "r") as f:
            data = yaml.safe_load(f)
        return data

    def _read_file(self, path: str) -> str:
        """Reads a file an returns as a string.

        Args:
            path (str): path to the file.

        Returns:
            str: content of the file.
        """
        with open(path, "r") as f:
            content = f.read()
        return content

    def _create_ingress_integration(self) -> None:
        """Create ingress integration.

        Return:
            int: relation id.
        """
        remote_app = "traefik-k8s"
        relation_id = self.harness.add_relation(
            relation_name=INGRESS_RELATION_NAME, remote_app=remote_app
        )
        self.harness.add_relation_unit(relation_id=relation_id, remote_unit=f"{remote_app}/0")
        return relation_id

    def test_given_container_cant_connect_when_configure_sdcore_gui_then_status_is_waiting(
        self,
    ):
        self.harness.set_can_connect(container=self.container_name, val=False)

        self.harness.charm._configure_sdcore_gui(event=Mock())

        self.assertEqual(
            self.harness.charm.unit.status, WaitingStatus("Waiting for container to be ready")
        )

    def test_given_storage_is_not_attached_when_configure_sdcore_gui_then_status_is_waiting(
        self,
    ):
        self.harness.set_can_connect(container=self.container_name, val=True)
        self.harness.charm._storage_is_attached = Mock(return_value=False)

        self.harness.charm._configure_sdcore_gui(event=Mock())

        self.assertEqual(
            self.harness.charm.unit.status, WaitingStatus("Waiting for the storage to be attached")
        )

    def test_given_ingress_integration_is_not_created_when_configure_sdcore_gui_then_status_is_blocked(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container=self.container_name, val=True)
        self.harness.charm._storage_is_attached = Mock(return_value=True)

        self.harness.charm._configure_sdcore_gui(event=Mock())

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Waiting for `ingress` relation to be created"),
        )
