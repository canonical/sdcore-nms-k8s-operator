import tempfile
from unittest.mock import patch

import pytest
import scenario
from interface_tester import InterfaceTester
from ops.pebble import Layer, ServiceStatus

from charm import SDCoreNMSOperatorCharm


@pytest.fixture
def interface_tester(interface_tester: InterfaceTester):

    with tempfile.TemporaryDirectory() as tempdir:
        with patch("charm.check_output"):
            auth_database_relation = scenario.Relation(
                endpoint="auth_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "apple",
                    "password": "hamburger",
                    "uris": "1.2.3.4:1234",
                },
            )
            common_database_relation = scenario.Relation(
                endpoint="common_database",
                interface="mongodb_client",
                remote_app_data={
                    "username": "banana",
                    "password": "pizza",
                    "uris": "1.1.1.1:1234",
                },
            )
            config_mount = scenario.Mount(
                location="/nms/config",
                src=tempdir,
            )
            container = scenario.Container(
                name="nms",
                can_connect=True,
                mounts={"config": config_mount},
                layers={"nms": Layer({"services": {"nms": {}}})},
                service_status={"nms": ServiceStatus.ACTIVE},
            )

            #with open(f"{tempdir}/webuicfg.conf", "w") as f:
            #    f.write("whatever config file content")

            #state_out = self.ctx.run("collect_unit_status", state_in)

            #assert state_out.unit_status == ActiveStatus()

            interface_tester.configure(
                charm_type=SDCoreNMSOperatorCharm,
                state_template=scenario.State(
                    leader=True,
                    relations=[auth_database_relation, common_database_relation],
                    containers=[container],
                ),
            )
            yield interface_tester
