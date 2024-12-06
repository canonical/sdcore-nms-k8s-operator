# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json

import ops

from lib.charms.sdcore_nms_k8s.v0.fiveg_core_gnb import (
    FivegCoreGnbProvides,
    FivegCoreGnbRequirerAppData,
    PLMNConfig,
)


class DummyFivegCoreGnbProviderCharm(ops.CharmBase):
    """Mock provider charm to test fiveg_core_gnb library."""

    def __init__(self, framework):
        super().__init__(framework)
        self.fiveg_core_gnb_provider = FivegCoreGnbProvides(self, "fiveg_core_gnb")
        framework.observe(self.on.publish_gnb_config_action, self._on_publish_gnb_config_action)
        framework.observe(
            self.on.publish_gnb_config_wrong_data_action,
            self._on_publish_gnb_config_action_wrong_data,
        )
        framework.observe(self.on.get_gnb_name_action, self._on_get_gnb_name_action)
        framework.observe(
            self.on.get_gnb_name_invalid_action,
            self._on_get_gnb_name_action_invalid
        )

    def _on_publish_gnb_config_action(self, event: ops.ActionEvent):
        relation_id = event.params.get("relation-id", "")
        tac = event.params.get("tac", "")
        plmns = event.params.get("plmns", "")
        self.fiveg_core_gnb_provider.publish_gnb_config_information(
            relation_id=int(relation_id) if relation_id else None,
            tac=int(tac),
            plmns=[PLMNConfig(**data) for data in json.loads(plmns)],
        )

    def _on_publish_gnb_config_action_wrong_data(self, event: ops.ActionEvent):
        relation_id = event.params.get("relation-id", "")
        tac = event.params.get("tac")
        plmns = event.params.get("plmns")
        assert relation_id
        assert tac
        assert plmns
        self.fiveg_core_gnb_provider.publish_gnb_config_information(
            relation_id=int(relation_id),
            tac=int(tac),
            plmns=plmns,
        )

    def _on_get_gnb_name_action(self, event: ops.ActionEvent):
        relation_id = event.params.get("relation-id", "")
        gnb_name = event.params.get("gnb-name", "")
        validated_data = {
            "gnb-name": gnb_name,
        }
        requirer_app_data = FivegCoreGnbRequirerAppData(**validated_data)

        assert (
                requirer_app_data.gnb_name ==
                self.fiveg_core_gnb_provider.get_gnb_name(int(relation_id))
        )

    def _on_get_gnb_name_action_invalid(self, event: ops.ActionEvent):
        assert self.fiveg_core_gnb_provider.get_gnb_name(None) is None


if __name__ == "__main__":
    ops.main(DummyFivegCoreGnbProviderCharm)  # type: ignore
