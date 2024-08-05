# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.


import pytest
from fixtures import (
    CONTAINER,
    FIVEG_N4_RELATION_NAME,
    GNB_IDENTITY_RELATION_NAME,
    REMOTE_APP_NAME,
    NMSUnitTestFixtures,
)
from webui import GnodeB, Upf
from unittest.mock import call

POD_IP = "1.2.3.4"
UPF_CONFIG_URL = "config/v1/inventory/upf"
GNB_CONFIG_URL = "config/v1/inventory/gnb"
WEBUI_ENDPOINT = f"{POD_IP}:5000"


class TestCharmWorkloadConfiguration(NMSUnitTestFixtures):

    @pytest.mark.parametrize(
        "relation_name,relation_data",
        [
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                {"tac": "1234"},
                id="missing_gnb_name_in_gNB_config",
            ),
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                {"gnb_name": "some.gnb"},
                id="missing_tac_in_gNB_config",
            ),
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                {"tac": "", "gnb_name": ""},
                id="gnb_name_and_tac_are_empty_strings_in_gNB_config",
            ),
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                {"gnb_name": "something", "some": "key"},
                id="invalid_key_in_gNB_config",
            ),
                        pytest.param(
                FIVEG_N4_RELATION_NAME,
                {"upf_hostname": "some.host.name"},
                id="missing_upf_port_in_UPF_config",
            ),
            pytest.param(
                FIVEG_N4_RELATION_NAME,
                {"upf_port": "1234"},
                id="missing_upf_hostname_in_UPF_config",
            ),
            pytest.param(
                FIVEG_N4_RELATION_NAME,
                {"upf_hostname": "", "upf_port": ""},
                id="upf_hostname_and_upf_port_are_empty_strings_in_UPF_config",
            ),
            pytest.param(
                FIVEG_N4_RELATION_NAME,
                {"some": "key"},
                id="invalid_key_in_UPF_config",
            ),
        ],
    )
    def test_given_incomplete_data_in_relation_when_pebble_ready_then_is_not_updated_in_webui_db(
        self, relation_name, relation_data, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=True)
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=relation_id,
            app_or_unit=REMOTE_APP_NAME,
            key_values=relation_data,
        )

        self.harness.container_pebble_ready(CONTAINER)

        self.mock_add_gnb.assert_not_called()
        self.mock_add_upf.assert_not_called()
        self.mock_delete_gnb.assert_not_called()
        self.mock_delete_upf.assert_not_called()
        

    def test_given_no_db_relations_when_pebble_ready_then_inventory_is_not_updated(self):
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        self.mock_add_gnb.assert_not_called()
        self.mock_delete_gnb.assert_not_called()
        self.mock_get_upfs.assert_not_called()
        self.mock_add_upf.assert_not_called()
        self.mock_delete_upf.assert_not_called()

    def test_given_db_relations_when_pebble_ready_then_upf_inventory_is_updated(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        expected_upf = Upf(hostname="some.host.name", port=1234)
        self.mock_add_upf.assert_called_once_with(expected_upf)

    def test_given_db_relations_when_pebble_ready_then_gnb_inventory_is_updated(
        self, auth_database_relation_id, common_database_relation_id
    ):
        gnb_name = "gnb-11"
        tac = "12333"
        self.mock_check_output.return_value = POD_IP.encode()
        self.harness.add_storage("config", attach=True)
        self.set_gnb_identity_relation_data({"gnb_name": gnb_name, "tac": tac})

        self.harness.container_pebble_ready(CONTAINER)

        expected_gnb = GnodeB(name=gnb_name, tac=int(tac))
        self.mock_add_gnb.assert_called_once_with(expected_gnb)

    def test_given_multiple_n4_relations_when_pebble_ready_then_upf_inventory_both_upfs_are_added(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_n4_relation_data({"upf_hostname": "my_host", "upf_port": "77"})

        self.harness.container_pebble_ready(CONTAINER)
        
        expected_upf1 = Upf(hostname="some.host.name", port=1234)
        expected_upf2 = Upf(hostname="my_host", port=77)
        self.mock_add_upf.assert_any_call(expected_upf1)
        self.mock_add_upf.assert_any_call(expected_upf2)

    def test_given_multiple_gnb_relations_when_pebble_ready_then_gnb_inventory_both_gnbs_are_added(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()
        self.harness.add_storage("config", attach=True)
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "my_gnb", "tac": "4567"})

        self.harness.container_pebble_ready(CONTAINER)
        
        expected_gnb1 = GnodeB(name="some.gnb.name", tac=1234)
        expected_gnb2 = GnodeB(name="my_gnb", tac=4567)
        self.mock_add_gnb.assert_any_call(expected_gnb1)
        self.mock_add_gnb.assert_any_call(expected_gnb2)

    def test_given_upf_exist_in_inventory_and_relation_matches_when_pebble_ready_then_upf_inventory_is_not_updated(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()        
        existing_upfs = [Upf(hostname="some.host.name", port=1234)]
        self.mock_get_upfs.return_value = existing_upfs
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        self.mock_get_upfs.assert_called()
        self.mock_add_upf.assert_not_called()

    def test_given_gnb_exist_in_inventory_and_relation_matches_when_pebble_ready_then_gnb_inventory_is_not_updated(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()       
        existing_gnbs = [GnodeB(name="some.gnb.name", tac=1234)]
        self.mock_get_gnbs.return_value = existing_gnbs
        self.harness.add_storage("config", attach=True)
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        self.mock_get_gnbs.assert_called()
        self.mock_add_gnb.assert_not_called()

    def test_given_no_upf_or_gnb_relation_or_db_when_pebble_ready_then_inventory_is_not_updated(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=True)

        self.harness.container_pebble_ready(CONTAINER)

        self.mock_add_gnb.assert_not_called()
        self.mock_delete_gnb.assert_not_called()
        self.mock_add_upf.assert_not_called()
        self.mock_delete_upf.assert_not_called()
        

    def test_given_upf_exists_in_inventory_and_new_upf_relation_is_added_when_pebble_ready_then_second_upf_is_added_to_inventory(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()
        self.harness.add_storage("config", attach=True)
        existing_upf = Upf(hostname="some.host.name", port=1234)
        self.mock_get_upfs.return_value = [existing_upf]
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_n4_relation_data({"upf_hostname": "my_host", "upf_port": "4567"})

        self.harness.container_pebble_ready(CONTAINER)
        
        expected_upf = existing_upf = Upf(hostname="my_host", port=4567)
        self.mock_add_upf.assert_any_call(expected_upf)
        unwanted_call = call(Upf(hostname="some.host.name", port=1234))
        assert unwanted_call not in self.mock_add_upf.call_args_list
        self.mock_delete_upf.assert_not_called()


    def test_given_gnb_exists_in_inventory_and_new_gnb_relation_is_added_when_pebble_ready_then_second_gnb_is_added_to_inventory(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()        
        existing_gnbs = [GnodeB(name="some.gnb.name", tac=1234)]
        self.mock_get_gnbs.return_value = existing_gnbs
        self.harness.add_storage("config", attach=True)
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "my_gnb", "tac": "4567"})

        self.harness.container_pebble_ready(CONTAINER)
        
        expected_gnb = GnodeB(name="my_gnb", tac=4567)
        self.mock_add_gnb.assert_any_call(expected_gnb)
        unwanted_call = call(GnodeB(name="some.gnb.name", tac=1234))
        assert unwanted_call not in self.mock_add_gnb.call_args_list
        self.mock_delete_gnb.assert_not_called()

    def test_given_two_n4_relations_when_n4_relation_broken_then_upf_is_removed_from_inventory(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()
        existing_upfs = [
            Upf(hostname="some.host.name", port=1234),
            Upf(hostname="some.host", port=22)
        ]
        self.mock_get_upfs.return_value = existing_upfs
        self.harness.add_storage("config", attach=True)
        fiveg_n4_relation_1_id = self.set_n4_relation_data(
            {"upf_hostname": "some.host.name", "upf_port": "1234"}
        )
        self.set_n4_relation_data({"upf_hostname": "some.host", "upf_port": "22"})
        self.harness.container_pebble_ready(CONTAINER)

        self.harness.remove_relation(fiveg_n4_relation_1_id)

        self.mock_delete_upf.assert_called_once_with("some.host.name")
        unwanted_call = call("some.host")
        assert unwanted_call not in self.mock_delete_upf.call_args_list
        self.mock_add_upf.assert_not_called()

    def test_given_two_gnb_identity_relations_when_relation_broken_then_gnb_is_removed_from_inventory(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.mock_check_output.return_value = POD_IP.encode()
        existing_gnbs = [
            GnodeB(name="some.gnb.name", tac=1234),
            GnodeB(name="gnb.name", tac=333)
        ]
        self.mock_get_gnbs.return_value = existing_gnbs
        self.harness.add_storage("config", attach=True)
        gnb_identity_relation_1_id = self.set_gnb_identity_relation_data(
            {"gnb_name": "some.gnb.name", "tac": "1234"}
        )
        self.set_gnb_identity_relation_data({"gnb_name": "gnb.name", "tac": "333"})
        self.harness.container_pebble_ready(CONTAINER)

        self.harness.remove_relation(gnb_identity_relation_1_id)

        self.mock_delete_gnb.assert_called_once_with("some.gnb.name")
        unwanted_call = call("gnb.name")
        assert unwanted_call not in self.mock_delete_gnb.call_args_list
        self.mock_add_gnb.assert_not_called()

