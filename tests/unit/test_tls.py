# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import MagicMock, patch

import pytest
from charms.tls_certificates_interface.v4.tls_certificates import Certificate, PrivateKey

from tests.unit.certificates_helpers import example_cert_and_key
from tls import CA_CERTIFICATE_NAME, CERTIFICATE_NAME, PRIVATE_KEY_NAME, Tls

STORAGE_PATH = "test"
CA_CERTIFICATE_PATH = f"{STORAGE_PATH}/{CA_CERTIFICATE_NAME}"
CERTIFICATE_PATH = f"{STORAGE_PATH}/{CERTIFICATE_NAME}"
PRIVATE_KEY_PATH = f"{STORAGE_PATH}/{PRIVATE_KEY_NAME}"


class TestTls:
    patcher_get_assigned_certificate = patch(
        "charms.tls_certificates_interface.v4.tls_certificates.TLSCertificatesRequiresV4.get_assigned_certificate"
    )

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_get_assigned_certificate = TestTls.patcher_get_assigned_certificate.start()
        mock_charm = MagicMock()
        self.mock_container = MagicMock()
        self.tls = Tls(
            charm=mock_charm,
            relation_name="certs",
            container=self.mock_container,
            domain_name="test",
            storage_path=STORAGE_PATH
        )
        request.addfinalizer(self.tearDown)

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    def test_given_get_assigned_certificate_valid_values_then_certificate_is_available_returns_true(self):  # noqa: E501
        mock_cert = MagicMock(spec=Certificate)
        mock_key = MagicMock(spec=PrivateKey)
        self.mock_get_assigned_certificate.return_value = mock_cert, mock_key

        assert self.tls.certificate_is_available() is True

    @pytest.mark.parametrize(
        "certificate, private_key",
        [
            (None, None),
            (None, MagicMock(spec=PrivateKey)),
            (MagicMock(spec=Certificate), None),
        ]
    )
    def test_given_get_assigned_certificate_returns_none_then_certificate_is_available_returns_false(  # noqa: E501
        self, certificate, private_key
    ):
        self.mock_get_assigned_certificate.return_value = certificate, private_key

        assert self.tls.certificate_is_available() is False

    def test_given_certificates_do_not_exist_when_check_and_update_certificate_then_certificates_are_stored(self):  # noqa: E501
        mock_cert, mock_key = example_cert_and_key()
        self.mock_get_assigned_certificate.return_value = mock_cert, mock_key
        self.mock_container.exists.return_value = False

        was_updated = self.tls.check_and_update_certificate()

        assert was_updated is True
        self.mock_container.push.assert_any_call(path=PRIVATE_KEY_PATH, source=str(mock_key))
        self.mock_container.push.assert_any_call(
            path=CERTIFICATE_PATH,
            source=str(mock_cert.certificate)
        )
        self.mock_container.push.assert_any_call(
            path=CA_CERTIFICATE_PATH,
            source=str(mock_cert.ca)
        )

    def test_given_certificate_private_key_and_ca_certificate_exist_when_clean_up_certificates_then_certificates_are_removed(self):  # noqa: E501
        self.mock_container.exists.return_value = True

        self.tls.clean_up_certificates()

        self.mock_container.remove_path.assert_any_call(path=CERTIFICATE_PATH)
        self.mock_container.remove_path.assert_any_call(path=PRIVATE_KEY_PATH)
        self.mock_container.remove_path.assert_any_call(path=CA_CERTIFICATE_PATH)

    def test_given_certificate_private_key_and_ca_certificate_do_not_exist_when_clean_up_certificates_then_certificates_are_removed(self):  # noqa: E501
        self.mock_container.exists.return_value = False

        self.tls.clean_up_certificates()

        self.mock_container.remove_path.assert_not_called()
