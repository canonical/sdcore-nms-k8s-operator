# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import MagicMock, call, patch

import pytest
import requests
from webui import GnodeB, Upf, Webui


class TestWebui:
    patcher_request_get = patch("requests.get")
    patcher_request_post = patch("requests.post")
    patcher_request_delete = patch("requests.delete")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_request_get = TestWebui.patcher_request_get.start()
        self.mock_request_post = TestWebui.patcher_request_post.start()
        self.mock_request_delete = TestWebui.patcher_request_delete.start()
        self.webui = Webui("some_url")
        request.addfinalizer(self.tearDown)

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @staticmethod
    def mock_response_with_exception() -> MagicMock:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP Error occurred")
        return mock_response

    @staticmethod
    def mock_response_with_list(resource_list) -> MagicMock:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = resource_list
        return mock_response

    def test_given_exception_is_raised_when_get_gnb_then_an_empty_list_is_returned(self):
        self.mock_request_get.return_value = self.mock_response_with_exception()

        gnbs = self.webui.get_gnbs()

        assert gnbs == []

    def test_when_get_gnbs_then_gnb_url_is_used(self):
        self.mock_request_get.return_value = self.mock_response_with_list([])

        self.webui.get_gnbs()

        self.mock_request_get.assert_called_once_with("some_url/config/v1/inventory/gnb")

    def test_given_webui_returns_a_gnb_list_when_get_gnbs_then_a_gnb_list_is_returned(self):
        webui_gnbs = [{"name": "some.gnb.name", "tac": "111"}]
        self.mock_request_get.return_value = self.mock_response_with_list(webui_gnbs)

        gnbs = self.webui.get_gnbs()

        expected_gnb = GnodeB(name="some.gnb.name", tac=111)
        assert len(gnbs) == 1
        assert gnbs[0] == expected_gnb

    def test_given_webui_returns_an_empty_list_when_get_gnbs_then_empty_list_is_returned(self):
        webui_gnbs = []
        self.mock_request_get.return_value = self.mock_response_with_list(webui_gnbs)

        gnbs = self.webui.get_gnbs()

        assert gnbs == []

    def test_given_multiple_gnbs_in_webui_when_get_gnbs_then_multiple_gnbs_are_returned(self):
        webui_gnbs = [
            {"name": "some.gnb.name", "tac": "111"},
            {"name": "a_gnb_name", "tac": "342"},
            {"name": "other.gnb_name", "tac": "99"},
        ]
        self.mock_request_get.return_value = self.mock_response_with_list(webui_gnbs)

        gnbs = self.webui.get_gnbs()

        expected_gnbs = [
            GnodeB(name="some.gnb.name", tac=111),
            GnodeB(name="a_gnb_name", tac=342),
            GnodeB(name="other.gnb_name", tac=99),
        ]
        for gnb in expected_gnbs:
            assert gnb in gnbs
        assert len(gnbs) == 3

    def test_given_exception_is_raised_when_add_gnb_then_exception_is_handled(self):
        self.mock_request_post.return_value = self.mock_response_with_exception()

        gnb = GnodeB(name="some.gnb.name", tac=111)
        self.webui.add_gnb(gnb)

        self.mock_request_post.assert_called_once_with(
            "some_url/config/v1/inventory/gnb/some.gnb.name",
            headers={"Content-Type": "application/json"},
            json={"tac": "111"},
        )

    def test_given_a_valid_gnb_when_add_gnb_then_gnb_is_added_to_webui(self):
        gnb = GnodeB(name="some.gnb.name", tac=111)
        self.webui.add_gnb(gnb)

        self.mock_request_post.assert_called_once_with(
            "some_url/config/v1/inventory/gnb/some.gnb.name",
            headers={"Content-Type": "application/json"},
            json={"tac": "111"},
        )

    def test_given_exception_is_raised_when_delete_gnb_then_exceptions_is_handled(self):
        self.mock_request_delete.return_value = self.mock_response_with_exception()

        gnb_name = "some.gnb.name"
        self.webui.delete_gnb(gnb_name)

        self.mock_request_delete.assert_called_once_with(
            f"some_url/config/v1/inventory/gnb/{gnb_name}"
        )

    def test_given_valid_gnb_when_delete_gnb_then_gnb_is_successfully_deleted(self):
        gnb_name = "some.gnb.name"
        self.webui.delete_gnb(gnb_name)

        self.mock_request_delete.assert_called_once_with(
            f"some_url/config/v1/inventory/gnb/{gnb_name}"
        )

    def test_given_exception_is_raised_when_get_upfs_then_an_empty_list_is_returned(self):
        self.mock_request_get.return_value = self.mock_response_with_exception()

        upfs = self.webui.get_upfs()

        assert upfs == []

    def test_when_get_upfs_then_upf_url_is_used(self):
        webui_upfs = []
        self.mock_request_get.return_value = self.mock_response_with_list(webui_upfs)

        self.webui.get_upfs()

        self.mock_request_get.assert_called_once_with("some_url/config/v1/inventory/upf")

    def test_given_webui_returns_a_upf_list_when_get_upfs_then_a_upf_list_is_returned(self):
        webui_upfs = [{"hostname": "some.host.name", "port": "111"}]
        self.mock_request_get.return_value = self.mock_response_with_list(webui_upfs)

        upfs = self.webui.get_upfs()

        expected_upf = Upf(hostname="some.host.name", port=111)
        assert len(upfs) == 1
        assert upfs[0] == expected_upf

    def test_given_webui_returns_an_empty_list_when_get_upfs_then_empty_list_is_returned(self):
        webui_upfs = []
        self.mock_request_get.return_value = self.mock_response_with_list(webui_upfs)

        upfs = self.webui.get_upfs()

        assert upfs == []

    def test_given_multiple_upfs_in_webui_when_get_upfs_then_multiple_upfs_are_returned(self):
        webui_upfs = [
            {"hostname": "some.host.name", "port": "111"},
            {"hostname": "a_host_name", "port": "342"},
            {"hostname": "other.host_name", "port": "99"},
        ]
        self.mock_request_get.return_value = self.mock_response_with_list(webui_upfs)

        upfs = self.webui.get_upfs()

        expected_upfs = [
            Upf(hostname="some.host.name", port=111),
            Upf(hostname="a_host_name", port=342),
            Upf(hostname="other.host_name", port=99),
        ]
        for upf in expected_upfs:
            assert upf in upfs
        assert len(upfs) == 3

    def test_given_exception_is_raised_when_add_upf_then_exception_is_handled(self):
        self.mock_request_post.return_value = self.mock_response_with_exception()

        upf = Upf(hostname="some.upf.name", port=111)
        self.webui.add_upf(upf)

        self.mock_request_post.assert_called_once_with(
            "some_url/config/v1/inventory/upf/some.upf.name",
            headers={"Content-Type": "application/json"},
            json={"port": "111"},
        )

    def test_given_a_valid_upf_when_add_upf_then_upf_is_added_to_webui(self):
        upf = Upf(hostname="some.upf.name", port=22)
        self.webui.add_upf(upf)

        self.mock_request_post.assert_called_once_with(
            "some_url/config/v1/inventory/upf/some.upf.name",
            headers={"Content-Type": "application/json"},
            json={"port": "22"},
        )

    def test_given_exception_is_raised_when_delete_upf_then_exceptions_is_handled(self):
        self.mock_request_delete.return_value = self.mock_response_with_exception()

        upf_name = "some.upf.name"
        self.webui.delete_upf(upf_name)

        self.mock_request_delete.assert_called_once_with(
            f"some_url/config/v1/inventory/upf/{upf_name}"
        )

    def test_given_valid_upf_when_delete_upf_then_upf_is_successfully_deleted(self):
        upf_name = "some.upf.name"
        self.webui.delete_upf(upf_name)

        self.mock_request_delete.assert_called_once_with(
            f"some_url/config/v1/inventory/upf/{upf_name}"
        )

    def test_given_url_is_changed_when_get_upfs_then_new_url_is_used(self):
        webui_upfs = []
        self.mock_request_get.return_value = self.mock_response_with_list(webui_upfs)
        self.webui.get_upfs()

        self.webui.set_url("new_url")
        self.webui.get_upfs()

        calls = [
            call("some_url/config/v1/inventory/upf"),
            call("new_url/config/v1/inventory/upf"),
        ]
        self.mock_request_get.assert_has_calls(calls, any_order=True)

    @pytest.mark.parametrize(
        "gnb",
        [
            pytest.param(
                {"hostname": "some.gnb.name", "tac": "111"},
                id="missing_name_parameter",
            ),
            pytest.param(
                {"name": "some.gnb.name", "port": "111"},
                id="missing_tac_parameter",
            ),
            pytest.param(
                {"name": "some.host.name", "tac": "aaa"},
                id="invalid_str_tac",
            ),
        ],
    )
    def test_given_webui_returns_an_invalid_gnb_when_get_gnbs_then_gnb_is_not_returned(self, gnb):
        webui_gnbs = [gnb]
        self.mock_request_get.return_value = self.mock_response_with_list(webui_gnbs)

        gnbs = self.webui.get_gnbs()

        assert gnbs == []

    @pytest.mark.parametrize(
        "upf",
        [
            pytest.param(
                {"name": "some.host.name", "port": "111"},
                id="missing_hostname_parameter",
            ),
            pytest.param(
                {"hostname": "some.host.name", "tac": "111"},
                id="missing_port_parameter",
            ),
            pytest.param(
                {"hostname": "some.host.name", "port": "aaa"},
                id="invalid_str_port",
            ),
        ],
    )
    def test_given_webui_returns_an_invalid_upf_when_get_upfs_then_upf_is_not_returned(self, upf):
        webui_upfs = [upf]
        self.mock_request_get.return_value = self.mock_response_with_list(webui_upfs)

        upfs = self.webui.get_upfs()

        assert upfs == []
