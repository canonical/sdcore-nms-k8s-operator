#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.


import json
import logging
import time
from pathlib import Path

import pytest
import requests  # type: ignore[import]
import yaml

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
APP_NAME = METADATA["name"]
TRAEFIK_APP_NAME = "traefik"
UPF_APP_NAME = "upf"
WEBUI_APP_NAME = "webui"
GNBSIM_APP_NAME = "gnbsim"
GRAFANA_AGENT_APP_NAME = "grafana-agent-k8s"


@pytest.mark.abort_on_fail
async def build_and_deploy(ops_test):
    """Build the charm-under-test and deploy it."""
    charm = await ops_test.build_charm(".")
    resources = {
        "nms-image": METADATA["resources"]["nms-image"]["upstream-source"],
    }
    await ops_test.model.deploy(
        charm,
        resources=resources,
        application_name=APP_NAME,
        trust=True,
    )


@pytest.mark.abort_on_fail
async def deploy_traefik(ops_test):
    """Deploy Traefik."""
    await ops_test.model.deploy(
        "traefik-k8s",
        application_name=TRAEFIK_APP_NAME,
        config={"external_hostname": "pizza.com", "routing_mode": "subdomain"},
        trust=True,
    )


@pytest.mark.abort_on_fail
async def deploy_sdcore_upf(ops_test):
    """Deploy sdcore-upf-operator."""
    await ops_test.model.deploy(
        "sdcore-upf",
        application_name=UPF_APP_NAME,
        channel="edge",
        trust=True,
    )


@pytest.mark.abort_on_fail
async def deploy_sdcore_webui(ops_test):
    """Deploy sdcore-webui-operator."""
    await ops_test.model.deploy(
        "sdcore-webui",
        application_name=WEBUI_APP_NAME,
        channel="edge",
        trust=True,
    )


@pytest.mark.abort_on_fail
async def deploy_sdcore_gnbsim(ops_test):
    """Deploy sdcore-gnbsim-operator."""
    await ops_test.model.deploy(
        "sdcore-gnbsim",
        application_name=GNBSIM_APP_NAME,
        channel="edge",
        trust=True,
    )


@pytest.mark.abort_on_fail
async def deploy_grafana_agent(ops_test):
    """Deploy grafana-agent operator."""
    await ops_test.model.deploy(
        GRAFANA_AGENT_APP_NAME,
        application_name=GRAFANA_AGENT_APP_NAME,
        channel="stable",
    )


async def get_sdcore_nms_endpoint(ops_test) -> str:
    """Retrieves the SD-Core NMS endpoint by using Traefik's `show-proxied-endpoints` action."""
    traefik = ops_test.model.applications[TRAEFIK_APP_NAME]
    traefik_unit = traefik.units[0]
    t0 = time.time()
    timeout = 30  # seconds
    while time.time() - t0 < timeout:
        proxied_endpoint_action = await traefik_unit.run_action(
            action_name="show-proxied-endpoints"
        )
        action_output = await ops_test.model.get_action_output(
            action_uuid=proxied_endpoint_action.entity_id, wait=30
        )

        if "proxied-endpoints" in action_output:
            proxied_endpoints = json.loads(action_output["proxied-endpoints"])
            return proxied_endpoints[APP_NAME]["url"]
        else:
            logger.info("Traefik did not return proxied endpoints yet")
        time.sleep(2)

    raise TimeoutError("Traefik did not return proxied endpoints")


async def get_traefik_ip(ops_test) -> str:
    """Retrieves the IP of the Traefik Application."""
    app_status = await ops_test.model.get_status(filters=[TRAEFIK_APP_NAME])
    return app_status.applications[TRAEFIK_APP_NAME].public_address


def _get_host_from_url(url: str) -> str:
    """Returns the host from a URL formatted as http://<host>:<port>/ or as http://<host>/."""
    return url.split("//")[1].split(":")[0].split("/")[0]


def ui_is_running(ip: str, host: str) -> bool:
    """Returns whether the UI is running."""
    url = f"http://{ip}/network-configuration"
    headers = {"Host": host}
    t0 = time.time()
    timeout = 300  # seconds
    while time.time() - t0 < timeout:
        try:
            response = requests.get(url=url, headers=headers, timeout=5)
            response.raise_for_status()
            if "5G NMS" in response.content.decode("utf-8"):
                return True
        except Exception as e:
            logger.info(f"UI is not running yet: {e}")
        time.sleep(2)
    return False


@pytest.mark.abort_on_fail
async def test_given_required_relations_not_created_when_deploy_charm_then_status_is_blocked(
    ops_test,
):
    await build_and_deploy(ops_test)
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="blocked",
        timeout=1000,
    )


@pytest.mark.abort_on_fail
async def test_given_sdcore_management_relation_created_when_deploy_charm_then_status_is_active(
    ops_test,
):
    await deploy_sdcore_webui(ops_test)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:sdcore-management", relation2=f"{WEBUI_APP_NAME}:sdcore-management"
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=1000,
    )


@pytest.mark.abort_on_fail
async def test_given_fiveg_n4_relation_when_deploy_charm_then_status_is_active(
    ops_test,
):
    await deploy_sdcore_upf(ops_test)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:fiveg_n4", relation2=f"{UPF_APP_NAME}:fiveg_n4"
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=1000,
    )


@pytest.mark.abort_on_fail
async def test_given_fiveg_gnb_identity_created_when_deploy_charm_then_status_is_active(
    ops_test,
):
    await deploy_sdcore_gnbsim(ops_test)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:fiveg_gnb_identity",
        relation2=f"{GNBSIM_APP_NAME}:fiveg_gnb_identity",
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME, UPF_APP_NAME],
        status="active",
        timeout=1000,
    )


@pytest.mark.abort_on_fail
async def test_given_traefik_deployed_when_relate_to_ingress_then_status_is_active(ops_test):
    await deploy_traefik(ops_test)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:ingress", relation2=f"{TRAEFIK_APP_NAME}:ingress"
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME, TRAEFIK_APP_NAME],
        status="active",
        timeout=1000,
    )


@pytest.mark.abort_on_fail
async def test_given_grafana_agent_deployed_when_relate_to_logging_then_status_is_active(ops_test):
    await deploy_grafana_agent(ops_test)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:logging", relation2=GRAFANA_AGENT_APP_NAME
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=1000,
    )


@pytest.mark.abort_on_fail
async def test_given_related_to_traefik_when_fetch_ui_then_returns_html_content(ops_test):
    nms_url = await get_sdcore_nms_endpoint(ops_test)
    traefik_ip = await get_traefik_ip(ops_test)
    nms_host = _get_host_from_url(nms_url)
    assert ui_is_running(ip=traefik_ip, host=nms_host)
