#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle webui API calls."""

import logging
from dataclasses import dataclass
from typing import Dict, List

import requests  # type: ignore[import]

logger = logging.getLogger(__name__)

GNB_CONFIG_URL = "config/v1/inventory/gnb"
UPF_CONFIG_URL = "config/v1/inventory/upf"
JSON_HEADER = {'Content-Type': 'application/json'}


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

class Webui:
    """Handle webui API calls."""
    def __init__(self, url: str):
        self.url = url

    def set_url(self, new_url: str) -> None:
        """Set a new URL for the Webui instance."""
        self.url = new_url

    def get_gnbs(self) -> List[GnodeB]:
        """Get a gNB list from the webui inventory."""
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}"
        json_gnb_list = self._get_resources_from_inventory(inventory_url)
        return self._transform_response_to_gnb(json_gnb_list)

    def add_gnb(self, gnb: GnodeB) -> None:
        """Add a gNB list to the webui inventory."""
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}/{gnb.name}"
        data = {"tac": str(gnb.tac)}
        self._add_resource_to_inventory(inventory_url, gnb.name, data)

    def delete_gnb(self, gnb_name: str) -> None:
        """Delete a gNB list from the webui inventory."""
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}/{gnb_name}"
        self._delete_resource_from_inventory(inventory_url, gnb_name)

    def get_upfs(self) -> List[Upf]:
        """Get a UPF list from the webui inventory."""
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}"
        json_upf_list = self._get_resources_from_inventory(inventory_url)
        return self._transform_response_to_upf(json_upf_list)

    def add_upf(self, upf: Upf) -> None:
        """Add a UPF list to the webui inventory."""
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}/{upf.hostname}"
        data = {"port": str(upf.port)}
        self._add_resource_to_inventory(inventory_url, upf.hostname, data)

    def delete_upf(self, upf_hostname: str) -> None:
        """Delete a UPF list from the webui inventory."""
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}/{upf_hostname}"
        self._delete_resource_from_inventory(inventory_url, upf_hostname)

    def _get_resources_from_inventory(self, inventory_url: str) -> List[Dict]:
        response = requests.get(inventory_url)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.error("Failed to get resource from inventory: %s", e)
            return []
        resources = response.json()
        logger.info("Got %s from inventory", resources)
        return resources

    def _add_resource_to_inventory(self, url: str, resource_name: str, data: dict) -> None:
        response = requests.post(url, headers=JSON_HEADER, json=data)
        try:
            response.raise_for_status()
        except Exception as e:
            logger.error("Failed to add %s to webui: %s", resource_name, e)
            return
        logger.info("%s added to webui", resource_name)

    def _delete_resource_from_inventory(self, inventory_url: str, resource_name: str) -> None:
        response = requests.delete(inventory_url)
        try:
            response.raise_for_status()
        except Exception as e:
            logger.error("Failed to remove %s from webui: %s", resource_name, e)
            return
        logger.info("%s removed from webui", resource_name)

    @staticmethod
    def _transform_response_to_gnb(json_data: List[Dict]) -> List[GnodeB]:
        gnb_list = []
        for item in json_data:
            try:
                gnb_list.append(GnodeB(name=item["name"], tac=int(item["tac"])))
            except (ValueError, KeyError):
                logger.error("invalid gnB %s", item)
        return gnb_list

    @staticmethod
    def _transform_response_to_upf(json_data: List[Dict]) -> List[Upf]:
        upf_list = []
        for item in json_data:
            try:
                upf_list.append(Upf(hostname=item["hostname"], port=int(item["port"])))
            except (ValueError, KeyError):
                logger.error("invalid UPF %s", item)
        return upf_list
