# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from unittest.mock import patch

import pytest
import scenario

from charm import SDCoreNMSOperatorCharm


class NMSUnitTestFixtures:
    patcher_check_output = patch("charm.check_output")
    patcher_set_webui_url_in_all_relations = patch(
        "charms.sdcore_nms_k8s.v0.sdcore_config.SdcoreConfigProvides.set_webui_url_in_all_relations"
    )
    patcher_nms_list_gnbs = patch("nms.NMS.list_gnbs")
    patcher_nms_create_gnb = patch("nms.NMS.create_gnb")
    patcher_nms_delete_gnb = patch("nms.NMS.delete_gnb")
    patcher_nms_list_upfs = patch("nms.NMS.list_upfs")
    patcher_nms_create_upf = patch("nms.NMS.create_upf")
    patcher_nms_delete_upf = patch("nms.NMS.delete_upf")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_check_output = NMSUnitTestFixtures.patcher_check_output.start()
        self.mock_set_webui_url_in_all_relations = (
            NMSUnitTestFixtures.patcher_set_webui_url_in_all_relations.start()
        )
        self.mock_list_gnbs = NMSUnitTestFixtures.patcher_nms_list_gnbs.start()
        self.mock_create_gnb = NMSUnitTestFixtures.patcher_nms_create_gnb.start()
        self.mock_delete_gnb = NMSUnitTestFixtures.patcher_nms_delete_gnb.start()
        self.mock_list_upfs = NMSUnitTestFixtures.patcher_nms_list_upfs.start()
        self.mock_create_upf = NMSUnitTestFixtures.patcher_nms_create_upf.start()
        self.mock_delete_upf = NMSUnitTestFixtures.patcher_nms_delete_upf.start()
        yield
        request.addfinalizer(self.tearDown)

    @staticmethod
    def tearDown() -> None:
        patch.stopall()

    @pytest.fixture(autouse=True)
    def context(self):
        self.ctx = scenario.Context(
            charm_type=SDCoreNMSOperatorCharm,
        )
