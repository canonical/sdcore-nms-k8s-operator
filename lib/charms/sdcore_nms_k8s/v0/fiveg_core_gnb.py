# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the `fiveg_core_gnb` relation.

This library contains the Requires and Provides classes for handling the `fiveg_core_gnb`
interface.

The purpose of this library is to provide a way for a 5G core to provide network information and
configuration to CUs/gNodeBs.

To get started using the library, you need to fetch the library using `charmcraft`.

```shell
cd some-charm
charmcraft fetch-lib charms.sdcore_nms_k8s.v0.fiveg_core_gnb
```

Add the following libraries to the charm's `requirements.txt` file:
- pydantic
- pytest-interface-tester

Charms providing the `fiveg_core_gnb` relation should use `FivegCoreGnbProvides`.
The class `PLMNConfig` represents the configuration of a PLMN for the CU/gNodeB. It is composed by
the Mobile Country Code (MCC), the Mobile Network Code (MNC), the Slice Service Type (SST) and the
Slice Differentiator (SD). Each CU can be configured with a single Tracking Area Code (TAC) and
multiple PLMNS.

Typical usage of this class would look something like:

    ```python
    ...
    from charms.sdcore_gnbsim_k8s.v0.fiveg_core_gnb import FivegCoreGnbProvides, PLMNConfig
    ...

    class SomeProviderCharm(CharmBase):

        def __init__(self, *args):
            ...
            self.fiveg_core_gnb_provider = FivegCoreGnbProvides(
                charm=self,
                relation_name="fiveg_core_gnb"
                )
            ...
            self.framework.observe(
                self.fiveg_core_gnb_provider.on.gnb_available,
                self._on_gnb_available
            )

        def _on_gnb_available(self, event):
            ...
            # implement the logic to populate the list of PLMNs.
            plmns = [PLMNConfig(mcc=..., mnc=..., sst=..., sd=...)
            self.fiveg_core_gnb_provider.publish_fiveg_core_gnb_information(
                relation_id=event.relation_id,
                tac=tac,
                plmns=plmns,
            )
    ```

    And a corresponding section in charm's `charmcraft.yaml`:
    ```
    provides:
        fiveg_core_gnb:  # Relation name
            interface: fiveg_core_gnb  # Relation interface
    ```

Charms that require the `fiveg_core_gnb` relation should use `FivegCoreGnbRequires`.
Typical usage of this class would look something like:

    ```python
    ...
    from charms.sdcore_nms_k8s.v0.fiveg_core_gnb import FivegCoreGnbRequires
    ...

    class SomeRequirerCharm(CharmBase):

        def __init__(self, *args):
            ...
            self.fiveg_core_gnb = FivegCoreGnbRequires(
                charm=self,
                relation_name="fiveg_core_gnb"
            )
            ...
            self.framework.observe(self.fiveg_core_gnb.on.gnb_config_available,
                self._on_gnb_config_available)

        def _on_gnb_config_available(self, event):
            tac = event.tac,
            plmns = event.plmns,
            # Do something with the TAC and PLMNs.
    ```

    And a corresponding section in charm's `charmcraft.yaml`:
    ```
    requires:
        fiveg_core_gnb:  # Relation name
            interface: fiveg_core_gnb  # Relation interface
    ```
"""

import json
import logging
from dataclasses import dataclass

from interface_tester.schema_base import DataBagSchema
from ops.charm import CharmBase, CharmEvents, RelationChangedEvent
from ops.framework import EventBase, EventSource, Handle, Object
from pydantic import BaseModel, Field, ValidationError

# The unique Charmhub library identifier, never change it
LIBID = "196ff8f539ba4f2998209fbb50e2dbbf"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

logger = logging.getLogger(__name__)

"""Schemas definition for the provider and requirer sides of the `fiveg_core_gnb` interface.
It exposes two interfaces.schema_base.DataBagSchema subclasses called:
- ProviderSchema
- RequirerSchema

Examples:
    ProviderSchema:
        unit: <empty>
        app: {
            "tac": 1,
            "plmns": [
                {
                    "mcc": "001",
                    "mnc": "01",
                    "sst": 1,
                    "sd": 1,
                }
            ],
        }
    RequirerSchema:
        unit: <empty>
        app: {
            "cu_name": "gnb001",
        }
"""


@dataclass
class PLMNConfig:
    """Dataclass representing the configuration for a PLMN."""

    mcc: str = Field(
        description="Mobile Country Code",
        examples=["001", "208", "302"],
        pattern=r"[0-9][0-9][0-9]",
    )
    mnc: str = Field(
        description="Mobile Network Code",
        examples=["01", "001", "999"],
        pattern=r"[0-9][0-9][0-9]?",
    )
    sst: int = Field(
        description="Slice/Service Type",
        examples=[1, 2, 3, 4],
        ge=0,
        le=255,
    )
    sd: int = Field(
        description="Slice Differentiator",
        examples=[1],
        ge=0,
        le=16777215,
    )


class FivegCoreGnbProviderAppData(BaseModel):
    """Provider application data for fiveg_core_gnb."""
    tac: int = Field(
        description="Tracking Area Code",
        examples=[1],
        ge=1,
        le=16777215,
    )
    plmn: list[PLMNConfig]


class ProviderSchema(DataBagSchema):
    """Provider schema for fiveg_core_gnb."""

    app_data: FivegCoreGnbProviderAppData


def data_matches_provider_schema(data: dict) -> bool:
    """Return whether data matches provider schema.

    Args:
        data (dict): Data to be validated.

    Returns:
        bool: True if data matches provider schema, False otherwise.
    """
    try:
        ProviderSchema(app_data=FivegCoreGnbProviderAppData(**data))
        return True
    except ValidationError as e:
        logger.error("Invalid data: %s", e)
        return False


class GnbAvailableEvent(EventBase):
    """Dataclass for the `fiveg_core_gnb` request event."""

    def __init__(self, handle: Handle, relation_id: int, cu_name: str):
        """Set relation id.

        Args:
            handle (Handle): Juju framework handle.
            relation_id (int): ID of the relation.
            cu_name (str): name of the CU/gNodeB.
        """
        super().__init__(handle)
        self.relation_id = relation_id
        self.cu_name = cu_name

    def snapshot(self) -> dict:
        """Return event data.

        Returns:
            (dict): contains the relation ID.
        """
        return {
            "relation_id": self.relation_id,
            "cu_name": self.cu_name,
        }

    def restore(self, snapshot: dict) -> None:
        """Restore event data.

        Args:
            snapshot (dict): contains information to be restored.
        """
        self.relation_id = snapshot["relation_id"]
        self.cu_name = snapshot["cu_name"]


class FivegCoreGnbProviderCharmEvents(CharmEvents):
    """Custom events for the FivegCoreGnbProvider."""

    gnb_available = EventSource(GnbAvailableEvent)


class FivegCoreGnbProvides(Object):
    """Class to be instantiated by provider of the `fiveg_core_gnb`."""

    on = FivegCoreGnbProviderCharmEvents()  # type: ignore

    def __init__(self, charm: CharmBase, relation_name: str):
        """Observe relation joined event.

        Args:
            charm: Juju charm
            relation_name (str): Relation name
        """
        self.relation_name = relation_name
        self.charm = charm
        super().__init__(charm, relation_name)
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def publish_fiveg_core_gnb_information(
        self, relation_id: int, tac: int, plmns: list[PLMNConfig]
    ) -> None:
        """Set TAC and PLMNs in the relation data.

        Args:
            relation_id (str): Relation ID.
            tac (int): Tracking Area Code.
            plmns (list[PLMNConfig]): Configured PLMNs.
        """
        if not data_matches_provider_schema(
            data={"tac": tac, "plmns": plmns}
        ):
            raise ValueError(f"Invalid fiveG core gNB data: {tac}, {plmns}")
        relation = self.model.get_relation(
            relation_name=self.relation_name, relation_id=relation_id
        )
        if not relation:
            raise RuntimeError(f"Relation {self.relation_name} not created yet.")
        relation.data[self.charm.app].update({"tac": str(tac), "plmns": json.dumps(plmns)})

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Triggered every time there's a change in relation data.

        Args:
            event (RelationChangedEvent): Juju event
        """
        relation_data = event.relation.data
        cu_name = relation_data[event.app].get("cu_name")
        if cu_name:
            self.on.gnb_available.emit(relation_id=event.relation.id, cu_name=cu_name)


class GnbConfigAvailableEvent(EventBase):
    """Dataclass for the `fiveg_core_gnb` available event."""

    def __init__(self, handle: Handle, tac: str, plmns: list[PLMNConfig]):
        """Set CU / gNodeB's TAC and PLMNs."""
        super().__init__(handle)
        self.tac = tac
        self.plmns = plmns

    def snapshot(self) -> dict:
        """Return event data."""
        return {
            "tac": self.tac,
            "plmns": self.plmns,
        }

    def restore(self, snapshot: dict) -> None:
        """Restore event data.

        Args:
            snapshot (dict): contains information to be restored.
        """
        self.tac = snapshot["tac"]
        self.plmns = snapshot["plmns"]


class FivegCoreGnbRequirerAppData(BaseModel):
    """Requirer application data for fiveg_core_gnb."""
    cu_name: str = Field(
        description="CU/gNB unique identifier",
        examples=["gnb001"],
    )


class RequirerSchema(DataBagSchema):
    """Requirer schema for fiveg_core_gnb."""

    app_data: FivegCoreGnbRequirerAppData


def data_matches_requirer_schema(data: dict) -> bool:
    """Return whether data matches requirer schema.

    Args:
        data (dict): Data to be validated.

    Returns:
        bool: True if data matches requirer schema, False otherwise.
    """
    try:
        RequirerSchema(app_data=FivegCoreGnbRequirerAppData(**data))
        return True
    except ValidationError as e:
        logger.error("Invalid data: %s", e)
        return False


class FivegCoreGnbRequirerCharmEvents(CharmEvents):
    """Custom events for the FivegCoreGnbRequirer."""

    gnb_config_available = EventSource(GnbConfigAvailableEvent)


class FivegCoreGnbRequires(Object):
    """Class to be instantiated by requirer of the `fiveg_core_gnb`."""

    on = FivegCoreGnbRequirerCharmEvents()  # type: ignore

    def __init__(self, charm: CharmBase, relation_name: str, cu_name: str):
        """Observes relation joined and relation changed events.

        Args:
            charm: Juju charm
            relation_name (str): Relation name
            cu_name (str): name of the CU/gNodeB
        """
        self.relation_name = relation_name
        self.cu_name = cu_name
        self.charm = charm
        super().__init__(charm, relation_name)
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def publish_gnb_information(
        self, relation_id: int, cu_name: str
    ) -> None:
        """Set CU/gNB identifier in the relation data.

        Args:
            relation_id (str): Relation ID.
            cu_name (str): CU/gNB unique identifier.
        """
        if not data_matches_requirer_schema(
            data={"cu_name": cu_name}
        ):
            raise ValueError(f"Invalid fiveG core gNB data: {cu_name}")
        relation = self.model.get_relation(
            relation_name=self.relation_name, relation_id=relation_id
        )
        if not relation:
            raise RuntimeError(f"Relation {self.relation_name} not created yet.")
        relation.data[self.charm.app]["cu_name"] = cu_name

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Triggered every time there's a change in relation data.

        Args:
            event (RelationChangedEvent): Juju event
        """
        relation_data = event.relation.data
        tac = relation_data[event.app].get("tac")
        plmns = relation_data[event.app].get("plmns")
        if tac and plmns:
            self.on.gnb_config_available.emit(tac=tac, plmns=plmns)