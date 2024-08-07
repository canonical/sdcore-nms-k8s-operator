# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from typing import Generator
from unittest.mock import patch

import pytest
from charm import SDCoreNMSOperatorCharm
from ops import testing

AUTH_DATABASE_RELATION_NAME = "auth_database"
COMMON_DATABASE_RELATION_NAME = "common_database"
FIVEG_N4_RELATION_NAME = "fiveg_n4"
GNB_IDENTITY_RELATION_NAME = "fiveg_gnb_identity"
REMOTE_APP_NAME = "some_app"
SDCORE_CONFIG_RELATION_NAME = "sdcore_config"
CONTAINER = "nms"
CONTAINER_CONFIG_FILE_PATH = "nms/config/webuicfg.conf"


class NMSUnitTestFixtures:
    patcher_check_output = patch("charm.check_output")
    patcher_get_service = patch("ops.model.Container.get_service")
    patcher_set_webui_url_in_all_relations = patch(
        "charms.sdcore_nms_k8s.v0.sdcore_config.SdcoreConfigProvides.set_webui_url_in_all_relations"
    )
    patcher_webui_get_gnbs = patch("webui.Webui.get_gnbs")
    patcher_webui_add_gnb = patch("webui.Webui.add_gnb")
    patcher_webui_delete_gnb = patch("webui.Webui.delete_gnb")
    patcher_webui_get_upfs = patch("webui.Webui.get_upfs")
    patcher_webui_add_upf = patch("webui.Webui.add_upf")
    patcher_webui_delete_upf = patch("webui.Webui.delete_upf")
    patcher_webui_set_url = patch("webui.Webui.set_url")

    @pytest.fixture()
    def setUp(self):
        self.mock_check_output = NMSUnitTestFixtures.patcher_check_output.start()
        self.mock_get_service = NMSUnitTestFixtures.patcher_get_service.start()
        self.mock_set_webui_url_in_all_relations = (
            NMSUnitTestFixtures.patcher_set_webui_url_in_all_relations.start()
        )
        self.mock_get_gnbs = NMSUnitTestFixtures.patcher_webui_get_gnbs.start()
        self.mock_add_gnb = NMSUnitTestFixtures.patcher_webui_add_gnb.start()
        self.mock_delete_gnb = NMSUnitTestFixtures.patcher_webui_delete_gnb.start()
        self.mock_get_upfs = NMSUnitTestFixtures.patcher_webui_get_upfs.start()
        self.mock_add_upf = NMSUnitTestFixtures.patcher_webui_add_upf.start()
        self.mock_delete_upf = NMSUnitTestFixtures.patcher_webui_delete_upf.start()
        self.mock_webui_set_url = NMSUnitTestFixtures.patcher_webui_set_url.start()

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def setup_harness(self, setUp, request, empty_webui_inventory):
        self.harness = testing.Harness(SDCoreNMSOperatorCharm)
        self.harness.set_model_name(name="whatever")
        self.harness.set_leader(is_leader=True)
        self.harness.begin()
        yield self.harness
        self.harness.cleanup()
        request.addfinalizer(self.tearDown)

    @pytest.fixture()
    def common_database_relation_id(self) -> Generator[int, None, None]:
        relation_id = self.harness.add_relation(COMMON_DATABASE_RELATION_NAME, "mongodb")
        self.harness.add_relation_unit(relation_id=relation_id, remote_unit_name="mongodb/0")
        self.harness.update_relation_data(
            relation_id=relation_id,
            app_or_unit="mongodb",
            key_values={
                "username": "banana",
                "password": "pizza",
                "uris": "1.9.11.4:1234",
            },
        )
        yield relation_id

    @pytest.fixture()
    def auth_database_relation_id(self) -> Generator[int, None, None]:
        relation_id = self.harness.add_relation(AUTH_DATABASE_RELATION_NAME, "mongodb")
        self.harness.add_relation_unit(relation_id=relation_id, remote_unit_name="mongodb/0")
        self.harness.update_relation_data(
            relation_id=relation_id,
            app_or_unit="mongodb",
            key_values={
                "username": "apple",
                "password": "hamburger",
                "uris": "1.8.11.4:1234",
            },
        )
        yield relation_id

    @pytest.fixture()
    def sdcore_config_relation_id(self) -> Generator[int, None, None]:
        relation_id = self.harness.add_relation(SDCORE_CONFIG_RELATION_NAME, REMOTE_APP_NAME)
        self.harness.add_relation_unit(
            relation_id=relation_id, remote_unit_name=f"{REMOTE_APP_NAME}/0"
        )
        yield relation_id

    def set_gnb_identity_relation_data(self, key_values) -> int:
        gnb_identity_relation_id = self.harness.add_relation(
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=gnb_identity_relation_id,
            app_or_unit=REMOTE_APP_NAME,
            key_values=key_values,
        )
        return gnb_identity_relation_id

    def set_n4_relation_data(self, key_values) -> int:
        fiveg_n4_relation_id = self.harness.add_relation(
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.update_relation_data(
            relation_id=fiveg_n4_relation_id,
            app_or_unit=REMOTE_APP_NAME,
            key_values=key_values,
        )
        return fiveg_n4_relation_id

    @pytest.fixture()
    def empty_webui_inventory(self) -> None:
        self.mock_get_gnbs.return_value = []
        self.mock_get_upfs.return_value = []
