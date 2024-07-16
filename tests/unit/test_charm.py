# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import os
from unittest.mock import call, patch

import pytest
from charm import SDCoreNMSOperatorCharm
from ops import testing
from ops.model import ActiveStatus, BlockedStatus, ModelError, WaitingStatus

FIVEG_N4_RELATION_NAME = "fiveg_n4"
TEST_FIVEG_N4_PROVIDER_APP_NAME = "fiveg_n4_provider_app"
SDCORE_MANAGEMENT_RELATION_NAME = "sdcore-management"
TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME = "sdcore_management_provider_app"
GNB_IDENTITY_RELATION_NAME = "fiveg_gnb_identity"
TEST_GNB_IDENTITY_PROVIDER_APP_NAME = "fiveg_gnb_identity_provider_app"
UPF_CONFIG_FILE = "nms/config/upf_config.json"
TEST_UPF_CONFIG_PATH = f"/{UPF_CONFIG_FILE}"
GNB_CONFIG_FILE = "nms/config/gnb_config.json"
TEST_GNB_CONFIG_PATH = f"/{GNB_CONFIG_FILE}"
REMOTE_APP_NAME = "some_app"
SDCORE_CONFIG_RELATION_NAME = "sdcore-config"


def read_file(path: str) -> str:
    """Read a file and returns as a string.

    Args:
        path (str): path to the file.

    Returns:
        str: content of the file.
    """
    with open(path, "r") as f:
        content = f.read()
    return content


class TestCharm:

    patcher_set_webui_url_in_all_relations = patch(
        "charms.sdcore_nms_k8s.v0.sdcore_config.SdcoreConfigProvides.set_webui_url_in_all_relations"
    )
    patcher_get_service = patch("ops.model.Container.get_service")

    @pytest.fixture()
    def setUp(self):
        self.mock_get_service = TestCharm.patcher_get_service.start()
        self.mock_set_webui_url_in_all_relations = TestCharm.patcher_set_webui_url_in_all_relations.start()  # noqa: E501

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def harness(self, setUp, request):
        self.harness = testing.Harness(SDCoreNMSOperatorCharm)
        self.harness.begin()
        yield self.harness
        self.harness.cleanup()
        request.addfinalizer(self.tearDown)

    def set_sdcore_management_relation_data(self, management_url) -> int:
        """Create the sdcore_management relation and set its data.

        Returns:
            int: ID of the created relation
        """
        relation_id = self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=relation_id,
            app_or_unit=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
            key_values={"management_url": management_url},
        )
        return relation_id

    def set_gnb_identity_relation_data(self, key_values) -> int:
        """Create the fiveg_gnb_identity relation and set its data.

        Returns:
            int: ID of the created relation
        """
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=TEST_GNB_IDENTITY_PROVIDER_APP_NAME,
            key_values=key_values,
        )
        return gnb_identity_relation_id

    def set_n4_relation_data(self, key_values) -> int:
        """Create the fiveg_n4 relation and set its data.

        Returns:
            int: ID of the created relation
        """
        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=TEST_FIVEG_N4_PROVIDER_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=TEST_FIVEG_N4_PROVIDER_APP_NAME,
            key_values=key_values,
        )
        return fiveg_n4_relation_id

    def _create_sdcore_config_relation(self, requirer) -> None:
        relation_id = self.harness.add_relation(SDCORE_CONFIG_RELATION_NAME, requirer)  # type:ignore
        self.harness.add_relation_unit(relation_id=relation_id, remote_unit_name=f"{requirer}/0")  # type:ignore

    def test_given_cant_connect_to_container_when_update_config_then_status_is_waiting(self):
        self.harness.update_config(key_values={})
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus("Waiting for container to be ready")

    def test_given_storage_not_available_when_pebble_ready_then_status_is_waiting(self):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")

        self.harness.container_pebble_ready("nms")
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus(
            "Waiting for storage to be attached"
        )

    def test_given_sdcore_management_relation_not_created_when_pebble_ready_then_status_is_blocked(
        self,
    ):
        self.harness.container_pebble_ready("nms")
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == BlockedStatus(
            f"Waiting for `{SDCORE_MANAGEMENT_RELATION_NAME}` relation to be created"
        )

    def test_given_management_url_not_available_when_pebble_ready_then_status_is_waiting(self):
        self.harness.add_relation(
            relation_name=SDCORE_MANAGEMENT_RELATION_NAME,
            remote_app=TEST_SDCORE_MANAGEMENT_PROVIDER_APP_NAME,
        )

        self.harness.container_pebble_ready("nms")
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus(
            "Waiting for webui management URL to be available"
        )

    def test_given_management_url_available_when_pebble_ready_then_status_is_active(self):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")

        self.harness.container_pebble_ready("nms")
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

    @pytest.mark.parametrize(
        "relation_name", [(FIVEG_N4_RELATION_NAME), (GNB_IDENTITY_RELATION_NAME)]
    )
    def test_given_data_from_not_mandatory_relation_not_available_when_pebble_ready_then_status_is_active(  # noqa: E501
        self, relation_name
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )

        self.harness.container_pebble_ready("nms")
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

    @pytest.mark.parametrize(
        "relation_name,relation_data",
        [
            pytest.param(
                GNB_IDENTITY_RELATION_NAME, {"tac": "1234"}, id="missing_gnb_name_in_gNB_config"
            ),
            pytest.param(
                GNB_IDENTITY_RELATION_NAME,
                {"gnb_name": "some.gnb"},
                id="missing_tac_in_gNB_config",
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
        ],
    )
    def test_given_incomplete_data_in_not_mandatory_relation_when_pebble_ready_then_status_is_active(  # noqa: E501
        self, relation_name, relation_data
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=relation_id,
            app_or_unit=REMOTE_APP_NAME,
            key_values=relation_data,
        )

        self.harness.container_pebble_ready("nms")
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

    def test_given_service_is_not_running_when_evaluate_status_then_status_is_waiting(self):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        (root / UPF_CONFIG_FILE).write_text("some")
        (root / GNB_CONFIG_FILE).write_text("content")
        self.mock_get_service.side_effect = ModelError()

        self.harness.set_can_connect(container="nms", val=True)
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus("Waiting for NMS service to start")

    @pytest.mark.parametrize(
        "existing_config_file,app_name",
        [
            pytest.param(UPF_CONFIG_FILE, "GNB", id="gNB_config_file_is_missing"),
            pytest.param(GNB_CONFIG_FILE, "UPF", id="UPF_config_file_is_missing"),
        ],
    )
    def test_given_config_file_not_available_when_evaluate_status_then_status_is_waiting(
        self, existing_config_file, app_name
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        (root / existing_config_file).write_text("something")

        self.harness.set_can_connect(container="nms", val=True)
        self.harness.evaluate_status()

        assert self.harness.model.unit.status == WaitingStatus(
            f"Waiting for {app_name} config file to be stored"
        )

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
    def test_given_incomplete_data_in_relation_when_pebble_ready_then_is_not_written_in_config_file(  # noqa: E501
        self, relation_name, config_file, relation_data
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=relation_id,
            app_or_unit=REMOTE_APP_NAME,
            key_values=relation_data,
        )

        self.harness.container_pebble_ready("nms")
        self.harness.evaluate_status()

        assert json.loads((root / config_file).read_text()) == []

    def test_given_information_available_all_relations_created_when_pebble_ready_then_status_is_active(  # noqa: E501
        self,
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.harness.set_can_connect(container="nms", val=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.evaluate_status()

        assert self.harness.model.unit.status == ActiveStatus()

    def test_given_all_relations_created_when_pebble_ready_then_pebble_plan_is_applied(self):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        test_management_url = "http://10.0.0.2:5000"
        self.set_sdcore_management_relation_data(test_management_url)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        expected_plan = {
            "services": {
                "nms": {
                    "startup": "enabled",
                    "override": "replace",
                    "command": "/bin/bash -c 'cd /app && npm run start'",
                    "environment": {
                        "UPF_CONFIG_PATH": TEST_UPF_CONFIG_PATH,
                        "GNB_CONFIG_PATH": TEST_GNB_CONFIG_PATH,
                        "WEBUI_ENDPOINT": test_management_url,
                    },
                }
            }
        }

        self.harness.container_pebble_ready("nms")
        updated_plan = self.harness.get_container_pebble_plan("nms").to_dict()

        assert expected_plan == updated_plan

    def test_given_only_sdcore_management_relation_when_pebble_ready_then_pebble_plan_is_applied(  # noqa: E501
        self,
    ):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        test_management_url = "http://10.11.0.1:5000"
        self.set_sdcore_management_relation_data(test_management_url)

        expected_plan = {
            "services": {
                "nms": {
                    "startup": "enabled",
                    "override": "replace",
                    "command": "/bin/bash -c 'cd /app && npm run start'",
                    "environment": {
                        "UPF_CONFIG_PATH": TEST_UPF_CONFIG_PATH,
                        "GNB_CONFIG_PATH": TEST_GNB_CONFIG_PATH,
                        "WEBUI_ENDPOINT": test_management_url,
                    },
                }
            }
        }
        self.harness.container_pebble_ready("nms")
        updated_plan = self.harness.get_container_pebble_plan("nms").to_dict()

        assert expected_plan == updated_plan

    def test_given_no_sdcore_management_relation_when_pebble_ready_then_upf_config_file_is_generated_and_pushed(  # noqa: E501
        self,
    ):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})

        self.harness.container_pebble_ready("nms")

        expected_config = [{"hostname": "some.host.name", "port": "1234"}]
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_config

    def test_given_no_sdcore_management_relation_when_pebble_ready_then_gnb_config_file_is_generated_and_pushed(  # noqa: E501
        self,
    ):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready("nms")

        expected_config = [{"name": "some.gnb.name", "tac": "1234"}]
        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_config

    def test_given_sdcore_management_relation_when_pebble_ready_then_upf_config_file_is_generated_and_pushed(  # noqa: E501
        self,
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})

        self.harness.container_pebble_ready("nms")

        expected_config = [{"hostname": "some.host.name", "port": "1234"}]
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_config

    def test_given_sdcore_management_relation_when_pebble_ready_then_gnb_config_file_is_generated_and_pushed(  # noqa: E501
        self,
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready("nms")

        expected_config = [{"name": "some.gnb.name", "tac": "1234"}]
        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_config

    def test_given_multiple_n4_relations_when_pebble_ready_then_upf_config_generated_and_pushed(
        self,
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.harness.set_can_connect(container="nms", val=True)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_n4_relation_data({"upf_hostname": "my_host", "upf_port": "77"})

        self.harness.container_pebble_ready("nms")

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
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_upf_config

    def test_given_multiple_gnb_config_relations_when_pebble_ready_then_gnb_config_is_pushed(
        self,
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "my_gnb", "tac": "4567"})

        self.harness.container_pebble_ready("nms")

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

    def test_given_gnb_config_already_pushed_and_content_matches_when_pebble_ready_then_gnb_config_is_not_changed(  # noqa: E501
        self,
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        expected_gnb_content = read_file("tests/unit/expected_gnb.json")
        (root / GNB_CONFIG_FILE).write_text(expected_gnb_content)
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})

        self.harness.container_pebble_ready("nms")

        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == json.loads(expected_gnb_content)

    def test_given_upf_config_already_pushed_and_content_matches_when_pebble_ready_then_upf_config_is_not_changed(  # noqa: E501
        self,
    ):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        expected_upf_content = read_file("tests/unit/expected_upf.json")
        (root / UPF_CONFIG_FILE).write_text(expected_upf_content)
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})

        self.harness.container_pebble_ready("nms")

        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == json.loads(expected_upf_content)

    @pytest.mark.parametrize("config_file", [(UPF_CONFIG_FILE), (GNB_CONFIG_FILE)])
    def test_given_no_relation_when_pebble_ready_then_config_file_pushed(self, config_file):
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        self.harness.set_can_connect(container="nms", val=True)
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)

        self.harness.container_pebble_ready("nms")

        assert (root / config_file).read_text() == "[]"

    def test_given_upf_config_already_pushed_and_content_changes_when_pebble_ready_then_upf_config_is_updated(  # noqa: E501
        self,
    ):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        (root / UPF_CONFIG_FILE).write_text("some_config")
        self.set_n4_relation_data({"upf_hostname": "some.host.name", "upf_port": "1234"})
        self.set_n4_relation_data({"upf_hostname": "my_host", "upf_port": "4567"})

        self.harness.container_pebble_ready("nms")

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
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        (root / GNB_CONFIG_FILE).write_text("some configuration")
        self.set_gnb_identity_relation_data({"gnb_name": "some.gnb.name", "tac": "1234"})
        self.set_gnb_identity_relation_data({"gnb_name": "my_gnb", "tac": "4567"})

        self.harness.container_pebble_ready("nms")

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

    def test_given_2_n4_relations_when_n4_relation_broken_then_upf_config_file_is_updated(self):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        fiveg_n4_relation_1_id = self.set_n4_relation_data(
            {"upf_hostname": "some.host.name", "upf_port": "1234"}
        )
        self.set_n4_relation_data({"upf_hostname": "some.host", "upf_port": "22"})
        self.harness.container_pebble_ready("nms")

        self.harness.remove_relation(fiveg_n4_relation_1_id)

        expected_upf_config = [
            {
                "hostname": "some.host",
                "port": "22",
            }
        ]
        assert json.loads((root / UPF_CONFIG_FILE).read_text()) == expected_upf_config

    def test_given_2_gnb_identity_relations_when_relation_broken_then_gnb_config_file_is_updated(
        self,
    ):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        gnb_identity_relation_1_id = self.set_gnb_identity_relation_data(
            {"gnb_name": "some.gnb.name", "tac": "1234"}
        )
        self.set_gnb_identity_relation_data({"gnb_name": "gnb.name", "tac": "333"})
        self.harness.container_pebble_ready("nms")

        self.harness.remove_relation(gnb_identity_relation_1_id)

        expected_gnb_config = [
            {
                "name": "gnb.name",
                "tac": "333",
            }
        ]
        assert json.loads((root / GNB_CONFIG_FILE).read_text()) == expected_gnb_config

    @pytest.mark.parametrize(
        "relation_name,config_file",
        [
            pytest.param(FIVEG_N4_RELATION_NAME, UPF_CONFIG_FILE, id="UPF_config"),
            pytest.param(GNB_IDENTITY_RELATION_NAME, GNB_CONFIG_FILE, id="gNB_config"),
        ],
    )
    def test_given_not_sdcore_management_relation_and_existing_config_file_when_relation_broken_then_config_file_is_updated(  # noqa: E501
        self, relation_name, config_file
    ):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        (root / config_file).write_text("Some random config")

        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container="nms", val=True)

        self.harness.remove_relation(relation_id)

        assert (root / config_file).read_text() == "[]"

    @pytest.mark.parametrize(
        "relation_name", [(FIVEG_N4_RELATION_NAME), (GNB_IDENTITY_RELATION_NAME)]
    )
    def test_given_storage_not_attached_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container="nms", val=True)

        self.harness.remove_relation(relation_id)

    @pytest.mark.parametrize(
        "relation_name", [(FIVEG_N4_RELATION_NAME), (GNB_IDENTITY_RELATION_NAME)]
    )
    def test_given_cannot_connect_to_container_when_relation_broken_then_no_exception_is_raised(
        self, relation_name
    ):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container="nms", val=False)

        self.harness.remove_relation(relation_id)

    @pytest.mark.parametrize(
        "relation_name,config_file",
        [
            pytest.param(FIVEG_N4_RELATION_NAME, UPF_CONFIG_FILE, id="UPF_config"),
            pytest.param(GNB_IDENTITY_RELATION_NAME, GNB_CONFIG_FILE, id="gNB_config"),
        ],
    )
    def test_given_config_file_does_not_exist_when_relation_broken_then_file_is_created(
        self, relation_name, config_file
    ):
        root = self.harness.get_filesystem_root("nms")
        (root / "nms/config/").mkdir(parents=True)
        relation_id = self.harness.add_relation(
            relation_name=relation_name,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.set_can_connect(container="nms", val=True)
        assert not (root / config_file).exists()

        self.harness.remove_relation(relation_id)

        assert (root / config_file).read_text() == "[]"

    def test_given_no_workload_version_file_when_pebble_ready_then_workload_version_not_set(
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.evaluate_status()
        version = self.harness.get_workload_version()
        assert version == ""

    def test_given_workload_version_file_when_pebble_ready_then_workload_version_set(
        self,
    ):
        expected_version = "1.2.3"
        root = self.harness.get_filesystem_root("nms")
        os.mkdir(f"{root}/etc")
        (root / "etc/workload-version").write_text(expected_version)
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.evaluate_status()
        version = self.harness.get_workload_version()
        assert version == expected_version

    def test_given_storage_not_attached_when_sdcore_config_relation_is_created_then_webui_url_is_not_published_for_relations(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_storage("config", attach=False)
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        self._create_sdcore_config_relation("requirer")
        self.mock_set_webui_url_in_all_relations.assert_not_called()

    def test_given_nms_service_is_running_when_sdcore_config_relation_is_joined_then_webui_url_is_published_for_relations(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_storage("config", attach=True)
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        self.mock_get_service.side_effect = None
        self._create_sdcore_config_relation("requirer")
        calls = [
            call.emit(webui_url="webui:9876"),
        ]
        self.mock_set_webui_url_in_all_relations.assert_has_calls(calls)

    def test_given_nms_service_is_running_when_several_sdcore_config_relations_are_joined_then_webui_url_is_set_in_all_relations(  # noqa: E501
        self
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_storage("config", attach=True)
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
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

    def test_given_nms_service_is_not_running_when_sdcore_config_relation_joined_then_webui_url_is_not_set_in_the_relations(  # noqa: E501
        self,
    ):
        self.harness.set_can_connect(container="nms", val=True)
        self.harness.add_storage("config", attach=True)
        self.set_sdcore_management_relation_data("http://10.0.0.1:5000")
        self.mock_get_service.side_effect = ModelError()
        self._create_sdcore_config_relation(requirer="requirer1")
        self.mock_set_webui_url_in_all_relations.assert_not_called()
