# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from typing import Generator
from unittest.mock import Mock, patch

import pytest
from webui import Webui


class TestWebui:

    patcher_request_get = patch("requests.get")
    patcher_request_post = patch("requests.post")
    patcher_request_delete = patch("requests.delete")

    @pytest.fixture()
    def setUp(self):
        self.mock_request_get = TestWebui.patcher_request_get.start()
        self.mock_request_post = TestWebui.patcher_request_post.start()
        self.mock_request_delete = TestWebui.patcher_request_delete.start()

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def harness(self, setUp, request, empty_inventory):
        self.webui = Webui("some_url")
        request.addfinalizer(self.tearDown)

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


    def test_given_exception_is_raised_when_get_gnb_from_inventory_then_an_empty_list_is_returned(self):  # noqa: E501
        pass

    def test_given_webui_returns_a_gnb_list_when_get_gnb_from_inventory_then_an_gnb_list_is_returned(self):  # noqa: E501
        pass

    def test_given_exception_is_raised_when_add_gnb_to_inventory_then_exception_is_handled(self):
        pass

    def test_given_a_valid_gnb_when_add_gnb_to_inventory_then_gnb_is_added_to_inventory(self):
        pass

    def test_given_exception_is_raised_when_delete_gnb_from_inventory_then_exceptions_is_handled(self):  # noqa: E501
        pass

    def test_given_valid_gnb_when_delete_gnb_from_inventory_then_gnb_is_successfully_deleted(self):  # noqa: E501
        pass
