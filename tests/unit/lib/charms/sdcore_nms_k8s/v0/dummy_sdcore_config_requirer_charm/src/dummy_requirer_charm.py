# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm the service."""

import logging

from ops.charm import CharmBase
from ops.main import main

from lib.charms.sdcore_nms_k8s.v0.sdcore_config import (
    SdcoreConfigRequires,
    WebuiBroken,
    WebuiUrlAvailable,
)

logger = logging.getLogger(__name__)


class DummySdcoreConfigRequirerCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.webui_requirer = SdcoreConfigRequires(self, "sdcore_config")
        self.framework.observe(
            self.webui_requirer.on.webui_url_available, self._on_webui_url_available
        )
        self.framework.observe(self.webui_requirer.on.webui_broken, self._on_webui_broken)

    def _on_webui_url_available(self, event: WebuiUrlAvailable):
        logging.info(f"Webui URL from the event: {event.webui_url}")
        logging.info(f"Webui URL from the property: {self.webui_requirer.webui_url}")

    def _on_webui_broken(self, event: WebuiBroken) -> None:
        logging.info(f"Received {event}")


if __name__ == "__main__":
    main(DummySdcoreConfigRequirerCharm)
