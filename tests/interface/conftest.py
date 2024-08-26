import pytest
from interface_tester import InterfaceTester
from scenario.state import State

from charm import SDCoreNMSOperatorCharm


@pytest.fixture
def interface_tester(interface_tester: InterfaceTester):
    interface_tester.configure(
        charm_type=SDCoreNMSOperatorCharm,
        state_template=State(
            leader=True,
        ),
    )
    yield interface_tester
