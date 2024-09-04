# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


"""Charm the service."""

import ops

from lib.charms.sdcore_nms_k8s.v0.sdcore_config import SdcoreConfigProvides


class DummySdcoreConfigProviderCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, framework):
        super().__init__(framework)
        self.webui_url_provider = SdcoreConfigProvides(self, "sdcore_config")
        framework.observe(self.on.set_webui_url_action, self._on_set_webui_url_action)
        framework.observe(
            self.on.set_webui_url_in_all_relations_action,
            self._on_set_webui_url_in_all_relations_action,
        )

    def _on_set_webui_url_action(self, event: ops.ActionEvent):
        relation_id = event.params.get("relation-id", "")
        url = event.params.get("url", None)
        self.webui_url_provider.set_webui_url(
            webui_url=url if url else None,  # type: ignore
            relation_id=int(relation_id),
        )

    def _on_set_webui_url_in_all_relations_action(self, event: ops.ActionEvent):
        url = event.params.get("url", None)
        self.webui_url_provider.set_webui_url_in_all_relations(
            webui_url=url if url else None,  # type: ignore
        )


if __name__ == "__main__":
    ops.main(DummySdcoreConfigProviderCharm)  # type: ignore
