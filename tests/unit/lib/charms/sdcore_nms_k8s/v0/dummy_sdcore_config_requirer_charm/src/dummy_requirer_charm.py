# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm the service."""

import logging

import ops

from lib.charms.sdcore_nms_k8s.v0.sdcore_config import (
    SdcoreConfigRequires,
    WebuiBroken,
    WebuiUrlAvailable,
)

logger = logging.getLogger(__name__)


class DummySdcoreConfigRequirerCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework):
        super().__init__(framework)
        self.webui_requirer = SdcoreConfigRequires(self, "sdcore_config")
        self.framework.observe(
            self.webui_requirer.on.webui_url_available, self._on_webui_url_available
        )
        framework.observe(self.webui_requirer.on.webui_broken, self._on_webui_broken)
        framework.observe(self.on.get_webui_url_action, self._on_get_webui_url_action)

    def _on_webui_url_available(self, event: WebuiUrlAvailable):
        logging.info(f"Webui URL from the event: {event.webui_url}")
        logging.info(f"Webui URL from the property: {self.webui_requirer.webui_url}")

    def _on_webui_broken(self, event: WebuiBroken) -> None:
        logging.info(f"Received {event}")

    def _on_get_webui_url_action(self, event: ops.ActionEvent):
        event.set_results({"webui-url": self.webui_requirer.webui_url})


if __name__ == "__main__":
    ops.main(DummySdcoreConfigRequirerCharm)  # type: ignore
