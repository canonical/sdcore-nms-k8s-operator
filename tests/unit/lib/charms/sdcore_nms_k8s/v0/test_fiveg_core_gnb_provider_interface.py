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
TEST_SD = 2


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
                            "description": "The relation ID of the relation",
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
                "publish-gnb-config-wrong-data": {
                    "params": {
                        "relation-id": {
                            "description": "The relation ID of the relation",
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

    def test_given_fiveg_core_gnb_relation_when_publish_gnb_config_valid_tac_then_data_is_in_application_databag(  # noqa: E501
        self,
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
        )
        state_in = scenario.State(
            leader=True,
            relations={fiveg_core_gnb_relation},
        )

        plmns = [PLMNConfig(mcc=TEST_MCC, mnc=TEST_MNC, sst=TEST_SST, sd=TEST_SD)]
        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "tac": str(TEST_TAC_VALID),
            "plmns": json.dumps([plmn.asdict() for plmn in plmns])
        }

        state_out = self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params),
                                 state_in)
        assert (
            state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["tac"]
            == str(TEST_TAC_VALID)
        )
        rel_plmns = state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["plmns"]
        assert plmns == [PLMNConfig(**data) for data in json.loads(rel_plmns)]

    def test_given_fiveg_core_gnb_relation_when_publish_gnb_config_invalid_tac_then_exception_is_raised(  # noqa: E501
        self,
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
        )
        state_in = scenario.State(
            leader=True,
            relations={fiveg_core_gnb_relation},
        )

        plmns = [PLMNConfig(mcc=TEST_MCC, mnc=TEST_MNC, sst=TEST_SST, sd=TEST_SD)]
        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "tac": str(TEST_TAC_INVALID),
            "plmns": json.dumps([plmn.asdict() for plmn in plmns])
        }

        with pytest.raises(Exception):
            self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)

    def test_given_fiveg_core_gnb_relation_when_publish_gnb_config_invalid_plmn_then_exception_is_raised(  # noqa: E501
        self,
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
            "plmns": "dummy-string"
        }

        with pytest.raises(Exception):
            self.ctx.run(
                self.ctx.on.action("publish-gnb-config-wrong-data", params=params),
                state_in
            )

    def test_given_fiveg_core_gnb_relation_when_publish_gnb_config_plmn_no_sd_then_data_is_in_application_databag(  # noqa: E501
        self,
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
        )
        state_in = scenario.State(
            leader=True,
            relations={fiveg_core_gnb_relation},
        )

        plmns = [PLMNConfig(mcc=TEST_MCC, mnc=TEST_MNC, sst=TEST_SST)]
        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "tac": str(TEST_TAC_VALID),
            "plmns": json.dumps([plmn.asdict() for plmn in plmns])
        }

        state_out = self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params),
                                 state_in)
        assert (
                state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["tac"]
                == str(TEST_TAC_VALID)
        )
        rel_plmns = state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["plmns"]
        assert plmns == [PLMNConfig(**data) for data in json.loads(rel_plmns)]
