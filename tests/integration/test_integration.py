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
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
DATABASE_CHARM_NAME = "mongodb-k8s"
DATABASE_CHARM_CHANNEL = "6/beta"
TRAEFIK_CHARM_NAME = "traefik-k8s"
TRAEFIK_CHARM_CHANNEL = "latest/stable"
UPF_CHARM_NAME = "sdcore-upf-k8s"
UPF_CHARM_CHANNEL = "1.5/edge"
WEBUI_CHARM_NAME = "sdcore-webui-k8s"
WEBUI_CHARM_CHANNEL = "1.5/edge"
GNBSIM_CHARM_NAME = "sdcore-gnbsim-k8s"
GNBSIM_CHARM_CHANNEL = "1.5/edge"
GRAFANA_AGENT_CHARM_NAME = "grafana-agent-k8s"
GRAFANA_AGENT_CHARM_CHANNEL = "latest/stable"
TIMEOUT = 15 * 60


@pytest.fixture(scope="module")
@pytest.mark.abort_on_fail
async def deploy(ops_test: OpsTest, request):
    """Deploy the charm-under-test."""
    charm = Path(request.config.getoption("--charm_path")).resolve()
    resources = {
        "nms-image": METADATA["resources"]["nms-image"]["upstream-source"],
    }
    assert ops_test.model
    await ops_test.model.deploy(
        charm,
        resources=resources,
        application_name=APP_NAME,
    )


@pytest.mark.abort_on_fail
async def deploy_traefik(ops_test: OpsTest):
    """Deploy Traefik."""
    assert ops_test.model
    await ops_test.model.deploy(
        TRAEFIK_CHARM_NAME,
        application_name=TRAEFIK_CHARM_NAME,
        channel=TRAEFIK_CHARM_CHANNEL,
        trust=True,
    )

async def configure_traefik(ops_test: OpsTest, traefik_ip: str) ->  None:
    await ops_test.model.applications[TRAEFIK_CHARM_NAME].set_config(
        {
            "external_hostname": f"{traefik_ip}.nip.io",
            "routing_mode": "subdomain"
        }
    )
    await ops_test.model.wait_for_idle(
        apps=[TRAEFIK_CHARM_NAME],
        status="active",
        timeout=TIMEOUT,
    )

@pytest.mark.abort_on_fail
async def deploy_sdcore_upf(ops_test: OpsTest):
    """Deploy sdcore-upf-k8s-operator."""
    assert ops_test.model
    await ops_test.model.deploy(
        UPF_CHARM_NAME,
        application_name=UPF_CHARM_NAME,
        channel=UPF_CHARM_CHANNEL,
        trust=True,
    )


@pytest.mark.abort_on_fail
async def deploy_sdcore_webui(ops_test: OpsTest):
    """Deploy sdcore-webui-operator."""
    assert ops_test.model
    await ops_test.model.deploy(
        DATABASE_CHARM_NAME,
        application_name=DATABASE_CHARM_NAME,
        channel=DATABASE_CHARM_CHANNEL,
        trust=True,
    )
    await ops_test.model.deploy(
        WEBUI_CHARM_NAME,
        application_name=WEBUI_CHARM_NAME,
        channel=WEBUI_CHARM_CHANNEL,
    )
    await ops_test.model.integrate(
        relation1=f"{WEBUI_CHARM_NAME}:common_database", relation2=f"{DATABASE_CHARM_NAME}"
    )
    await ops_test.model.integrate(
        relation1=f"{WEBUI_CHARM_NAME}:auth_database", relation2=f"{DATABASE_CHARM_NAME}"
    )


@pytest.mark.abort_on_fail
async def deploy_sdcore_gnbsim(ops_test: OpsTest):
    """Deploy sdcore-gnbsim-operator."""
    assert ops_test.model
    await ops_test.model.deploy(
        GNBSIM_CHARM_NAME,
        application_name=GNBSIM_CHARM_NAME,
        channel=GNBSIM_CHARM_CHANNEL,
        trust=True,
    )


@pytest.mark.abort_on_fail
async def deploy_grafana_agent(ops_test: OpsTest):
    """Deploy grafana-agent operator."""
    assert ops_test.model
    await ops_test.model.deploy(
        GRAFANA_AGENT_CHARM_NAME,
        application_name=GRAFANA_AGENT_CHARM_NAME,
        channel=GRAFANA_AGENT_CHARM_CHANNEL,
    )


async def get_sdcore_nms_endpoint(ops_test: OpsTest) -> str:
    """Retrieve the SD-Core NMS endpoint by using Traefik's `show-proxied-endpoints` action."""
    assert ops_test.model
    traefik = ops_test.model.applications[TRAEFIK_CHARM_NAME]
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


async def get_traefik_ip(ops_test: OpsTest) -> str:
    """Retrieve the IP of the Traefik Application from the status message.

    The status message looks like this: Serving at 10.0.0.7
    """
    assert ops_test.model
    app_status = await ops_test.model.get_status(filters=[TRAEFIK_CHARM_NAME])
    ip_address = app_status.applications[TRAEFIK_CHARM_NAME].status["info"].split()[-1]
    return ip_address


def ui_is_running(nms_endpoint: str) -> bool:
    """Return whether the UI is running."""
    url = f"{nms_endpoint}network-configuration"
    t0 = time.time()
    timeout = 300  # seconds
    while time.time() - t0 < timeout:
        try:
            response = requests.get(url=url, timeout=5)
            response.raise_for_status()
            if "5G NMS" in response.content.decode("utf-8"):
                return True
        except Exception as e:
            logger.info(f"UI is not running yet: {e}")
        time.sleep(2)
    return False


@pytest.mark.abort_on_fail
async def test_given_required_relations_not_created_when_deploy_charm_then_status_is_blocked(
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="blocked",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_given_sdcore_management_relation_created_when_deploy_charm_then_status_is_active(
    ops_test: OpsTest, deploy
):
    await deploy_sdcore_webui(ops_test)
    assert ops_test.model
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:sdcore-management",
        relation2=f"{WEBUI_CHARM_NAME}:sdcore-management",
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=TIMEOUT,
    )

@pytest.mark.abort_on_fail
async def test_given_fiveg_n4_relation_when_deploy_charm_then_status_is_active(
    ops_test: OpsTest, deploy
):
    await deploy_sdcore_upf(ops_test)
    assert ops_test.model
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:fiveg_n4", relation2=f"{UPF_CHARM_NAME}:fiveg_n4"
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=TIMEOUT,
    )

@pytest.mark.abort_on_fail
async def test_given_fiveg_gnb_identity_created_when_deploy_charm_then_status_is_active(
    ops_test: OpsTest, deploy
):
    await deploy_sdcore_gnbsim(ops_test)
    assert ops_test.model
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:fiveg_gnb_identity",
        relation2=f"{GNBSIM_CHARM_NAME}:fiveg_gnb_identity",
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_given_traefik_deployed_when_relate_to_ingress_then_status_is_active(
    ops_test: OpsTest, deploy
):
    await deploy_traefik(ops_test)
    assert ops_test.model
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:ingress", relation2=f"{TRAEFIK_CHARM_NAME}:ingress"
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME, TRAEFIK_CHARM_NAME],
        status="active",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_given_grafana_agent_deployed_when_relate_to_logging_then_status_is_active(
    ops_test: OpsTest, deploy
):
    await deploy_grafana_agent(ops_test)
    assert ops_test.model
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:logging", relation2=GRAFANA_AGENT_CHARM_NAME
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="active",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_given_related_to_traefik_when_fetch_ui_then_returns_html_content(
    ops_test: OpsTest, deploy
):
    traefik_ip = await get_traefik_ip(ops_test)
    await configure_traefik(ops_test, traefik_ip)
    nms_url = await get_sdcore_nms_endpoint(ops_test)
    assert ui_is_running(nms_endpoint=nms_url)
