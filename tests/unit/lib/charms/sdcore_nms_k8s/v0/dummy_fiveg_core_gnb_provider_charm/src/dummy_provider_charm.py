# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm the service."""
import json

import ops

from lib.charms.sdcore_nms_k8s.v0.fiveg_core_gnb import FivegCoreGnbProvides, PLMNConfig


class DummyFivegCoreGnbProviderCharm(ops.CharmBase):
    """Charm the service."""
    def __init__(self, framework):
        super().__init__(framework)
        self.fiveg_core_gnb_provider = FivegCoreGnbProvides(self, "fiveg_core_gnb")
        framework.observe(self.on.publish_gnb_config_action, self._on_publish_gnb_config_action)
        framework.observe(
            self.on.publish_gnb_config_wrong_data_action,
            self._on_publish_gnb_config_action_wrong_data,
        )

    def _on_publish_gnb_config_action(self, event: ops.ActionEvent):
        relation_id = event.params.get("relation-id")
        tac = event.params.get("tac")
        plmns = event.params.get("plmns")
        assert relation_id
        assert tac
        assert plmns
        self.fiveg_core_gnb_provider.publish_fiveg_core_gnb_information(
            relation_id=int(relation_id),
            tac=int(tac),
            plmns=[PLMNConfig(**data) for data in json.loads(plmns)],
        )

    def _on_publish_gnb_config_action_wrong_data(self, event: ops.ActionEvent):
        relation_id = event.params.get("relation-id")
        tac = event.params.get("tac")
        plmns = event.params.get("plmns")
        assert relation_id
        assert tac
        assert plmns
        self.fiveg_core_gnb_provider.publish_fiveg_core_gnb_information(
            relation_id=int(relation_id),
            tac=int(tac),
            plmns=plmns,
        )


if __name__ == "__main__":
    ops.main(DummyFivegCoreGnbProviderCharm)  # type: ignore
