#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle NMS API calls."""

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, List

import requests

logger = logging.getLogger(__name__)

GNB_CONFIG_URL = "config/v1/inventory/gnb"
UPF_CONFIG_URL = "config/v1/inventory/upf"

JSON_HEADER = {"Content-Type": "application/json"}


@dataclass
class GnodeB:
    """Class to represent a gNB."""

    name: str
    tac: int


@dataclass
class Upf:
    """Class to represent a UPF."""

    hostname: str
    port: int


@dataclass
class CreateGnbParams:
    """Parameters to create a gNB."""

    tac: int


@dataclass
class CreateUPFParams:
    """Parameters to create a UPF."""

    port: int


class NMS:
    """Handle NMS API calls."""

    def __init__(self, url: str):
        self.url = url

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: any = None,  # type: ignore[reportGeneralTypeIssues]
    ) -> Any | None:
        """Make an HTTP request and handle common error patterns."""
        headers = JSON_HEADER
        url = f"{self.url}{endpoint}"
        logger.info("Request: %s %s", method, url)
        try:
            req = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
            )
        except requests.RequestException as e:
            logger.error("HTTP request failed: %s", e)
            return None
        except OSError as e:
            logger.error("couldn't complete HTTP request: %s", e)
            return None
        try:
            req.raise_for_status()
        except requests.HTTPError:
            logger.error(
                "Request failed: code %s",
                req.status_code,
            )
            return None
        try:
            response = req.json()
        except json.JSONDecodeError:
            return None
        logger.info("Response: %s", response)
        return response

    def list_gnbs(self) -> List[GnodeB]:
        """List gNBs from the NMS inventory."""
        response = self._make_request("GET", f"/{GNB_CONFIG_URL}")
        if not response:
            return []
        gnb_list = []
        for item in response:
            try:
                gnb_list.append(GnodeB(name=item["name"], tac=int(item["tac"])))
            except (ValueError, KeyError):
                logger.error("invalid gNB data: %s", item)
        return gnb_list

    def create_gnb(self, name: str, tac: int) -> None:
        """Create a gNB in the NMS inventory."""
        create_gnb_params = CreateGnbParams(tac=tac)
        self._make_request("POST", f"/{GNB_CONFIG_URL}/{name}", data=asdict(create_gnb_params))
        logger.info("gNB %s created in NMS", name)

    def delete_gnb(self, name: str) -> None:
        """Delete a gNB list from the NMS inventory."""
        self._make_request("DELETE", f"/{GNB_CONFIG_URL}/{name}")
        logger.info("UPF %s deleted from NMS", name)

    def list_upfs(self) -> List[Upf]:
        """List UPFs from the NMS inventory."""
        response = self._make_request("GET", f"/{UPF_CONFIG_URL}")
        if not response:
            return []
        upf_list = []
        for item in response:
            try:
                upf_list.append(Upf(hostname=item["hostname"], port=int(item["port"])))
            except (ValueError, KeyError):
                logger.error("invalid UPF data: %s", item)
        return upf_list

    def create_upf(self, hostname: str, port: int) -> None:
        """Create a UPF in the NMS inventory."""
        create_upf_params = CreateUPFParams(port=port)
        self._make_request("POST", f"/{UPF_CONFIG_URL}/{hostname}", data=asdict(create_upf_params))
        logger.info("UPF %s created in NMS", hostname)

    def delete_upf(self, hostname: str) -> None:
        """Delete a UPF list from the NMS inventory."""
        self._make_request("DELETE", f"/{UPF_CONFIG_URL}/{hostname}")
        logger.info("UPF %s deleted from NMS", hostname)
