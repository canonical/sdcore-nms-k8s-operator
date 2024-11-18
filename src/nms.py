#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle NMS API calls."""

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, List, Optional

import requests

logger = logging.getLogger(__name__)

GNB_CONFIG_URL = "config/v1/inventory/gnb"
UPF_CONFIG_URL = "config/v1/inventory/upf"
ACCOUNTS_URL = "config/v1/account"

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
class StatusResponse:
    """Response from NMS when checking the status."""

    initialized: bool


@dataclass
class LoginParams:
    """Parameters to login to NMS."""

    username: str
    password: str


@dataclass
class LoginResponse:
    """Response from NMS when logging in."""

    token: str


@dataclass
class CreateUserParams:
    """Parameters to create a user in NMS."""

    username: str
    password: str


@dataclass
class CreateUserResponse:
    """Response from NMS when creating a user."""

    id: int


@dataclass
class CreateGnbParams:
    """Parameters to create a gNB."""

    tac: str


@dataclass
class CreateUPFParams:
    """Parameters to create a UPF."""

    port: str


class NMS:
    """Handle NMS API calls."""

    def __init__(self, url: str, ca_certificate_path: str = ""):
        if url.endswith("/"):
            url = url[:-1]
        self.url = url
        self._ca_certificate_path = ca_certificate_path

    def _make_request(
        self,
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        data: any = None,  # type: ignore[reportGeneralTypeIssues]
    ) -> Any | None:
        """Make an HTTP request and handle common error patterns."""
        headers = JSON_HEADER
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = f"{self.url}{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                verify=self._ca_certificate_path or False
            )
        except requests.exceptions.SSLError as e:
            logger.error("SSL error: %s", e)
            return None
        except requests.RequestException as e:
            logger.error("HTTP request failed: %s", e)
            return None
        except OSError as e:
            logger.error("couldn't complete HTTP request: %s", e)
            return None
        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.error(
                "Request failed: code %s",
                response.status_code,
            )
            return None
        try:
            json_response = response.json()
        except json.JSONDecodeError:
            return None
        return json_response

    def is_initialized(self) -> bool:
        """Return if NMS is initialized."""
        status = self.get_status()
        return status.initialized if status else False

    def is_api_available(self) -> bool:
        """Return if NMS is reachable."""
        status = self.get_status()
        return status is not None

    def login(self, username: str, password: str) -> LoginResponse | None:
        """Login to NMS by sending the username and password and return a Token."""
        login_params = LoginParams(username=username, password=password)
        response = self._make_request("POST", "/login", data=asdict(login_params))
        logger.info("Response: %s", response)
        if response:
            return LoginResponse(
                token=response.get("token"),
            )
        return None

    def token_is_valid(self, token: str) -> bool:
        """Return if the token is still valid by attempting to connect to an endpoint."""
        response = self._make_request("GET", f"/{ACCOUNTS_URL}/me", token=token)
        logger.info("Response: %s", response)
        return response is not None

    def get_status(self) -> StatusResponse | None:
        """Return if NMS is initialized."""
        response = self._make_request("GET", "/status")
        logger.info("Response: %s", response)
        if response:
            return StatusResponse(
                initialized=response.get("initialized"),
            )
        return None

    def list_gnbs(self, token: str) -> List[GnodeB]:
        """List gNBs from the NMS inventory."""
        response = self._make_request("GET", f"/{GNB_CONFIG_URL}", token=token)
        logger.info("Response: %s", response)
        if not response:
            return []
        gnb_list = []
        for item in response:
            try:
                gnb_list.append(GnodeB(name=item["name"], tac=int(item["tac"])))
            except (ValueError, KeyError):
                logger.error("invalid gNB data: %s", item)
        return gnb_list

    def create_gnb(self, name: str, tac: int, token: str) -> None:
        """Create a gNB in the NMS inventory."""
        create_gnb_params = CreateGnbParams(tac=str(tac))
        self._make_request(
            "POST", f"/{GNB_CONFIG_URL}/{name}", data=asdict(create_gnb_params), token=token
        )
        logger.info("gNB %s created in NMS", name)

    def delete_gnb(self, name: str, token: str) -> None:
        """Delete a gNB list from the NMS inventory."""
        self._make_request("DELETE", f"/{GNB_CONFIG_URL}/{name}", token=token)
        logger.info("UPF %s deleted from NMS", name)

    def list_upfs(self, token: str) -> List[Upf]:
        """List UPFs from the NMS inventory."""
        response = self._make_request("GET", f"/{UPF_CONFIG_URL}", token=token)
        logger.info("Response: %s", response)
        if not response:
            return []
        upf_list = []
        for item in response:
            try:
                upf_list.append(Upf(hostname=item["hostname"], port=int(item["port"])))
            except (ValueError, KeyError):
                logger.error("invalid UPF data: %s", item)
        return upf_list

    def create_upf(self, hostname: str, port: int, token: str) -> None:
        """Create a UPF in the NMS inventory."""
        create_upf_params = CreateUPFParams(port=str(port))
        self._make_request(
            "POST", f"/{UPF_CONFIG_URL}/{hostname}", data=asdict(create_upf_params), token=token
        )
        logger.info("UPF %s created in NMS", hostname)

    def delete_upf(self, hostname: str, token: str) -> None:
        """Delete a UPF list from the NMS inventory."""
        self._make_request("DELETE", f"/{UPF_CONFIG_URL}/{hostname}", token=token)
        logger.info("UPF %s deleted from NMS", hostname)

    def create_first_user(self, username: str, password: str) -> CreateUserResponse | None:
        """Create the first admin user."""
        logger.info("Creating first user %s", username)
        create_user_params = CreateUserParams(username=username, password=password)
        response = self._make_request("POST", f"/{ACCOUNTS_URL}", data=asdict(create_user_params))
        logger.info("Response: %s", response)
        if response:
            return CreateUserResponse(
                id=response.get("id"),
            )
        return None
