# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from interface_tester import InterfaceTester


def test_sdcore_config_v0_interface(interface_tester: InterfaceTester):
    interface_tester.configure(
        interface_name="sdcore_config",
    )
    interface_tester.run()
