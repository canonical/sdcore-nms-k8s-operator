#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle webui API calls."""

import json
import logging
from dataclasses import dataclass
from typing import List
import requests

logger = logging.getLogger(__name__)

GNB_CONFIG_URL = "config/v1/inventory/gnb"
UPF_CONFIG_URL = "config/v1/inventory/upf"
JSON_HEADER = {'Content-Type': 'application/json'}


@dataclass
class GnodeB:
    name: str
    tac: int

def transform_json_to_gnb(json_data: str) -> List[GnodeB]:
    parsed_data = json.loads(json_data)
    gnodeb_list = [GnodeB(name=item['name'], tac=int(item['tac'])) for item in parsed_data]
    return gnodeb_list

@dataclass
class Upf:
    hostname: str
    port: int

def transform_json_to_upf(json_data: str) -> List[Upf]:
    parsed_data = json.loads(json_data)
    upf_list = [Upf(hostname=item['hostname'], tac=int(item['port'])) for item in parsed_data]
    return upf_list

class Webui:

    def __init__(self, url: str):
        self.url = url

    def get_gnbs_from_inventory(self) -> List[GnodeB]:
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}"
        json_gnb_list = self._get_resources_from_inventory(inventory_url)
        return transform_json_to_gnb(json_gnb_list)

    def add_gnb_to_inventory(self, gnb: GnodeB) -> None:
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}/{gnb.name}"
        data = {"tac": gnb.tac}
        self._add_resource_to_inventory(inventory_url, gnb.name, data)

    def delete_gnb_from_inventory(self, gnb_name: str) -> None:
        inventory_url = f"{self.url}/{GNB_CONFIG_URL}/{gnb_name}"
        self._delete_resource_from_inventory(inventory_url, gnb_name)

    def get_upfs_from_inventory(self) -> List[Upf]:
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}"
        json_upf_list = self._get_resources_from_inventory(inventory_url)
        return transform_json_to_upf(json_upf_list)

    def add_upf_to_inventory(self, upf: Upf) -> None:
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}/{upf.hostname}"
        data = {"port": upf.port}
        self._add_resource_to_inventory(inventory_url, upf.hostname, data)

    def delete_upf_from_inventory(self, upf_hostname: str) -> None:
        inventory_url = f"{self.url}/{UPF_CONFIG_URL}/{upf_hostname}"
        self._delete_resource_from_inventory(inventory_url, upf_hostname)

    def _get_resources_from_inventory(self, inventory_url: str) -> list:
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
            logger.error(f"Failed to add {resource_name} to webui: {e}")
            return
        logger.info(f"{resource_name} added to webui")

    def _delete_resource_from_inventory(self, inventory_url: str, resource_name: str) -> None:
        response = requests.delete(inventory_url)
        try:
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to remove {resource_name} from webui: {e}")
            return
        logger.info(f"{resource_name} removed from webui")
