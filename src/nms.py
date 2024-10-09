#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle NMS API calls."""

import json
import logging
from dataclasses import asdict, dataclass
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

GNB_CONFIG_URL = "config/v1/inventory/gnb"
UPF_CONFIG_URL = "config/v1/inventory/upf"
ACCOUNTS_URL = "config/v1/accounts"

JSON_HEADER = {"Content-Type": "application/json"}


@dataclass
class Response:
    """Response from NMS."""

    result: any  # type: ignore[reportGeneralTypeIssues]
    error: str


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
class GnodeB:
    """Class to represent a gNB."""

    name: str
    tac: int


@dataclass
class Upf:
    """Class to represent a UPF."""

    hostname: str
    port: int


@dataclass(frozen=True)
class CreateUPFParams:
    """Parameters to create a UPF in NMS."""

    port: int


@dataclass(frozen=True)
class CreateGnbParams:
    """Parameters to create a gNB in NMS."""

    tac: int


class NMS:
    """Handle NMS API calls."""

    def __init__(self, url: str):
        self.url = url

    def _make_request(
        self,
        method: str,
        endpoint: str,
        token: Optional[str] = None,
        data: any = None,  # type: ignore[reportGeneralTypeIssues]
    ) -> Response | None:
        """Make an HTTP request and handle common error patterns."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        url = f"{self.url}{endpoint}"
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

        response = self._get_result(req)
        try:
            req.raise_for_status()
        except requests.HTTPError:
            logger.error(
                "Request failed: code %s, %s",
                req.status_code,
                response.error if response else "unknown",
            )
            return None
        return response

    def _get_result(self, req: requests.Response) -> Response | None:
        """Return the response from a request."""
        try:
            response = req.json()
        except json.JSONDecodeError:
            return None
        return Response(
            result=response.get("result"),
            error=response.get("error"),
        )

    def list_gnbs(self, token: str) -> List[GnodeB]:
        """List gNBs from the NMS inventory."""
        response = self._make_request("GET", f"/{GNB_CONFIG_URL}", token=token)
        if response and response.result:
            return [
                GnodeB(
                    name=item.get("name"),
                    tac=item.get("tac"),
                )
                for item in response.result
            ]
        return []

    def create_gnb(self, name: str, tac: int, token: str) -> None:
        """Create a gNB in the NMS inventory."""
        create_gnb_params = CreateGnbParams(tac=tac)
        self._make_request(
            "POST", f"/{GNB_CONFIG_URL}/{name}", token=token, data=asdict(create_gnb_params)
        )
        logger.info("gNB %s created in NMS", name)

    def delete_gnb(self, name: str, token: str) -> None:
        """Delete a gNB from the NMS inventory."""
        self._make_request("DELETE", f"/{GNB_CONFIG_URL}/{name}", token=token)
        logger.info("gNB %s removed from NMS", name)

    def list_upfs(self, token: str) -> List[Upf]:
        """List UPFs from the NMS inventory."""
        response = self._make_request("GET", f"/{UPF_CONFIG_URL}", token=token)
        if response and response.result:
            return [
                Upf(
                    hostname=item.get("hostname"),
                    port=item.get("port"),
                )
                for item in response.result
            ]
        return []

    def create_upf(self, hostname: str, port: int, token: str) -> None:
        """Create a UPF in the NMS inventory."""
        create_upf_params = CreateUPFParams(port=port)
        self._make_request(
            "POST", f"/{UPF_CONFIG_URL}/{hostname}", token=token, data=asdict(create_upf_params)
        )
        logger.info("UPF %s added to NMS", hostname)

    def delete_upf(self, hostname: str, token: str) -> None:
        """Delete a UPF from the NMS inventory."""
        self._make_request("DELETE", f"/{UPF_CONFIG_URL}/{hostname}", token=token)
        logger.info("UPF %s removed from NMS", hostname)

    def login(self, username: str, password: str) -> LoginResponse | None:
        """Login to NMS by sending the username and password and return a Token."""
        login_params = LoginParams(username=username, password=password)
        response = self._make_request("POST", "/login", data=asdict(login_params))
        if response and response.result:
            return LoginResponse(
                token=response.result.get("token"),
            )
        return None

    def token_is_valid(self, token: str) -> bool:
        """Return if the token is still valid by attempting to connect to an endpoint."""
        response = self._make_request("GET", f"/{ACCOUNTS_URL}/me", token=token)
        return response is not None

    def get_status(self) -> StatusResponse | None:
        """Return whether NMS is initialized."""
        response = self._make_request("GET", "/status")
        if response and response.result:
            return StatusResponse(
                initialized=response.result.get("initialized"),
            )
        return None

    def create_first_user(self, username: str, password: str) -> CreateUserResponse | None:
        """Create the first admin user."""
        create_user_params = CreateUserParams(username=username, password=password)
        response = self._make_request("POST", ACCOUNTS_URL, data=asdict(create_user_params))
        if response and response.result:
            return CreateUserResponse(
                id=response.result.get("id"),
            )
        return None

    def is_initialized(self) -> bool:
        """Return whether NMS is initialized."""
        status = self.get_status()
        return status.initialized if status else False

    def is_api_available(self) -> bool:
        """Return whether NMS is reachable."""
        status = self.get_status()
        return status is not None
