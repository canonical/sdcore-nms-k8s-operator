# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json

import ops

from lib.charms.sdcore_nms_k8s.v0.fiveg_core_gnb import (
    FivegCoreGnbProviderAppData,
    FivegCoreGnbRequires,
    PLMNConfig,
)


class DummyFivegCoreGnbRequirerCharm(ops.CharmBase):
    """Mock requirer charm to test fiveg_core_gnb library."""

    def __init__(self, framework):
        super().__init__(framework)
        self.fiveg_core_gnb_requirer = FivegCoreGnbRequires(self, "fiveg_core_gnb")
        framework.observe(self.on.publish_gnb_name_action, self._on_publish_gnb_name)
        framework.observe(self.on.get_gnb_config_action, self._on_get_gnb_config_action)
        framework.observe(
            self.on.get_gnb_config_invalid_action,
            self._on_get_gnb_config_action_invalid
        )

    def _on_publish_gnb_name(self, event: ops.ActionEvent):
        relation_id = event.params.get("relation-id")
        gnb_name = event.params.get("gnb-name", "")
        self.fiveg_core_gnb_requirer.publish_gnb_information(
            relation_id=int(relation_id) if relation_id else None,
            gnb_name=gnb_name,
        )

    def _on_get_gnb_config_action(self, event: ops.ActionEvent):
        tac = event.params.get("tac", "")
        plmns = event.params.get("plmns", "")
        validated_data = {
            "tac": int(tac),
            "plmns": [PLMNConfig(**data) for data in json.loads(plmns)],
        }
        provider_app_data = FivegCoreGnbProviderAppData(**validated_data)

        assert provider_app_data.tac == self.fiveg_core_gnb_requirer.tac
        assert provider_app_data.plmns == self.fiveg_core_gnb_requirer.plmns

    def _on_get_gnb_config_action_invalid(self, event: ops.ActionEvent):
        assert self.fiveg_core_gnb_requirer.tac is None
        assert self.fiveg_core_gnb_requirer.plmns is None


if __name__ == "__main__":
    ops.main(DummyFivegCoreGnbRequirerCharm)  # type: ignore
