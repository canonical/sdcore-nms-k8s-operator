# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch

import pytest
import scenario

from tests.unit.lib.charms.sdcore_nms_k8s.v0.dummy_sdcore_config_requirer_charm.src.dummy_requirer_charm import (  # noqa: E501
    DummySdcoreConfigRequirerCharm,
    WebuiBroken,
    WebuiUrlAvailable,
)

WEBUI_URL = "sdcore-webui-k8s:9876"


class TestSdcoreConfigRequirer:
    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = scenario.Context(
            charm_type=DummySdcoreConfigRequirerCharm,
            meta={
                "name": "sdcore-config-requirer",
                "requires": {"sdcore_config": {"interface": "sdcore_config"}},
            },
            actions={"get-webui-url": {}},
        )

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        yield
        request.addfinalizer(self.tearDown)

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    def test_given_webui_information_in_relation_data_when_get_webui_url_then_webui_url_is_returned(  # noqa: E501
        self,
    ):
        sdcore_relation = scenario.Relation(
            endpoint="sdcore_config",
            interface="sdcore_config",
            remote_app_data={"webui_url": WEBUI_URL},
        )
        state_in = scenario.State(
            relations={sdcore_relation},
        )

        self.ctx.run(self.ctx.on.action("get-webui-url"), state_in)
        assert self.ctx.action_results == {"webui-url": WEBUI_URL}

    def test_given_webui_information_not_in_relation_data_when_get_webui_url_then_webui_is_not_returned(  # noqa: E501
        self,
    ):
        sdcore_relation = scenario.Relation(
            endpoint="sdcore_config",
            interface="sdcore_config",
        )
        state_in = scenario.State(
            relations={sdcore_relation},
        )

        self.ctx.run(self.ctx.on.action("get-webui-url"), state_in)
        assert self.ctx.action_results == {"webui-url": None}

    def test_given_webui_url_info_in_relation_data_when_relation_changed_then_event_is_emitted(
        self,
    ):
        sdcore_relation = scenario.Relation(
            endpoint="sdcore_config",
            interface="sdcore_config",
            remote_app_data={"webui_url": WEBUI_URL},
        )

        state_in = scenario.State(
            relations={sdcore_relation},
        )

        self.ctx.run(self.ctx.on.relation_changed(sdcore_relation), state_in)

        assert len(self.ctx.emitted_events) == 2
        assert isinstance(self.ctx.emitted_events[1], WebuiUrlAvailable)
        assert self.ctx.emitted_events[1].webui_url == WEBUI_URL

    def test_given_webui_url_info_not_in_relation_data_when_relation_changed_then_event_not_is_emitted(  # noqa: E501
        self,
    ):
        sdcore_relation = scenario.Relation(
            endpoint="sdcore_config",
            interface="sdcore_config",
            remote_app_data={"whatever": "content"},
        )

        state_in = scenario.State(
            relations={sdcore_relation},
        )

        self.ctx.run(self.ctx.on.relation_changed(sdcore_relation), state_in)

        assert len(self.ctx.emitted_events) == 1

    def test_given_webui_relation_when_relation_broken_then_webui_broken_event_emitted(
        self,
    ):
        sdcore_relation = scenario.Relation(
            endpoint="sdcore_config",
            interface="sdcore_config",
            remote_app_data={"webui_url": WEBUI_URL},
        )

        state_in = scenario.State(
            relations={sdcore_relation},
        )

        self.ctx.run(self.ctx.on.relation_broken(sdcore_relation), state_in)

        print(self.ctx.emitted_events)
        assert len(self.ctx.emitted_events) == 2
        assert isinstance(self.ctx.emitted_events[1], WebuiBroken)
