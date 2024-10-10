#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle NMS API calls."""

import logging
from dataclasses import dataclass
from typing import Dict, List

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


class NMS:
    """Handle NMS API calls."""

    def __init__(self, url: str):
        self.url = url

    def list_gnbs(self) -> List[GnodeB]:
        """List gNBs from the NMS inventory."""
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}"
        json_gnb_list = self._get_resources_from_inventory(inventory_url)
        return self._transform_response_to_gnb(json_gnb_list)

    def create_gnb(self, name: str, tac: int) -> None:
        """Create a gNB in the NMS inventory."""
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}/{name}"
        data = {"tac": str(tac)}
        self._add_resource_to_inventory(inventory_url, name, data)

    def delete_gnb(self, name: str) -> None:
        """Delete a gNB list from the NMS inventory."""
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}/{name}"
        self._delete_resource_from_inventory(inventory_url, name)

    def list_upfs(self) -> List[Upf]:
        """List UPFs from the NMS inventory."""
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}"
        json_upf_list = self._get_resources_from_inventory(inventory_url)
        return self._transform_response_to_upf(json_upf_list)

    def create_upf(self, hostname: str, port: int) -> None:
        """Create a UPF in the NMS inventory."""
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}/{hostname}"
        data = {"port": str(port)}
        self._add_resource_to_inventory(inventory_url, hostname, data)

    def delete_upf(self, hostname: str) -> None:
        """Delete a UPF list from the NMS inventory."""
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}/{hostname}"
        self._delete_resource_from_inventory(inventory_url, hostname)

    @staticmethod
    def _get_resources_from_inventory(inventory_url: str) -> List[Dict]:
        try:
            response = requests.get(inventory_url)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error("Failed to connect to NMS: %s", e)
            return []
        except requests.HTTPError as e:
            logger.error("Failed to get resource from inventory: %s", e)
            return []
        resources = response.json()
        logger.info("Got %s from inventory", resources)
        return resources

    @staticmethod
    def _add_resource_to_inventory(url: str, resource_name: str, data: dict) -> None:
        try:
            response = requests.post(url, headers=JSON_HEADER, json=data)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error("Failed to connect to NMS: %s", e)
            return
        except requests.HTTPError as e:
            logger.error("Failed to add %s to NMS: %s", resource_name, e)
            return
        logger.info("%s added to NMS", resource_name)

    @staticmethod
    def _delete_resource_from_inventory(inventory_url: str, resource_name: str) -> None:
        try:
            response = requests.delete(inventory_url)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            logger.error("Failed to connect to NMS: %s", e)
            return
        except requests.HTTPError as e:
            logger.error("Failed to remove %s from NMS: %s", resource_name, e)
            return
        logger.info("%s removed from NMS", resource_name)

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
