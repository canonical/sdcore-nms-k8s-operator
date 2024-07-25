# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from typing import Generator
from unittest.mock import Mock, patch

import pytest
from charm import SDCoreNMSOperatorCharm
from ops import testing

AUTH_DATABASE_RELATION_NAME = "auth_database"
COMMON_DATABASE_RELATION_NAME = "common_database"
FIVEG_N4_RELATION_NAME = "fiveg_n4"
GNB_IDENTITY_RELATION_NAME = "fiveg_gnb_identity"
REMOTE_APP_NAME = "some_app"
SDCORE_CONFIG_RELATION_NAME = "sdcore-config"

class NMSUnitTestFixtures:

    patcher_check_output = patch("charm.check_output")
    patcher_get_service = patch("ops.model.Container.get_service")
    patcher_set_webui_url_in_all_relations = patch(
        "charms.sdcore_nms_k8s.v0.sdcore_config.SdcoreConfigProvides.set_webui_url_in_all_relations"
    )
    patcher_request_get = patch("requests.get")
    patcher_request_post = patch("requests.post")
    patcher_request_delete = patch("requests.delete")

    @pytest.fixture()
    def setUp(self):
        self.mock_check_output = NMSUnitTestFixtures.patcher_check_output.start()
        self.mock_get_service = NMSUnitTestFixtures.patcher_get_service.start()
        self.mock_set_webui_url_in_all_relations = NMSUnitTestFixtures.patcher_set_webui_url_in_all_relations.start()  # noqa: E501
        self.mock_request_get = NMSUnitTestFixtures.patcher_request_get.start()
        self.mock_request_post = NMSUnitTestFixtures.patcher_request_post.start()
        self.mock_request_delete = NMSUnitTestFixtures.patcher_request_delete.start()

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def harness(self, setUp, request, empty_inventory):
        self.harness = testing.Harness(SDCoreNMSOperatorCharm)
        self.harness.set_model_name(name="whatever")
        self.harness.set_leader(is_leader=True)
        self.harness.begin()
        yield self.harness
        self.harness.cleanup()
        request.addfinalizer(self.tearDown)

    @pytest.fixture()
    def common_database_relation_id(self) -> Generator[int, None, None]:
        relation_id = self.harness.add_relation(COMMON_DATABASE_RELATION_NAME, "mongodb")  # type:ignore
        self.harness.add_relation_unit(relation_id=relation_id, remote_unit_name="mongodb/0")  # type:ignore
        self.harness.update_relation_data(  # type:ignore
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
        relation_id = self.harness.add_relation(AUTH_DATABASE_RELATION_NAME, "mongodb")  # type:ignore
        self.harness.add_relation_unit(relation_id=relation_id, remote_unit_name="mongodb/0")  # type:ignore
        self.harness.update_relation_data(  # type:ignore
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
        relation_id = self.harness.add_relation(  # type:ignore
            SDCORE_CONFIG_RELATION_NAME, REMOTE_APP_NAME
        )
        self.harness.add_relation_unit(  # type:ignore
            relation_id=relation_id, remote_unit_name=f"{REMOTE_APP_NAME}/0"
        )
        yield relation_id

    def set_gnb_identity_relation_data(self, key_values) -> int:
        gnb_identity_relation_id = self.harness.add_relation(  # type:ignore
            relation_name=GNB_IDENTITY_RELATION_NAME,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.update_relation_data(  # type:ignore
            relation_id=gnb_identity_relation_id,
            app_or_unit=REMOTE_APP_NAME,
            key_values=key_values,
        )
        return gnb_identity_relation_id

    def set_n4_relation_data(self, key_values) -> int:
        fiveg_n4_relation_id = self.harness.add_relation(  # type:ignore
            relation_name=FIVEG_N4_RELATION_NAME,
            remote_app=REMOTE_APP_NAME,
        )
        self.harness.update_relation_data(  # type:ignore
            relation_id=fiveg_n4_relation_id,
            app_or_unit=REMOTE_APP_NAME,
            key_values=key_values,
        )
        return fiveg_n4_relation_id

    @pytest.fixture()
    def empty_inventory(self) -> Generator[None, None, None]:
        self.mock_request_get.return_value = self.get_inventory_mock_response([])

    def get_inventory_mock_response(self, existing_inventory: list) -> Mock:
        mock_get_response = Mock()
        mock_get_response.json.return_value = existing_inventory
        mock_get_response.status_code = 200
        return mock_get_response
    
    @property
    def empty_mock_response(self):
        self.get_inventory_mock_response([])
