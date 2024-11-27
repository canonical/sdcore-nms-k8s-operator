# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
from unittest.mock import patch

import pytest
import scenario

from tests.unit.lib.charms.sdcore_nms_k8s.v0.dummy_fiveg_core_gnb_requirer_charm.src.dummy_requirer_charm import (  # noqa: E501
    DummyFivegCoreGnbRequirerCharm,
    GnbConfigAvailableEvent,
)

CU_NAME = "gnb001"


class TestFivegCoreGnbRequirer:
    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = scenario.Context(
            charm_type=DummyFivegCoreGnbRequirerCharm,
            meta={
                "name": "fiveg-core-gnb-requirer",
                "requires": {"fiveg_core_gnb": {"interface": "fiveg_core_gnb"}},
            },
            actions={
                "publish-cu-name": {
                    "params": {
                        "relation-id": {
                            "description": "The relation ID of the relation",
                            "type": "string",
                        },
                        "cu_name": {
                            "type": "string"
                        }
                    }
                }
            },
        )

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        yield
        request.addfinalizer(self.tearDown)

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    def test_given_gnb_config_in_relation_data_when_publish_cu_name_then_cu_name_in_relation_databag(  # noqa: E501
        self,
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data={"tac": "1", "plmns": "[]"},
        )
        state_in = scenario.State(
            leader=True,
            relations={fiveg_core_gnb_relation},
        )
        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "cu_name": CU_NAME
        }

        state_out = self.ctx.run(self.ctx.on.action("publish-cu-name", params=params), state_in)
        assert (
                state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["cu_name"]
                == CU_NAME
        )

    def test_given_gnb_config_in_relation_data_when_relation_changed_then_event_is_emitted(
        self,
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data={"tac": "1", "plmns": "[]"},
        )

        state_in = scenario.State(
            relations={fiveg_core_gnb_relation},
        )

        self.ctx.run(self.ctx.on.relation_changed(fiveg_core_gnb_relation), state_in)

        assert len(self.ctx.emitted_events) == 2
        assert isinstance(self.ctx.emitted_events[1], GnbConfigAvailableEvent)

    def test_given_gnb_config_not_in_relation_data_when_relation_changed_then_event_not_is_emitted(  # noqa: E501
        self,
    ):
        sdcore_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data={"whatever": "content"},
        )

        state_in = scenario.State(
            relations={sdcore_relation},
        )

        self.ctx.run(self.ctx.on.relation_changed(sdcore_relation), state_in)

        assert len(self.ctx.emitted_events) == 1
