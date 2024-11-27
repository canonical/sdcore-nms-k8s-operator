# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm the service."""

import logging

import ops

from lib.charms.sdcore_nms_k8s.v0.fiveg_core_gnb import (
    FivegCoreGnbRequires,
    GnbConfigAvailableEvent,
)

logger = logging.getLogger(__name__)


class DummyFivegCoreGnbRequirerCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework):
        super().__init__(framework)
        self.fiveg_core_gnb_requirer = FivegCoreGnbRequires(self, "fiveg_core_gnb")
        self.framework.observe(
            self.fiveg_core_gnb_requirer.on.gnb_config_available, self._on_gnb_config_available
        )
        framework.observe(self.on.publish_cu_name_action, self._on_publish_cu_name)

    def _on_gnb_config_available(self, event: GnbConfigAvailableEvent):
        logging.info(f"TAC from the event: {event.tac}")

    def _on_publish_cu_name(self, event: ops.ActionEvent):
        relation_id = event.params.get("relation-id")
        cu_name = event.params.get("cu_name")
        assert relation_id
        assert cu_name
        self.fiveg_core_gnb_requirer.publish_gnb_information(
            relation_id=int(relation_id),
            cu_name=cu_name,
        )


if __name__ == "__main__":
    ops.main(DummyFivegCoreGnbRequirerCharm)  # type: ignore
