# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the `fiveg_n4` relation.

This library contains the Requires and Provides classes for handling the `fiveg_n4`
interface.

The purpose of this library is to integrate a charm claiming to be able to provide
information required to establish communication over the N4 interface with a charm
claiming to be able to consume this information.

To get started using the library, you need to fetch the library using `charmcraft`.

```shell
cd some-charm
charmcraft fetch-lib charms.sdcore_upf_k8s.v0.fiveg_n4
```

Add the following libraries to the charm's `requirements.txt` file:
- pydantic
- pytest-interface-tester

Charms providing the `fiveg_n4` relation should use `N4Provides`.
Typical usage of this class would look something like:

    ```python
    ...
    from charms.sdcore_upf_k8s.v0.fiveg_n4 import N4Provides
    ...

    class SomeProviderCharm(CharmBase):

        def __init__(self, *args):
            ...
            self.fiveg_n4 = N4Provides(charm=self, relation_name="fiveg_n4")
            ...
            self.framework.observe(self.fiveg_n4.on.fiveg_n4_request, self._on_fiveg_n4_request)

        def _on_fiveg_n4_request(self, event):
            ...
            self.fiveg_n4.publish_upf_n4_information(
                relation_id=event.relation_id,
                upf_hostname=hostname,
                upf_port=n4_port,
            )
    ```

    And a corresponding section in charm's `metadata.yaml`:
    ```
    provides:
        fiveg_n4:  # Relation name
            interface: fiveg_n4  # Relation interface
    ```

Charms that require the `fiveg_n4` relation should use `N4Requires`.
Typical usage of this class would look something like:

    ```python
    ...
    from charms.sdcore_upf_k8s.v0.fiveg_n4 import N4Requires
    ...

    class SomeRequirerCharm(CharmBase):

        def __init__(self, *args):
            ...
            self.fiveg_n4 = N4Requires(charm=self, relation_name="fiveg_n4")
            ...
            self.framework.observe(self.upf.on.fiveg_n4_available, self._on_fiveg_n4_available)

        def _on_fiveg_n4_available(self, event):
            upf_hostname = event.upf_hostname,
            upf_port = event.upf_port,
            # Do something with the UPF's hostname and port
    ```

    And a corresponding section in charm's `metadata.yaml`:
    ```
    requires:
        fiveg_n4:  # Relation name
            interface: fiveg_n4  # Relation interface
    ```
"""

import logging

from interface_tester.schema_base import DataBagSchema  # type: ignore[import]
from ops.charm import CharmBase, CharmEvents, RelationChangedEvent, RelationJoinedEvent
from ops.framework import EventBase, EventSource, Object
from pydantic import BaseModel, Field, ValidationError

# The unique Charmhub library identifier, never change it
LIBID = "6c81534a04904d48966ceb7b4f42a850"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 2

PYDEPS = ["pydantic", "pytest-interface-tester"]


logger = logging.getLogger(__name__)

"""Schemas definition for the provider and requirer sides of the `fiveg_n4` interface.
It exposes two interfaces.schema_base.DataBagSchema subclasses called:
- ProviderSchema
- RequirerSchema
Examples:
    ProviderSchema:
        unit: <empty>
        app: {
            "upf_hostname": "upf.uplane-cloud.canonical.com",
            "upf_port": 8805
        }
    RequirerSchema:
        unit: <empty>
        app:  <empty>
"""


class FivegN4ProviderAppData(BaseModel):
    """Provider app data for fiveg_n4."""

    upf_hostname: str = Field(
        description="Name of the host exposing the UPF's N4 interface.",
        examples=["upf.uplane-cloud.canonical.com"],
    )
    upf_port: int = Field(
        description="Port on which UPF's N4 interface is exposed.",
        examples=[8805],
    )


class ProviderSchema(DataBagSchema):
    """Provider schema for fiveg_n4."""

    app: FivegN4ProviderAppData


def data_matches_provider_schema(data: dict) -> bool:
    """Return whether data matches provider schema.

    Args:
        data (dict): Data to be validated.

    Returns:
        bool: True if data matches provider schema, False otherwise.
    """
    try:
        ProviderSchema(app=data)
        return True
    except ValidationError as e:
        logger.error("Invalid data: %s", e)
        return False


class FiveGN4RequestEvent(EventBase):
    """Dataclass for the `fiveg_n4` request event."""

    def __init__(self, handle, relation_id: int):
        """Set relation id."""
        super().__init__(handle)
        self.relation_id = relation_id

    def snapshot(self) -> dict:
        """Return event data."""
        return {
            "relation_id": self.relation_id,
        }

    def restore(self, snapshot):
        """Restore event data."""
        self.relation_id = snapshot["relation_id"]


class N4ProviderCharmEvents(CharmEvents):
    """Custom events for the N4Provider."""

    fiveg_n4_request = EventSource(FiveGN4RequestEvent)


class N4Provides(Object):
    """Class to be instantiated by provider of the `fiveg_n4`."""

    on = N4ProviderCharmEvents()

    def __init__(self, charm: CharmBase, relation_name: str):
        """Observe relation joined event.

        Args:
            charm: Juju charm
            relation_name (str): Relation name
        """
        self.relation_name = relation_name
        self.charm = charm
        super().__init__(charm, relation_name)
        self.framework.observe(charm.on[relation_name].relation_joined, self._on_relation_joined)

    def publish_upf_n4_information(
        self, relation_id: int, upf_hostname: str, upf_n4_port: int
    ) -> None:
        """Set UPF's hostname and port in the relation data.

        Args:
            relation_id (str): Relation ID
            upf_hostname (str): UPF's hostname
            upf_n4_port (int): Port on which UPF accepts N4 communication
        """
        if not data_matches_provider_schema(
            data={"upf_hostname": upf_hostname, "upf_port": upf_n4_port}
        ):
            raise ValueError(f"Invalid UPF N4 data: {upf_hostname}, {upf_n4_port}")
        relation = self.model.get_relation(
            relation_name=self.relation_name, relation_id=relation_id
        )
        if not relation:
            raise RuntimeError(f"Relation {self.relation_name} not created yet.")
        relation.data[self.charm.app]["upf_hostname"] = upf_hostname
        relation.data[self.charm.app]["upf_port"] = str(upf_n4_port)

    def _on_relation_joined(self, event: RelationJoinedEvent) -> None:
        """Triggered whenever a requirer charm joins the relation.

        Args:
            event (RelationJoinedEvent): Juju event
        """
        self.on.fiveg_n4_request.emit(relation_id=event.relation.id)


class N4AvailableEvent(EventBase):
    """Dataclass for the `fiveg_n4` available event."""

    def __init__(self, handle, upf_hostname: str, upf_port: int):
        """Set UPF's hostname and port."""
        super().__init__(handle)
        self.upf_hostname = upf_hostname
        self.upf_port = upf_port

    def snapshot(self) -> dict:
        """Return event data."""
        return {
            "upf_hostname": self.upf_hostname,
            "upf_port": self.upf_port,
        }

    def restore(self, snapshot):
        """Restores event data."""
        self.upf_hostname = snapshot["upf_hostname"]
        self.upf_port = snapshot["upf_port"]


class N4RequirerCharmEvents(CharmEvents):
    """Custom events for the N4Requirer."""

    fiveg_n4_available = EventSource(N4AvailableEvent)


class N4Requires(Object):
    """Class to be instantiated by requirer of the `fiveg_n4`."""

    on = N4RequirerCharmEvents()

    def __init__(self, charm: CharmBase, relation_name: str):
        """Observe relation joined and relation changed events.

        Args:
            charm: Juju charm
            relation_name (str): Relation name
        """
        self.relation_name = relation_name
        self.charm = charm
        super().__init__(charm, relation_name)
        self.framework.observe(charm.on[relation_name].relation_joined, self._on_relation_changed)
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Triggered every time there's a change in relation data.

        Args:
            event (RelationChangedEvent): Juju event
        """
        relation_data = event.relation.data
        upf_hostname = relation_data[event.app].get("upf_hostname")  # type: ignore[index]
        upf_port = relation_data[event.app].get("upf_port")  # type: ignore[index]
        if upf_hostname and upf_port:
            self.on.fiveg_n4_available.emit(upf_hostname=upf_hostname, upf_port=upf_port)
