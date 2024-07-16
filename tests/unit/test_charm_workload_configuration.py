# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import os
from unittest.mock import call

import pytest
from fixtures import NMSUnitTestFixtures
from ops.model import ModelError

CONTAINER = "nms"
CONTAINER_CONFIG_FILE_PATH = "nms/config/webuicfg.conf"
EXPECTED_CONFIG_FILE_PATH = "tests/unit/expected_webui_cfg.yaml"
GNB_IDENTITY_RELATION_NAME = "fiveg_gnb_identity"
GNB_CONFIG_FILE = "nms/config/gnb_config.json"
FIVEG_N4_RELATION_NAME = "fiveg_n4"
REMOTE_APP_NAME = "some_app"
SDCORE_CONFIG_RELATION_NAME = "sdcore-config"
UPF_CONFIG_FILE = "nms/config/upf_config.json"


def read_file_content(path: str) -> str:
    with open(path, "r") as f:
        content = f.read()
    return content


class TestCharmWorkloadConfiguration(NMSUnitTestFixtures):

    def test_given_db_relations_do_not_exist_when_pebble_ready_then_webui_config_file_is_not_written(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        with pytest.raises(FileNotFoundError):
            (root / CONTAINER_CONFIG_FILE_PATH).read_text()

    def test_given_storage_attached_and_webui_config_file_does_not_exist_when_pebble_ready_then_config_file_is_written(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        expected_config_file_content = read_file_content(EXPECTED_CONFIG_FILE_PATH)
        assert (root / CONTAINER_CONFIG_FILE_PATH).read_text() == expected_config_file_content

    def test_given_container_is_ready_db_relations_exist_and_storage_attached_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        pod_ip = "1.1.1.0"
        self.mock_check_output.return_value = pod_ip.encode()
        self.harness.add_storage("config", attach=True)
        self.harness.container_pebble_ready(container_name=CONTAINER)

        expected_plan = {
            "services": {
                CONTAINER: {
                    "override": "replace",
                    "command": "/bin/webconsole --webuicfg /nms/config/webuicfg.conf",
                    "startup": "enabled",
                    "environment": {
                        "GRPC_GO_LOG_VERBOSITY_LEVEL": "99",
                        "GRPC_GO_LOG_SEVERITY_LEVEL": "info",
                        "GRPC_TRACE": "all",
                        "GRPC_VERBOSITY": "debug",
                        "CONFIGPOD_DEPLOYMENT": "5G",
                        "SWAGGER_HOST": pod_ip,
                        "UPF_CONFIG_PATH": "/nms/config/upf_config.json",
                        "GNB_CONFIG_PATH": "/nms/config/gnb_config.json",
                    },
                }
            },
        }
        updated_plan = self.harness.get_container_pebble_plan(CONTAINER).to_dict()
        assert expected_plan == updated_plan

    def test_given_container_is_ready_all_relations_exist_and_storage_attached_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        pod_ip = "1.2.3.4"
        self.mock_check_output.return_value = pod_ip.encode()
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready(container_name=CONTAINER)

        expected_plan = {
            "services": {
                CONTAINER: {
                    "override": "replace",
                    "command": "/bin/webconsole --webuicfg /nms/config/webuicfg.conf",
                    "startup": "enabled",
                    "environment": {
                        "GRPC_GO_LOG_VERBOSITY_LEVEL": "99",
                        "GRPC_GO_LOG_SEVERITY_LEVEL": "info",
                        "GRPC_TRACE": "all",
                        "GRPC_VERBOSITY": "debug",
                        "CONFIGPOD_DEPLOYMENT": "5G",
                        "SWAGGER_HOST": pod_ip,
                        "UPF_CONFIG_PATH": "/nms/config/upf_config.json",
                        "GNB_CONFIG_PATH": "/nms/config/gnb_config.json",
                    },
                }
            },
        }
        updated_plan = self.harness.get_container_pebble_plan(CONTAINER).to_dict()
        assert expected_plan == updated_plan

    def test_given_db_relations_do_not_exist_when_pebble_ready_then_pebble_plan_is_empty(self):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)

        self.harness.container_pebble_ready(container_name=CONTAINER)

        assert {} == self.harness.get_container_pebble_plan(CONTAINER).to_dict()

    def test_given_storage_not_attached_when_sdcore_config_relation_is_created_then_config_url_is_not_published_for_relations(  # noqa: E501
        self, sdcore_config_relation_id, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=False)
        self.mock_set_webui_url_in_all_relations.assert_not_called()

    def test_given_webui_service_is_running_db_relations_are_not_joined_when_sdcore_config_relation_is_joined_then_config_url_is_not_published_for_relations(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.mock_get_service.side_effect = None
        self.mock_set_webui_url_in_all_relations.assert_not_called()

    def test_given_webui_service_is_running_db_relations_are_joined_when_several_sdcore_config_relations_are_joined_then_config_url_is_set_in_all_relations(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.mock_get_service.side_effect = None
        relation_id_1 = self.harness.add_relation(SDCORE_CONFIG_RELATION_NAME, "requirer1")
        self.harness.add_relation_unit(relation_id=relation_id_1, remote_unit_name="requirer1")
        relation_id_2 = self.harness.add_relation(SDCORE_CONFIG_RELATION_NAME, "requirer2")
        self.harness.add_relation_unit(relation_id=relation_id_2, remote_unit_name="requirer2")
        calls = [
            call.emit(webui_url="webui:9876"),
            call.emit(webui_url="webui:9876"),
        ]
        self.mock_set_webui_url_in_all_relations.assert_has_calls(calls)

    def test_given_webui_service_is_not_running_when_sdcore_config_relation_joined_then_config_url_is_not_set_in_the_relations(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)
        self.harness.add_storage("config", attach=True)
        self.mock_get_service.side_effect = ModelError()
        self.mock_set_webui_url_in_all_relations.assert_not_called()

    @pytest.mark.parametrize(
        "relation_name,config_file,relation_data",
        [
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                GNB_CONFIG_FILE,
                {"tac": "1234"},
                id="missing_gnb_name_in_gNB_config",
            ),
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                GNB_CONFIG_FILE,
                {"gnb_name": "some.gnb"},
                id="missing_tac_in_gNB_config",
            ),
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                GNB_CONFIG_FILE,
                {"tac": "", "gnb_name": ""},
                id="gnb_name_and_tac_are_empty_strings_in_gNB_config",
            ),
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                GNB_CONFIG_FILE,
                {"gnb_name": "something", "some": "key"},
                id="invalid_key_in_gNB_config",
            ),
            pytest.param(
                FIVEG_N4_RELATION_NAME,
                UPF_CONFIG_FILE,
                {"upf_hostname": "some.host.name"},
                id="missing_upf_port_in_UPF_config",
            ),
            pytest.param(
                FIVEG_N4_RELATION_NAME,
                UPF_CONFIG_FILE,
                {"upf_port": "1234"},
                id="missing_upf_hostname_in_UPF_config",
            ),
            pytest.param(
                FIVEG_N4_RELATION_NAME,
                UPF_CONFIG_FILE,
                {"upf_hostname": "", "upf_port": ""},
                id="upf_hostname_and_upf_port_are_empty_strings_in_UPF_config",
            ),
            pytest.param(
                FIVEG_N4_RELATION_NAME,
                UPF_CONFIG_FILE,
                {"some": "key"},
                id="invalid_key_in_UPF_config",
            ),
        ],
    )
    def test_given_incomplete_data_in_relation_when_pebble_ready_then_is_not_written_in_upf_or_gnb_config_file(  # noqa: E501
        self, relation_name, config_file, relation_data
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
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
        self.harness.evaluate_status()

        assert json.loads((root / config_file).read_text()) == []

    def test_given_no_db_relations_when_pebble_ready_then_upf_config_file_is_generated_and_pushed(  # noqa: E501
        self,
    ):
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        expected_config = [{"hostname": "some.host.name", "port": "1234"}]
        root = self.harness.get_filesystem_root(CONTAINER)
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_config

    def test_given_no_db_relations_when_pebble_ready_then_gnb_config_file_is_generated_and_pushed(  # noqa: E501
        self,
    ):
        self.harness.add_storage("config", attach=True)
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        self.harness.container_pebble_ready(CONTAINER)

        expected_config = [{"name": "some.gnb.name", "tac": "1234"}]
        root = self.harness.get_filesystem_root(CONTAINER)
        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_config

    def test_given_db_relations_when_pebble_ready_then_upf_config_file_is_generated_and_pushed(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        expected_config = [{"hostname": "some.host.name", "port": "1234"}]
        root = self.harness.get_filesystem_root(CONTAINER)
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_config

    def test_given_db_relations_when_pebble_ready_then_gnb_config_file_is_generated_and_pushed(  # noqa: E501
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=True)
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        expected_config = [{"name": "some.gnb.name", "tac": "1234"}]
        root = self.harness.get_filesystem_root(CONTAINER)
        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_config

    def test_given_multiple_n4_relations_when_pebble_ready_then_upf_config_generated_and_pushed(
        self,
    ):
        self.harness.add_storage("config", attach=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_n4_relation_data({"upf_hostname": "my_host", "upf_port": "77"})

        self.harness.container_pebble_ready(CONTAINER)

        expected_upf_config = [
            {
                "hostname": "some.host.name",
                "port": "1234",
            },
            {
                "hostname": "my_host",
                "port": "77",
            },
        ]
        root = self.harness.get_filesystem_root(CONTAINER)
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_upf_config

    def test_given_multiple_gnb_config_relations_when_pebble_ready_then_gnb_config_is_pushed(
        self,
    ):
        self.harness.add_storage("config", attach=True)
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "my_gnb", "tac": "4567"})

        self.harness.container_pebble_ready(CONTAINER)

        expected_gnb_config = [
            {
                "name": "some.gnb.name",
                "tac": "1234",
            },
            {
                "name": "my_gnb",
                "tac": "4567",
            },
        ]
        root = self.harness.get_filesystem_root(CONTAINER)
        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_gnb_config

    def test_given_upf_config_already_pushed_and_content_matches_when_pebble_ready_then_upf_config_is_not_changed(  # noqa: E501
        self,
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        expected_upf_config = [{"hostname": "some.host.name", "port": "1234"}]
        (root / UPF_CONFIG_FILE).write_text(json.dumps(expected_upf_config))
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_upf_config

    def test_given_gnb_config_already_pushed_and_content_matches_when_pebble_ready_then_gnb_config_is_not_changed(  # noqa: E501
        self,
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        expected_gnb_config = [{"name": "some.gnb.name", "tac": "1234"}]
        (root / GNB_CONFIG_FILE).write_text(json.dumps(expected_gnb_config))
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready(CONTAINER)

        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_gnb_config

    @pytest.mark.parametrize("config_file", [(UPF_CONFIG_FILE), (GNB_CONFIG_FILE)])
    def test_given_no_upf_or_gnb_relation_when_pebble_ready_then_empty_config_file_pushed(
        self, config_file
    ):
        self.harness.add_storage("config", attach=True)

        self.harness.container_pebble_ready(CONTAINER)

        root = self.harness.get_filesystem_root(CONTAINER)
        assert (root / config_file).read_text() == "[]"

    def test_given_upf_config_already_pushed_and_content_changes_when_pebble_ready_then_upf_config_is_updated(  # noqa: E501
        self,
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / UPF_CONFIG_FILE).write_text("some_config")
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_n4_relation_data({"upf_hostname": "my_host", "upf_port": "4567"})

        self.harness.container_pebble_ready(CONTAINER)

        expected_upf_config = [
            {
                "hostname": "some.host.name",
                "port": "1234",
            },
            {
                "hostname": "my_host",
                "port": "4567",
            },
        ]
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_upf_config

    def test_given_gnb_config_already_pushed_and_content_changes_when_pebble_ready_then_gnb_config_is_updated(  # noqa: E501
        self,
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / GNB_CONFIG_FILE).write_text("some configuration")
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "my_gnb", "tac": "4567"})

        self.harness.container_pebble_ready(CONTAINER)

        expected_gnb_config = [
            {
                "name": "some.gnb.name",
                "tac": "1234",
            },
            {
                "name": "my_gnb",
                "tac": "4567",
            },
        ]
        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_gnb_config

    def test_given_two_n4_relations_when_n4_relation_broken_then_upf_config_file_is_updated(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=True)
        fiveg_n4_relation_1_id = self.set_n4_relation_data(
            {"upf_hostname": "some.host.name", "upf_port": "1234"}
        )
        self.set_n4_relation_data({"upf_hostname": "some.host", "upf_port": "22"})
        self.harness.container_pebble_ready(CONTAINER)

        self.harness.remove_relation(fiveg_n4_relation_1_id)

        expected_upf_config = [
            {
                "hostname": "some.host",
                "port": "22",
            }
        ]
        root = self.harness.get_filesystem_root(CONTAINER)
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_upf_config

    def test_given_two_gnb_identity_relations_when_relation_broken_then_gnb_config_file_is_updated(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.add_storage("config", attach=True)
        gnb_identity_relation_1_id = self.set_gnb_identity_relation_data(
            {"gnb_name": "some.gnb.name", "tac": "1234"}
        )
        self.set_gnb_identity_relation_data({"gnb_name": "gnb.name", "tac": "333"})
        self.harness.container_pebble_ready(CONTAINER)

        self.harness.remove_relation(gnb_identity_relation_1_id)

        expected_gnb_config = [
            {
                "name": "gnb.name",
                "tac": "333",
            }
        ]
        root = self.harness.get_filesystem_root(CONTAINER)
        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_gnb_config

    @pytest.mark.parametrize(
        "relation_name,config_file",
        [
            pytest.param(FIVEG_N4_RELATION_NAME, UPF_CONFIG_FILE, id="UPF_config"),
            pytest.param(GNB_IDENTITY_RELATION_NAME, GNB_CONFIG_FILE, id="gNB_config"),
        ],
    )
    def test_given_db_relation_and_existing_config_file_when_relation_broken_then_config_file_is_updated(  # noqa: E501
        self, relation_name, config_file
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        (root / CONTAINER_CONFIG_FILE_PATH).write_text("something")

        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.remove_relation(relation_id)

        assert (root / config_file).read_text() == "[]"

    @pytest.mark.parametrize(
        "relation_name", [(FIVEG_N4_RELATION_NAME), (GNB_IDENTITY_RELATION_NAME)] #ADD OTHER?
    )
    def test_given_storage_not_attached_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.remove_relation(relation_id)

    @pytest.mark.parametrize(
        "relation_name", [(FIVEG_N4_RELATION_NAME), (GNB_IDENTITY_RELATION_NAME)] #ADD OTHER?
    )
    def test_given_cannot_connect_to_container_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
        self.harness.add_storage("config", attach=True)
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container=CONTAINER, val=False)

        self.harness.remove_relation(relation_id)

    @pytest.mark.parametrize(
        "relation_name,config_file",
        [
            pytest.param(FIVEG_N4_RELATION_NAME, UPF_CONFIG_FILE, id="UPF_config"),
            pytest.param(GNB_IDENTITY_RELATION_NAME, GNB_CONFIG_FILE, id="gNB_config"),
        ],
    )
    def test_given_upf_gnb_config_file_does_not_exist_when_relation_broken_then_file_is_created(
        self, relation_name, config_file
    ):
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container=CONTAINER, val=True)
        assert not (root / config_file).exists()

        self.harness.remove_relation(relation_id)

        assert (root / config_file).read_text() == "[]"

    def test_given_no_workload_version_file_when_pebble_ready_then_workload_version_not_set(
        self, auth_database_relation_id, common_database_relation_id
    ):
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.evaluate_status()

        version = self.harness.get_workload_version()
        assert version == ""

    def test_given_workload_version_file_when_pebble_ready_then_workload_version_set(
        self, auth_database_relation_id, common_database_relation_id
    ):
        expected_version = "1.2.3"
        self.harness.add_storage("config", attach=True)
        root = self.harness.get_filesystem_root(CONTAINER)
        os.mkdir(f"{root}/etc")
        (root / "etc/workload-version").write_text(expected_version)
        self.harness.set_can_connect(container=CONTAINER, val=True)

        self.harness.evaluate_status()

        version = self.harness.get_workload_version()
        assert version == expected_version
