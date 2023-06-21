#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charmed operator for the SD-Core GUI service."""

import logging

from ops.charm import CharmBase
from ops.main import main

logger = logging.getLogger(__name__)


class SDCoreGUIOperatorCharm(CharmBase):
    """Main class to describe juju event handling for the SD-Core GUI operator."""

    def __init__(self, *args):
        super().__init__(*args)


if __name__ == "__main__":  # pragma: no cover
    main(SDCoreGUIOperatorCharm)
