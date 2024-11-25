# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
import json
from unittest.mock import patch

import pytest
import scenario

from tests.unit.lib.charms.sdcore_nms_k8s.v0.dummy_fiveg_core_gnb_provider_charm.src.dummy_provider_charm import (  # noqa: E501
    DummyFivegCoreGnbProviderCharm,
    PLMNConfig,
)

TEST_TAC_VALID = 1
TEST_TAC_INVALID = 0
TEST_MCC = "001"
TEST_MNC = "01"
TEST_SST = 1
TEST_SD_VALID = 2
TEST_SD_INVALID = "ssss"


class TestFivegCoreGnbProviderCharm:
    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = scenario.Context(
            charm_type=DummyFivegCoreGnbProviderCharm,
            meta={
                "name": "fiveg-core-gnb-provider",
                "provides": {
                    "fiveg_core_gnb": {
                        "interface": "fiveg_core_gnb",
                    }
                },
            },
            actions={
                "publish-gnb-config": {
                    "params": {
                        "relation-id": {
                            "description": "The relation ID of the relation to get the URL from",
                            "type": "string",
                        },
                        "tac": {
                            "type": "string",
                        },
                        "plmns": {
                            "type": "string",
                        },
                    },
                },
            },
        )

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        yield
        request.addfinalizer(self.tearDown)

    def tearDown(self) -> None:
        patch.stopall()

    @pytest.mark.parametrize("tac", [TEST_TAC_VALID, TEST_TAC_INVALID])
    def test_given_fiveg_core_gnb_relation_when_publish_gnb_config_then_data_is_in_application_databag(  # noqa: E501
        self, tac,
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
        )
        state_in = scenario.State(
            leader=True,
            relations={fiveg_core_gnb_relation},
        )

        plmns = [PLMNConfig(mcc=TEST_MCC, mnc=TEST_MNC, sst=TEST_SST, sd=TEST_SD_VALID)]
        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "tac": str(tac),
            "plmns": json.dumps([plmn.asdict() for plmn in plmns])
        }

        if tac == TEST_TAC_INVALID:
            with pytest.raises(Exception):
                self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)
        else:
            state_out = self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params),
                                     state_in)
            assert (
                state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["tac"]
                == str(tac)
            )
            rel_plmns = state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["plmns"]
            assert plmns == [PLMNConfig(**data) for data in json.loads(rel_plmns)]

    @pytest.mark.parametrize("sd", [TEST_SD_VALID, TEST_SD_INVALID])
    def test_given_fiveg_core_gnb_relation_when_publish_gnb_config_then_data_is_in_application_databag_plmns(  # noqa: E501
        self, sd,
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
        )
        state_in = scenario.State(
            leader=True,
            relations={fiveg_core_gnb_relation},
        )

        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "tac": str(TEST_TAC_VALID),
            "plmns": f'[{{"mcc": "001", "mnc": "01", "sst": 1, "sd": {sd}}}]'
        }
        if sd == TEST_SD_INVALID:
            with pytest.raises(Exception):
                self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)
        else:
            plmns = [PLMNConfig(mcc=TEST_MCC, mnc=TEST_MNC, sst=TEST_SST, sd=sd)]
            state_out = self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params),
                                     state_in)
            rel_plmns = state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["plmns"]
            assert plmns == [PLMNConfig(**data) for data in json.loads(rel_plmns)]
