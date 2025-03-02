# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
import json

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
TEST_GNB_NAME = "gnb001"


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
                        "tac": {
                            "type": "string",
                        },
                        "plmns": {
                            "type": "string",
                        },
                    },
                },
                "get-gnb-name": {
                    "params": {
                        "relation-id": {
                            "description": "The relation ID of the relation",
                            "type": "string",
                        },
                        "gnb-name": {
                            "type": "string",
                        },
                    }
                },
                "get-gnb-name-invalid": {"params": {}},
            },
        )

    def test_given_unit_is_leader_and_fiveg_core_gnb_relation_when_publish_gnb_config_valid_tac_then_data_is_in_application_databag(  # noqa: E501
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
            "plmns": json.dumps([plmn.asdict() for plmn in plmns]),
        }

        state_out = self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)
        assert state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["tac"] == str(
            TEST_TAC_VALID
        )
        rel_plmns = state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["plmns"]
        assert plmns == [PLMNConfig(**data) for data in json.loads(rel_plmns)]

    def test_given_unit_is_leader_and_fiveg_core_gnb_relation_when_publish_gnb_config_invalid_tac_then_exception_is_raised(  # noqa: E501
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
            "plmns": json.dumps([plmn.asdict() for plmn in plmns]),
        }

        with pytest.raises(Exception) as exc:
            self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)

        assert "Invalid gNB config" in str(exc.value)

    def test_given_unit_is_leader_and_fiveg_core_gnb_relation_when_publish_gnb_config_invalid_plmn_then_exception_is_raised(  # noqa: E501
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
            "plmns": "[]",
        }

        with pytest.raises(Exception) as exc:
            self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)

        assert "Invalid gNB config" in str(exc.value)

    def test_given_unit_is_leader_and_fiveg_core_gnb_relation_when_publish_gnb_config_plmn_no_sd_then_data_is_in_application_databag(  # noqa: E501
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
            "plmns": json.dumps([plmn.asdict() for plmn in plmns]),
        }

        state_out = self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)
        assert state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["tac"] == str(
            TEST_TAC_VALID
        )
        rel_plmns = state_out.get_relation(fiveg_core_gnb_relation.id).local_app_data["plmns"]
        assert plmns == [PLMNConfig(**data) for data in json.loads(rel_plmns)]

    def test_given_unit_is_leader_and_fiveg_core_gnb_relation_is_not_created_when_publish_gnb_config_then_runtime_error_is_raised(  # noqa: E501
        self,
    ):
        state_in = scenario.State(leader=True)
        plmns = [PLMNConfig(mcc=TEST_MCC, mnc=TEST_MNC, sst=TEST_SST, sd=TEST_SD)]
        params = {
            "tac": str(TEST_TAC_VALID),
            "plmns": json.dumps([plmn.asdict() for plmn in plmns]),
        }

        # TODO: It seems like this should use event.fail() rather than raising.
        with pytest.raises(Exception):
            self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)

    def test_given_unit_is_not_leader_and_fiveg_core_gnb_relation_when_publish_gnb_config_valid_tac_then_data_is_not_in_application_databag(  # noqa: E501
        self,
    ):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
        )
        state_in = scenario.State(
            leader=False,
            relations={fiveg_core_gnb_relation},
        )

        plmns = [PLMNConfig(mcc=TEST_MCC, mnc=TEST_MNC, sst=TEST_SST, sd=TEST_SD)]
        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "tac": str(TEST_TAC_VALID),
            "plmns": json.dumps([plmn.asdict() for plmn in plmns]),
        }

        # TODO: It seems like this should use event.fail() rather than raising.
        with pytest.raises(Exception) as e:
            self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)

        assert "Unit must be leader to set application relation data" in str(e.value)

    def test_given_fiveg_core_gnb_relation_does_not_exist_when_publish_gnb_config_then_exception_is_raised(  # noqa E501
        self,
    ):
        state_in = scenario.State(relations=[], leader=True)
        plmns = [PLMNConfig(mcc=TEST_MCC, mnc=TEST_MNC, sst=TEST_SST, sd=TEST_SD)]
        params = {
            "tac": str(TEST_TAC_VALID),
            "plmns": json.dumps([plmn.asdict() for plmn in plmns]),
        }

        with pytest.raises(Exception) as exc:
            self.ctx.run(self.ctx.on.action("publish-gnb-config", params=params), state_in)

        assert "Relation fiveg_core_gnb not created yet." in str(exc.value)

    def test_given_gnb_name_in_relation_data_when_get_gnb_name_then_gnb_name_is_returned(self):
        fiveg_core_gnb_relation = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data={"gnb-name": TEST_GNB_NAME},
        )
        params = {
            "relation-id": str(fiveg_core_gnb_relation.id),
            "gnb-name": TEST_GNB_NAME,
        }
        state_in = scenario.State(
            relations={fiveg_core_gnb_relation},
        )

        self.ctx.run(self.ctx.on.action("get-gnb-name", params=params), state_in)

    def test_given_fiveg_core_gnb_relation_does_not_exist_when_get_gnb_name_then_none_is_returned(
        self,
    ):  # noqa E501
        state_in = scenario.State(relations=[], leader=True)

        self.ctx.run(self.ctx.on.action("get-gnb-name-invalid"), state_in)

    def test_given_multiple_relations_when_get_gnb_name_then_correct_gnb_name_is_returned(self):
        test_gnb_name_rel_1 = "gnb001"
        test_gnb_name_rel_2 = "gnb002"
        fiveg_core_gnb_relation_1 = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data={"gnb-name": test_gnb_name_rel_1},
        )
        fiveg_core_gnb_relation_2 = scenario.Relation(
            endpoint="fiveg_core_gnb",
            interface="fiveg_core_gnb",
            remote_app_data={"gnb-name": test_gnb_name_rel_2},
        )
        params = {
            "relation-id": str(fiveg_core_gnb_relation_2.id),
            "gnb-name": test_gnb_name_rel_2,
        }
        state_in = scenario.State(
            relations={fiveg_core_gnb_relation_1, fiveg_core_gnb_relation_2},
        )

        self.ctx.run(self.ctx.on.action("get-gnb-name", params=params), state_in)
