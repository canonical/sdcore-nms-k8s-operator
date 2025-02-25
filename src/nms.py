#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Module use to handle NMS API calls."""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, List, Optional

import requests
from charms.sdcore_nms_k8s.v0.fiveg_core_gnb import PLMNConfig

logger = logging.getLogger(__name__)

GNB_CONFIG_URL = "config/v1/inventory/gnb"
NETWORK_SLICE_CONFIG_URL = "config/v1/network-slice"
UPF_CONFIG_URL = "config/v1/inventory/upf"
ACCOUNTS_URL = "config/v1/account"

JSON_HEADER = {"Content-Type": "application/json"}


class NMSError(Exception):
    """Exception raised when an error occurs communicating with the NMS."""
    pass


@dataclass
class GnodeB:
    """Class to represent a gNB."""

    name: str
    tac: int = 1
    plmns: List[PLMNConfig] = field(default_factory=list)


@dataclass
class Upf:
    """Class to represent a UPF."""

    hostname: str
    port: int


@dataclass
class NetworkSlice:
    """Class to represent a NetworkSlice."""

    mcc: str
    mnc: str
    sst: int
    sd: int
    gnodebs: List[GnodeB]


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
class CreateGnbParams:
    """Parameters to create a gNB."""
    name: str
    tac: str

@dataclass
class UpdateGnbParams:
    """Parameters to update a gNB."""

    tac: str


@dataclass
class CreateUPFParams:
    """Parameters to create a UPF."""
    hostname: str
    port: str

@dataclass
class UpdateUPFParams:
    """Parameters to update a UPF."""

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
    ) -> Any:
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
                verify=self._ca_certificate_path or False,
            )
        except requests.exceptions.SSLError as e:
            logger.error("SSL error: %s", e)
            raise NMSError() from e
        except requests.RequestException as e:
            logger.error("HTTP request failed: %s", e)
            raise NMSError() from e
        except OSError as e:
            logger.error("couldn't complete HTTP request: %s", e)
            raise NMSError() from e
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.error(
                "%s request failed: code %s with message: %s",
                endpoint,
                response.status_code,
                response.text,
            )
            raise NMSError() from e
        try:
            json_response = response.json()
        except json.JSONDecodeError as e:
            raise NMSError() from e
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
        try:
            response = self._make_request("POST", "/login", data=asdict(login_params))
            return LoginResponse(
                token=response.get("token"),
            )
        except NMSError:
            return None

    def token_is_valid(self, token: str) -> bool:
        """Return if the token is still valid by attempting to connect to an endpoint."""
        try:
            return self._make_request("GET", f"/{ACCOUNTS_URL}", token=token)
        except NMSError:
            return False

    def get_status(self) -> StatusResponse | None:
        """Return if NMS is initialized."""
        try:
            return self._make_request("GET", "/status")
        except NMSError:
            return None

    def list_gnbs(self, token: str) -> List[GnodeB]:
        """List gNBs from the NMS inventory."""
        logger.info("Listing NMS gNBs")
        try:
            response = self._make_request("GET", f"/{GNB_CONFIG_URL}", token=token)
        except NMSError:
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
        create_gnb_params = CreateGnbParams(name=name, tac=str(tac))
        try:
            self._make_request(
                "POST", f"/{GNB_CONFIG_URL}", data=asdict(create_gnb_params), token=token
            )
            logger.info("gNB %s created in NMS", name)
        except NMSError:
            return

    def update_gnb(self, name: str, tac: int, token: str) -> None:
        """Update a gNB in the NMS inventory."""
        update_gnb_params = UpdateGnbParams(tac=str(tac))
        try:
            self._make_request(
                "PUT", f"/{GNB_CONFIG_URL}/{name}", data=asdict(update_gnb_params), token=token
            )
            logger.info("gNB %s updated in NMS", name)
        except NMSError:
            return

    def delete_gnb(self, name: str, token: str) -> None:
        """Delete a gNB list from the NMS inventory."""
        try:
            self._make_request("DELETE", f"/{GNB_CONFIG_URL}/{name}", token=token)
            logger.info("UPF %s deleted from NMS", name)
        except NMSError:
            return

    def list_upfs(self, token: str) -> List[Upf]:
        """List UPFs from the NMS inventory."""
        logger.info("Listing NMS UPFs")
        try:
            response = self._make_request("GET", f"/{UPF_CONFIG_URL}", token=token)
        except NMSError:
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
        create_upf_params = CreateUPFParams(hostname=hostname, port=str(port))
        try:
            self._make_request(
                "POST", f"/{UPF_CONFIG_URL}", data=asdict(create_upf_params), token=token
            )
            logger.info("UPF %s created in NMS", hostname)
        except NMSError:
            return

    def update_upf(self, hostname: str, port: int, token: str) -> None:
        """Update a UPF in the NMS inventory."""
        update_upf_params = UpdateUPFParams(port=str(port))
        try:
            self._make_request(
                "PUT", f"/{UPF_CONFIG_URL}/{hostname}", data=asdict(update_upf_params), token=token
            )
            logger.info("UPF %s updated in NMS", hostname)
        except NMSError:
            return

    def delete_upf(self, hostname: str, token: str) -> None:
        """Delete a UPF list from the NMS inventory."""
        try:
            self._make_request("DELETE", f"/{UPF_CONFIG_URL}/{hostname}", token=token)
            logger.info("UPF %s deleted from NMS", hostname)
        except NMSError:
            return

    def create_first_user(self, username: str, password: str) -> None:
        """Create the first admin user."""
        logger.info("Creating first user %s", username)
        create_user_params = CreateUserParams(username=username, password=password)
        self._make_request("POST", f"/{ACCOUNTS_URL}", data=asdict(create_user_params))

    def list_network_slices(self, token: str) -> List[str]:
        """List NetworkSlices."""
        try:
            return self._make_request("GET", f"/{NETWORK_SLICE_CONFIG_URL}", token=token)
        except NMSError:
            return []

    def get_network_slice(self, slice_name: str, token: str) -> Optional[NetworkSlice]:
        """Get NetworkSlice.

        The SD value received in the Network Slice configuration is a hex. In this function
        we cast it to a human-readable integer.
        """
        try:
            response = self._make_request("GET", f"/{NETWORK_SLICE_CONFIG_URL}/{slice_name}", token=token)  # noqa: E501
        except NMSError:
            return None
        mcc = response["site-info"]["plmn"]["mcc"]
        mnc = response["site-info"]["plmn"]["mnc"]
        sst = int(response["slice-id"]["sst"])
        sd = int(response["slice-id"]["sd"], 16)
        gnbs = [GnodeB(gnb["name"], gnb["tac"]) for gnb in response["site-info"]["gNodeBs"]]

        return NetworkSlice(mcc, mnc, sst, sd, gnbs)
