# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm the service."""

from ops.charm import ActionEvent, CharmBase
from ops.main import main

from lib.charms.sdcore_nms_k8s.v0.sdcore_config import (
    SdcoreConfigRequires,
)


class DummySdcoreConfigRequirerCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.webui_requirer = SdcoreConfigRequires(self, "sdcore_config")
        self.framework.observe(self.on.get_webui_url_action, self._on_get_webui_url_action)

    def _on_get_webui_url_action(self, event: ActionEvent):
        event.set_results({"webui-url": self.webui_requirer.webui_url})


if __name__ == "__main__":
    main(DummySdcoreConfigRequirerCharm)
