# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.


"""Library for the `sdcore_management` relation.

This library contains the Requires and Provides classes for handling the `sdcore_management`
interface.

The purpose of this library is to relate charms claiming
to be able to provide or consume the information to access the configuration service in SD-Core.

## Getting Started
From a charm directory, fetch the library using `charmcraft`:

```shell
charmcraft fetch-lib charms.sdcore_webui_k8s.v0.sdcore_management
```

Add the following libraries to the charm's `requirements.txt` file:
- pydantic
- pytest-interface-tester

### Requirer charm
The requirer charm is the one requiring the address to connect to configuration service.

Example:
```python

from ops.charm import CharmBase
from ops.main import main

from charms.sdcore_webui_k8s.v0.sdcore_management import (
    ManagementUrlAvailable,
    SdcoreManagementRequires,
)

logger = logging.getLogger(__name__)


class DummySdcoreManagementRequiresCharm(CharmBase):

    def __init__(self, *args):
        super().__init__(*args)
        self.sdcore_management = SdcoreManagementRequires(self, "sdcore-management")
        self.framework.observe(
            self.sdcore_management.on.management_url_available,
            self._on_management_url_available,
        )

    def _on_management_url_available(self, event: ManagementUrlAvailable):
        management_url = event.management_url
        <do something with the url>


if __name__ == "__main__":
    main(DummySdcoreManagementRequiresCharm)
```

### Provider charm
The provider charm is the one providing the address to connect to configuration service.

Example:
```python

from ops.charm import CharmBase, RelationJoinedEvent
from ops.main import main

from charms.sdcore_webui_k8s.v0.sdcore_management import (
    SdcoreManagementProvides,
)

class DummySdcoreManagementProvidesCharm(CharmBase):
    management_url = "http://1.2.3.4:1234"

    def __init__(self, *args):
        super().__init__(*args)
        self.sdcore_management = SdcoreManagementProvides(
            self, "sdcore-management"
        )
        self.framework.observe(
            self.on.sdcore_management_relation_joined, self._on_sdcore_management_relation_joined
        )

    def _on_sdcore_management_relation_joined(self, event: RelationJoinedEvent):
        if self.unit.is_leader():
            self.sdcore_management.set_management_url(
                management_url=self.management_url,
            )


if __name__ == "__main__":
    main(DummySdcoreManagementProvidesCharm)
```

"""

import logging
from typing import Dict, Optional

from interface_tester.schema_base import DataBagSchema  # type: ignore[import]
from ops.charm import CharmBase, CharmEvents, RelationChangedEvent
from ops.framework import EventBase, EventSource, Handle, Object
from ops.model import Relation
from pydantic import BaseModel, Field, HttpUrl, ValidationError

# The unique Charmhub library identifier, never change it
LIBID = "46698369ff444f10a4e86984c078ee82"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1

logger = logging.getLogger(__name__)
"""Schemas definition for the provider and requirer sides of the `sdcore_management` interface.
It exposes two interfaces.schema_base.DataBagSchema subclasses called:
- ProviderSchema
- RequirerSchema
Examples:
    ProviderSchema:
        unit: <empty>
        app: {
            "management_url": "http://1.2.3.4:1234",
        }
    RequirerSchema:
        unit: <empty>
        app:  <empty>
"""


class SdcoreManagementProviderAppData(BaseModel):
    """Provider app data for sdcore_management."""

    management_url: HttpUrl = Field(
        description="The endpoint to use to manage SD-Core network.",
        examples=["http://1.2.3.4:1234"]
    )

class ProviderSchema(DataBagSchema):
    """Provider schema for sdcore_management."""

    app: SdcoreManagementProviderAppData


def data_is_valid(data: dict) -> bool:
    """Returns whether data is valid.

    Args:
        data (dict): Data to be validated.

    Returns:
        bool: True if data is valid, False otherwise.
    """
    try:
        ProviderSchema(app=data)
        return True
    except ValidationError as e:
        logger.error("Invalid data: %s", e)
        return False


class ManagementUrlAvailable(EventBase):
    """Charm event emitted when the management url is available."""

    def __init__(self, handle: Handle, management_url: str):
        """Init."""
        super().__init__(handle)
        self.management_url = management_url

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "management_url": self.management_url,
        }

    def restore(self, snapshot: dict) -> None:
        """Restores snapshot."""
        self.management_url = snapshot["management_url"]


class SdcoreManagementRequirerCharmEvents(CharmEvents):
    """List of events that the SD-Core management requirer charm can leverage."""

    management_url_available = EventSource(ManagementUrlAvailable)


class SdcoreManagementRequires(Object):
    """Class to be instantiated by the SD-Core management requirer charm."""

    on = SdcoreManagementRequirerCharmEvents()

    def __init__(self, charm: CharmBase, relation_name: str):
        """Init."""
        super().__init__(charm, relation_name)
        self.charm = charm
        self.relation_name = relation_name
        self.framework.observe(charm.on[relation_name].relation_changed, self._on_relation_changed)

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handler triggered on relation changed event.

        Args:
            event (RelationChangedEvent): Juju event.

        Returns:
            None
        """
        if remote_app_relation_data := self._get_remote_app_relation_data(event.relation):
            self.on.management_url_available.emit(
                management_url=remote_app_relation_data["management_url"],
            )

    @property
    def management_url(self) -> Optional[str]:
        """Returns the address of the management endpoint.

        Returns:
            str: Endpoint address.
        """
        if remote_app_relation_data := self._get_remote_app_relation_data():
            return remote_app_relation_data.get("management_url")
        return None

    def _get_remote_app_relation_data(
        self, relation: Optional[Relation] = None
    ) -> Optional[Dict[str, str]]:
        """Get relation data for the remote application.

        Args:
            Relation: Juju relation object (optional).

        Returns:
            Dict: Relation data for the remote application
            or None if the relation data is invalid.
        """
        relation = relation or self.model.get_relation(self.relation_name)
        if not relation:
            logger.error("No relation: %s", self.relation_name)
            return None
        if not relation.app:
            logger.warning("No remote application in relation: %s", self.relation_name)
            return None
        remote_app_relation_data = dict(relation.data[relation.app])
        if not data_is_valid(remote_app_relation_data):
            logger.error("Invalid relation data: %s", remote_app_relation_data)
            return None
        return remote_app_relation_data


class SdcoreManagementProvides(Object):
    """Class to be instantiated by the charm providing the SD-Core management url."""

    def __init__(self, charm: CharmBase, relation_name: str):
        """Init."""
        super().__init__(charm, relation_name)
        self.relation_name = relation_name
        self.charm = charm

    def set_management_url(self, management_url: str) -> None:
        """Sets the address of the management endpoint.

        Args:
            management_url (str): Configuration service address.

        Returns:
            None
        """
        if not self.charm.unit.is_leader():
            raise RuntimeError("Unit must be leader to set application relation data.")
        relations = self.model.relations[self.relation_name]
        if not relations:
            raise RuntimeError(f"Relation {self.relation_name} not created yet.")
        if not data_is_valid(
            {"management_url": management_url}
        ):
            raise ValueError("Invalid relation data")
        for relation in relations:
            relation.data[self.charm.app].update(
                {
                    "management_url": management_url
                }
            )
