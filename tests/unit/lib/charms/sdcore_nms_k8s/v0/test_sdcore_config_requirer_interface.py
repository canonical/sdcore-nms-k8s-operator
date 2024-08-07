# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
from typing import Any, Generator
from unittest.mock import call, patch

import pytest
from ops import BoundEvent, testing

from tests.unit.lib.charms.sdcore_nms_k8s.v0.dummy_sdcore_config_requirer_charm.src.dummy_requirer_charm import (  # noqa: E501
    DummySdcoreConfigRequirerCharm,
)

DUMMY_REQUIRER_CHARM = "tests.unit.lib.charms.sdcore_nms_k8s.v0.dummy_sdcore_config_requirer_charm.src.dummy_requirer_charm.DummySdcoreConfigRequirerCharm"  # noqa: E501
REMOTE_APP_NAME = "dummy-sdcore-config-provider"
WEBUI_URL = "sdcore-webui-k8s:9876"


class TestSdcoreConfigRequirer:
    patcher_webui_broken = patch(
        "lib.charms.sdcore_nms_k8s.v0.sdcore_config.SdcoreConfigRequirerCharmEvents.webui_broken"
    )
    patcher_webui_url_available = patch(
        f"{DUMMY_REQUIRER_CHARM}._on_webui_url_available", autospec=True
    )

    @pytest.fixture()
    def setUp(self):
        self.mock_webui_broken = TestSdcoreConfigRequirer.patcher_webui_broken.start()
        self.mock_webui_broken.__class__ = BoundEvent
        self.mock_webui_url_available = (
            TestSdcoreConfigRequirer.patcher_webui_url_available.start()
        )

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def setup_harness(self, setUp, request):
        self.harness = testing.Harness(DummySdcoreConfigRequirerCharm)
        self.harness.set_model_name(name="some_model_name")
        self.harness.set_leader(is_leader=True)
        self.harness.begin()
        yield self.harness
        self.harness.cleanup()
        request.addfinalizer(self.tearDown)

    @pytest.fixture()
    def sdcore_config_relation_id(self) -> Generator[int, Any, Any]:
        relation_id = self.harness.add_relation(
            relation_name="sdcore_config", remote_app=REMOTE_APP_NAME
        )
        self.harness.add_relation_unit(
            relation_id=relation_id, remote_unit_name=f"{REMOTE_APP_NAME}/0"
        )
        yield relation_id

    def test_given_webui_information_in_relation_data_when_relation_changed_then_webui_url_available_event_emitted(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        relation_data = {"webui_url": WEBUI_URL}
        self.harness.update_relation_data(
            sdcore_config_relation_id, app_or_unit=REMOTE_APP_NAME, key_values=relation_data
        )

        self.mock_webui_url_available.assert_called()

    def test_given_webui_information_not_in_relation_data_when_relation_changed_then_webui_url_available_event_not_emitted(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        relation_data = {}
        self.harness.update_relation_data(
            sdcore_config_relation_id, app_or_unit=REMOTE_APP_NAME, key_values=relation_data
        )

        self.mock_webui_url_available.assert_not_called()

    def test_given_invalid_webui_information_in_relation_data_when_relation_changed_then_webui_url_available_event_not_emitted(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        relation_data = {"foo": "bar"}
        self.harness.update_relation_data(
            sdcore_config_relation_id, app_or_unit=REMOTE_APP_NAME, key_values=relation_data
        )

        self.mock_webui_url_available.assert_not_called()

    def test_given_invalid_webui_information_in_relation_data_when_relation_changed_then_error_is_logged(  # noqa: E501
        self, caplog, sdcore_config_relation_id
    ):
        relation_data = {"foo": "bar"}

        with caplog.at_level(logging.DEBUG):
            self.harness.update_relation_data(
                sdcore_config_relation_id, app_or_unit=REMOTE_APP_NAME, key_values=relation_data
            )
            assert "Invalid relation data" in caplog.text

    def test_given_webui_information_in_relation_data_when_get_webui_url_is_called_then_expected_url_is_returned(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        relation_data = {"webui_url": WEBUI_URL}
        self.harness.update_relation_data(
            sdcore_config_relation_id, app_or_unit=REMOTE_APP_NAME, key_values=relation_data
        )

        webui_url = self.harness.charm.webui_requirer.webui_url

        assert webui_url == WEBUI_URL

    def test_given_webui_information_not_in_relation_data_when_get_webui_url_then_returns_none(  # noqa: E501
        self, caplog, sdcore_config_relation_id
    ):
        relation_data = {}

        with caplog.at_level(logging.DEBUG):
            self.harness.update_relation_data(
                sdcore_config_relation_id, app_or_unit=REMOTE_APP_NAME, key_values=relation_data
            )
            webui_url = self.harness.charm.webui_requirer.webui_url
            assert webui_url is None
            assert "Invalid relation data" in caplog.text

    def test_given_webui_information_in_relation_data_is_not_valid_when_get_webui_url_then_returns_none(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        relation_data = {"foo": "bar"}

        self.harness.update_relation_data(
            sdcore_config_relation_id, app_or_unit=REMOTE_APP_NAME, key_values=relation_data
        )

        webui_url = self.harness.charm.webui_requirer.webui_url
        assert webui_url is None

    def test_given_sdcore_config_relation_created_when_relation_broken_then_webui_broken_event_emitted(  # noqa: E501
        self, sdcore_config_relation_id
    ):
        self.harness.remove_relation(sdcore_config_relation_id)

        calls = [call.emit()]
        self.mock_webui_broken.assert_has_calls(calls)
