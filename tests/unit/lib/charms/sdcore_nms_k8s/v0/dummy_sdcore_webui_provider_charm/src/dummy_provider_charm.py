# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm the service."""

from ops.charm import CharmBase, RelationJoinedEvent
from ops.main import main

from lib.charms.sdcore_nms_k8s.v0.sdcore_webui import SdcoreWebuiProvides


class DummySdcoreWebuiProviderCharm(CharmBase):
    """Charm the service."""

    WEBUI_URL = "sdcore-webui-k8s:9876"

    def __init__(self, *args):
        super().__init__(*args)
        self.webui_url_provider = SdcoreWebuiProvides(self, "sdcore-webui")
        self.framework.observe(
            self.on.sdcore_webui_relation_joined, self._on_sdcore_webui_relation_joined
        )

    def _on_sdcore_webui_relation_joined(self, event: RelationJoinedEvent):
        relation_id = event.relation.id
        self.webui_url_provider.set_webui_url(
            webui_url=self.WEBUI_URL,
            relation_id=relation_id,
        )


if __name__ == "__main__":
    main(DummySdcoreWebuiProviderCharm)
