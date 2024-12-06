# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import pytest
import scenario

from tests.unit.lib.charms.sdcore_nms_k8s.v0.dummy_fiveg_core_gnb_requirer_charm.src.dummy_requirer_charm import (  # noqa: E501
    DummyFivegCoreGnbRequirerCharm,
)

GNB_NAME = "gnb001"


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
                "publish-gnb-name": {
                    "params": {
                        "relation-id": {
                            "description": "The relation ID of the relation",
                            "type": "string",
                        },
                        "gnb-name": {
                            "type": "string"
                        }
                    }
                },
                "get-gnb-config": {
                    "params": {
                        "tac": {
                            "type": "string",
                        },
                        "plmns": {
                            "type": "string",
                        },
                    }
                },
                "get-gnb-config-invalid": {"params": {}},
            },
        )

    def test_given_gnb_config_in_relation_data_when_publish_gnb_name_then_gnb_name_in_relation_databag(  # noqa: E501
        self,
    ):
        encoded_plmns = '[{"mcc": "001", "mnc": "01", "sst": 1, "sd": 1}]'
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data={"tac": "1", "plmns": encoded_plmns},
        )
        state_in = scenario.State(
            leader=True,
            relations={fiveg_core_gnb_relation},
        )
        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "gnb-name": GNB_NAME
        }

        state_out = self.ctx.run(self.ctx.on.action("publish-gnb-name", params=params), state_in)
        assert (
                state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["gnb-name"]
                == GNB_NAME
        )

    def test_given_gnb_config_in_relation_data_when_get_gnb_config_then_gnb_config_is_returned(  # noqa: E501
        self,
    ):
        encoded_plmns = '[{"mcc": "001", "mnc": "01", "sst": 1, "sd": 1}]'
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data={"tac": "1", "plmns": encoded_plmns},
        )
        params = {
            "tac": "1",
            "plmns": encoded_plmns,
        }
        state_in = scenario.State(
            relations={fiveg_core_gnb_relation},
        )

        self.ctx.run(self.ctx.on.action("get-gnb-config", params=params), state_in)

    def test_given_fiveg_core_gnb_relation_does_not_exist_when_publish_gnb_name_then_exception_is_raised(self):  # noqa E501
        state_in = scenario.State(relations=[], leader=True)
        params = {"gnb-name": GNB_NAME}

        with pytest.raises(Exception) as exc:
            self.ctx.run(self.ctx.on.action("publish-gnb-name", params=params), state_in)

        assert "Relation fiveg_core_gnb not created yet." in str(exc.value)

    @pytest.mark.parametrize(
        "remote_databag",
        [
            pytest.param(
                {
                    "tac": "3",
                    "plmns": "[]",
                },
                id="invalid_plmns",
            ),
            pytest.param(
                {
                    "tac": "16777216",
                    "plmns": '[{"mcc": "001", "mnc": "01", "sst": 1, "sd": 1}]',
                },
                id="invalid_tac",
            ),
        ],
    )
    def test_given_invalid_gnb_config_in_relation_data_when_get_gnb_config_then_none_is_returned(  # noqa: E501
        self, remote_databag
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data=remote_databag,
        )
        state_in = scenario.State(
            relations={fiveg_core_gnb_relation},
        )

        self.ctx.run(self.ctx.on.action("get-gnb-config-invalid"), state_in)
