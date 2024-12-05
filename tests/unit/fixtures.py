# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch

import pytest
import scenario

from charm import SDCoreNMSOperatorCharm


class BaseNMSUnitTestFixtures:
    patcher_check_output = patch("charm.check_output")
    patcher_set_webui_url_in_all_relations = patch(
        "charms.sdcore_nms_k8s.v0.sdcore_config.SdcoreConfigProvides.set_webui_url_in_all_relations"
    )
    patcher_nms_login = patch("nms.NMS.login")
    patcher_nms_token_is_valid = patch("nms.NMS.token_is_valid")
    patcher_nms_is_api_available = patch("nms.NMS.is_api_available")
    patcher_nms_is_initialized = patch("nms.NMS.is_initialized")
    patcher_nms_create_first_user = patch("nms.NMS.create_first_user")
    patcher_nms_list_network_slices = patch("nms.NMS.list_network_slices")
    patcher_nms_get_network_slice = patch("nms.NMS.get_network_slice")
    patcher_nms_list_gnbs = patch("nms.NMS.list_gnbs")
    patcher_nms_create_gnb = patch("nms.NMS.create_gnb")
    patcher_nms_delete_gnb = patch("nms.NMS.delete_gnb")
    patcher_nms_list_upfs = patch("nms.NMS.list_upfs")
    patcher_nms_create_upf = patch("nms.NMS.create_upf")
    patcher_nms_delete_upf = patch("nms.NMS.delete_upf")

    def common_setup(self):
        self.mock_check_output = BaseNMSUnitTestFixtures.patcher_check_output.start()
        self.mock_set_webui_url_in_all_relations = (
            BaseNMSUnitTestFixtures.patcher_set_webui_url_in_all_relations.start()
        )
        self.mock_nms_login = NMSUnitTestFixtures.patcher_nms_login.start()
        self.mock_nms_token_is_valid = NMSUnitTestFixtures.patcher_nms_token_is_valid.start()
        self.mock_is_api_available = NMSUnitTestFixtures.patcher_nms_is_api_available.start()
        self.mock_is_initialized = NMSUnitTestFixtures.patcher_nms_is_initialized.start()
        self.mock_create_first_user = NMSUnitTestFixtures.patcher_nms_create_first_user.start()
        self.mock_list_network_slices = NMSUnitTestFixtures.patcher_nms_list_network_slices.start()
        self.mock_get_network_slice = NMSUnitTestFixtures.patcher_nms_get_network_slice.start()
        self.mock_list_gnbs = NMSUnitTestFixtures.patcher_nms_list_gnbs.start()
        self.mock_create_gnb = NMSUnitTestFixtures.patcher_nms_create_gnb.start()
        self.mock_delete_gnb = NMSUnitTestFixtures.patcher_nms_delete_gnb.start()
        self.mock_list_upfs = NMSUnitTestFixtures.patcher_nms_list_upfs.start()
        self.mock_create_upf = NMSUnitTestFixtures.patcher_nms_create_upf.start()
        self.mock_delete_upf = NMSUnitTestFixtures.patcher_nms_delete_upf.start()

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = scenario.Context(
            charm_type=SDCoreNMSOperatorCharm,
        )


class NMSUnitTestFixtures(BaseNMSUnitTestFixtures):
    patcher_certificate_is_available = patch("tls.Tls.certificate_is_available")
    patcher_check_and_update_certificate = patch("tls.Tls.check_and_update_certificate")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.common_setup()
        self.mock_certificate_is_available = (
            NMSUnitTestFixtures.patcher_certificate_is_available.start()
        )
        self.mock_check_and_update_certificate = (
            NMSUnitTestFixtures.patcher_check_and_update_certificate.start()
        )
        yield
        request.addfinalizer(self.tearDown)


class NMSTlsCertificatesFixtures(BaseNMSUnitTestFixtures):
    patcher_get_assigned_certificate = patch(
        "charms.tls_certificates_interface.v4.tls_certificates.TLSCertificatesRequiresV4.get_assigned_certificate"
    )

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.common_setup()
        self.mock_get_assigned_certificate = (
            NMSTlsCertificatesFixtures.patcher_get_assigned_certificate.start()
        )
        yield
        request.addfinalizer(self.tearDown)
