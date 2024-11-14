# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import MagicMock, patch

import pytest
import requests

from nms import NMS, GnodeB, Upf


class TestNMS:
    patcher_request = patch("requests.request")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_request = TestNMS.patcher_request.start()
        self.nms = NMS("some_url")
        request.addfinalizer(self.tearDown)

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @staticmethod
    def mock_response_with_http_error_exception() -> MagicMock:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP Error occurred")
        return mock_response

    @staticmethod
    def mock_response_with_connection_error_exception() -> MagicMock:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "Error connecting to NMS"
        )
        return mock_response

    @staticmethod
    def mock_response_with_list(resource_list) -> MagicMock:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = resource_list
        return mock_response

    @pytest.mark.parametrize(
        "exception",
        [
            requests.RequestException("Error connecting to NMS"),
            OSError("Error connecting to NMS"),
        ],
    )
    def test_given_exception_is_raised_when_list_gnbs_then_an_empty_list_is_returned(
        self, exception
    ):
        self.mock_request.side_effect = exception

        gnbs = self.nms.list_gnbs()

        assert gnbs == []

    def test_when_list_gnbs_then_gnb_url_is_used(self):
        self.mock_request.return_value = self.mock_response_with_list([])

        self.nms.list_gnbs()

        self.mock_request.assert_called_once_with(
            method="GET",
            url="some_url/config/v1/inventory/gnb",
            headers={"Content-Type": "application/json"},
            json=None,
            verify=False,
        )

    def test_given_nms_returns_a_gnb_list_when_list_gnbs_then_a_gnb_list_is_returned(self):
        nms_gnbs = [{"name": "some.gnb.name", "tac": "111"}]
        self.mock_request.return_value = self.mock_response_with_list(nms_gnbs)

        gnbs = self.nms.list_gnbs()

        expected_gnb = GnodeB(name="some.gnb.name", tac=111)
        assert len(gnbs) == 1
        assert gnbs[0] == expected_gnb

    def test_given_nms_returns_an_empty_list_when_list_gnbs_then_empty_list_is_returned(self):
        nms_gnbs = []
        self.mock_request.return_value = self.mock_response_with_list(nms_gnbs)

        gnbs = self.nms.list_gnbs()

        assert gnbs == []

    def test_given_multiple_gnbs_in_nms_when_list_gnbs_then_multiple_gnbs_are_returned(self):
        nms_gnbs = [
            {"name": "some.gnb.name", "tac": "111"},
            {"name": "a_gnb_name", "tac": "342"},
            {"name": "other.gnb_name", "tac": "99"},
        ]
        self.mock_request.return_value = self.mock_response_with_list(nms_gnbs)

        gnbs = self.nms.list_gnbs()

        expected_gnbs = [
            GnodeB(name="some.gnb.name", tac=111),
            GnodeB(name="a_gnb_name", tac=342),
            GnodeB(name="other.gnb_name", tac=99),
        ]
        for gnb in expected_gnbs:
            assert gnb in gnbs
        assert len(gnbs) == 3

    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(
                mock_response_with_http_error_exception,
            ),
            pytest.param(
                mock_response_with_connection_error_exception,
            ),
        ],
    )
    def test_given_exception_is_raised_when_create_gnb_then_exception_is_handled(self, exception):
        self.mock_request.side_effect = exception()

        self.nms.create_gnb(name="some.gnb.name", tac=111)

        self.mock_request.assert_called_once_with(
            method="POST",
            url="some_url/config/v1/inventory/gnb/some.gnb.name",
            headers={"Content-Type": "application/json"},
            json={"tac": "111"},
            verify=False,
        )

    def test_given_a_valid_gnb_when_create_gnb_then_gnb_is_added_to_nms(self):
        self.nms.create_gnb(name="some.gnb.name", tac=111)

        self.mock_request.assert_called_once_with(
            method="POST",
            url="some_url/config/v1/inventory/gnb/some.gnb.name",
            headers={"Content-Type": "application/json"},
            json={"tac": "111"},
            verify=False,
        )

    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(
                mock_response_with_http_error_exception,
            ),
            pytest.param(
                mock_response_with_connection_error_exception,
            ),
        ],
    )
    def test_given_exception_is_raised_when_delete_gnb_then_exceptions_is_handled(self, exception):
        self.mock_request.side_effect = exception()

        gnb_name = "some.gnb.name"
        self.nms.delete_gnb(name=gnb_name)

        self.mock_request.assert_called_once_with(
            method="DELETE",
            url="some_url/config/v1/inventory/gnb/some.gnb.name",
            headers={"Content-Type": "application/json"},
            json=None,
            verify=False,
        )

    def test_given_valid_gnb_when_delete_gnb_then_gnb_is_successfully_deleted(self):
        gnb_name = "some.gnb.name"
        self.nms.delete_gnb(name=gnb_name)

        self.mock_request.assert_called_once_with(
            method="DELETE",
            url="some_url/config/v1/inventory/gnb/some.gnb.name",
            headers={"Content-Type": "application/json"},
            json=None,
            verify=False,
        )

    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(
                mock_response_with_http_error_exception,
            ),
            pytest.param(
                mock_response_with_connection_error_exception,
            ),
        ],
    )
    def test_given_exception_is_raised_when_list_upfs_then_an_empty_list_is_returned(
        self, exception
    ):
        self.mock_request.side_effect = exception()

        upfs = self.nms.list_upfs()

        assert upfs == []

    def test_when_list_upfs_then_upf_url_is_used(self):
        nms_upfs = []
        self.mock_request.side_effect = self.mock_response_with_list(nms_upfs)

        self.nms.list_upfs()

        self.mock_request.assert_called_once_with(
            method="GET",
            url="some_url/config/v1/inventory/upf",
            headers={"Content-Type": "application/json"},
            json=None,
            verify=False,
        )

    def test_given_nms_returns_a_upf_list_when_list_upfs_then_a_upf_list_is_returned(self):
        nms_upfs = [{"hostname": "some.host.name", "port": "111"}]
        self.mock_request.return_value = self.mock_response_with_list(nms_upfs)

        upfs = self.nms.list_upfs()

        expected_upf = Upf(hostname="some.host.name", port=111)
        assert len(upfs) == 1
        assert upfs[0] == expected_upf

    def test_given_nms_returns_an_empty_list_when_list_upfs_then_empty_list_is_returned(self):
        nms_upfs = []
        self.mock_request.return_value = self.mock_response_with_list(nms_upfs)

        upfs = self.nms.list_upfs()

        assert upfs == []

    def test_given_multiple_upfs_in_nms_when_list_upfs_then_multiple_upfs_are_returned(self):
        nms_upfs = [
            {"hostname": "some.host.name", "port": "111"},
            {"hostname": "a_host_name", "port": "342"},
            {"hostname": "other.host_name", "port": "99"},
        ]
        self.mock_request.return_value = self.mock_response_with_list(nms_upfs)

        upfs = self.nms.list_upfs()

        expected_upfs = [
            Upf(hostname="some.host.name", port=111),
            Upf(hostname="a_host_name", port=342),
            Upf(hostname="other.host_name", port=99),
        ]
        for upf in expected_upfs:
            assert upf in upfs
        assert len(upfs) == 3

    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(
                mock_response_with_http_error_exception,
            ),
            pytest.param(
                mock_response_with_connection_error_exception,
            ),
        ],
    )
    def test_given_exception_is_raised_when_create_upf_then_exception_is_handled(self, exception):
        self.mock_request.side_effect = exception()

        self.nms.create_upf(hostname="some.upf.name", port=111)

        self.mock_request.assert_called_once_with(
            method="POST",
            url="some_url/config/v1/inventory/upf/some.upf.name",
            headers={"Content-Type": "application/json"},
            json={"port": "111"},
            verify=False,
        )

    def test_given_a_valid_upf_when_create_upf_then_upf_is_added_to_nms(self):
        self.nms.create_upf(hostname="some.upf.name", port=22)

        self.mock_request.assert_called_once_with(
            method="POST",
            url="some_url/config/v1/inventory/upf/some.upf.name",
            headers={"Content-Type": "application/json"},
            json={"port": "22"},
            verify=False,
        )

    @pytest.mark.parametrize(
        "exception",
        [
            pytest.param(
                mock_response_with_http_error_exception,
            ),
            pytest.param(
                mock_response_with_connection_error_exception,
            ),
        ],
    )
    def test_given_exception_is_raised_when_delete_upf_then_exceptions_is_handled(self, exception):
        self.mock_request.side_effect = exception()

        upf_name = "some.upf.name"
        self.nms.delete_upf(hostname=upf_name)

        self.mock_request.assert_called_once_with(
            method="DELETE",
            url="some_url/config/v1/inventory/upf/some.upf.name",
            headers={"Content-Type": "application/json"},
            json=None,
            verify=False,
        )

    def test_given_valid_upf_when_delete_upf_then_upf_is_successfully_deleted(self):
        upf_name = "some.upf.name"

        self.nms.delete_upf(hostname=upf_name)

        self.mock_request.assert_called_once_with(
            method="DELETE",
            url="some_url/config/v1/inventory/upf/some.upf.name",
            headers={"Content-Type": "application/json"},
            json=None,
            verify=False,
        )

    @pytest.mark.parametrize(
        "gnb",
        [
            pytest.param(
                {"tac": "111"},
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
    def test_given_nms_returns_an_invalid_gnb_when_list_gnbs_then_gnb_is_not_returned(self, gnb):
        nms_gnbs = [gnb]
        self.mock_request.return_value = self.mock_response_with_list(nms_gnbs)

        gnbs = self.nms.list_gnbs()

        assert gnbs == []

    @pytest.mark.parametrize(
        "upf",
        [
            pytest.param(
                {"port": "111"},
                id="missing_hostname_parameter",
            ),
            pytest.param(
                {"hostname": "some.host.name"},
                id="missing_port_parameter",
            ),
            pytest.param(
                {"hostname": "some.host.name", "port": "aaa"},
                id="invalid_str_port",
            ),
        ],
    )
    def test_given_nms_returns_an_invalid_upf_when_list_upfs_then_upf_is_not_returned(self, upf):
        nms_upfs = [upf]
        self.mock_request.return_value = self.mock_response_with_list(nms_upfs)

        upfs = self.nms.list_upfs()

        assert upfs == []
