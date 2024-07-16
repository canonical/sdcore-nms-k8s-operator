# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm the service."""

from ops.charm import CharmBase, RelationJoinedEvent
from ops.main import main

from lib.charms.sdcore_nms_k8s.v0.sdcore_config import SdcoreConfigProvides


class DummySdcoreConfigProviderCharm(CharmBase):
    """Charm the service."""

    WEBUI_URL = "sdcore-webui-k8s:9876"

    def __init__(self, *args):
        super().__init__(*args)
        self.webui_url_provider = SdcoreConfigProvides(self, "sdcore_config")
        self.framework.observe(
            self.on.sdcore_config_relation_joined, self._on_sdcore_config_relation_joined
        )

    def _on_sdcore_config_relation_joined(self, event: RelationJoinedEvent):
        relation_id = event.relation.id
        self.webui_url_provider.set_webui_url(
            webui_url=self.WEBUI_URL,
            relation_id=relation_id,
        )


if __name__ == "__main__":
    main(DummySdcoreConfigProviderCharm)
