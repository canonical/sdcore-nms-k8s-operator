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
    patcher_webui_get_gnbs = patch("webui.Webui.get_gnbs")
    patcher_webui_add_gnb = patch("webui.Webui.add_gnb")
    patcher_webui_delete_gnb = patch("webui.Webui.delete_gnb")
    patcher_webui_get_upfs = patch("webui.Webui.get_upfs")
    patcher_webui_add_upf = patch("webui.Webui.add_upf")
    patcher_webui_delete_upf = patch("webui.Webui.delete_upf")
    patcher_webui_set_url = patch("webui.Webui.set_url")

    @pytest.fixture(autouse=True)
    def setUp(self, request):
        self.mock_check_output = NMSUnitTestFixtures.patcher_check_output.start()
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
