#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging
import time
from collections import Counter
from pathlib import Path
from typing import List

import pytest
import requests
import yaml
from juju.application import Application
from pytest_operator.plugin import OpsTest

from nms import NMS, GnodeB, Upf

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
AMF_CHARM_NAME = "sdcore-amf-k8s"
AMF_CHARM_CHANNEL = "1.5/edge"
APP_NAME = METADATA["name"]
DATABASE_APP_NAME = "mongodb-k8s"
DATABASE_APP_CHANNEL = "6/beta"
COMMON_DATABASE_RELATION_NAME = "common_database"
AUTH_DATABASE_RELATION_NAME = "auth_database"
LOGGING_RELATION_NAME = "logging"
GNBSIM_CHARM_NAME = "sdcore-gnbsim-k8s"
GNBSIM_CHARM_CHANNEL = "1.5/edge"
GNBSIM_RELATION_NAME = "fiveg_gnb_identity"
GRAFANA_AGENT_APP_NAME = "grafana-agent-k8s"
GRAFANA_AGENT_APP_CHANNEL = "latest/stable"
NRF_CHARM_NAME = "sdcore-nrf-k8s"
NRF_CHARM_CHANNEL = "1.5/edge"
UPF_CHARM_NAME = "sdcore-upf-k8s"
UPF_CHARM_CHANNEL = "1.5/edge"
UPF_RELATION_NAME = "fiveg_n4"
TLS_PROVIDER_CHARM_NAME = "self-signed-certificates"
TLS_PROVIDER_CHARM_CHANNEL = "latest/stable"
TRAEFIK_CHARM_NAME = "traefik-k8s"
TRAEFIK_CHARM_CHANNEL = "latest/stable"
TIMEOUT = 15 * 60


async def _deploy_database(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        DATABASE_APP_NAME,
        application_name=DATABASE_APP_NAME,
        channel=DATABASE_APP_CHANNEL,
        trust=True,
    )


async def _deploy_grafana_agent(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        GRAFANA_AGENT_APP_NAME,
        application_name=GRAFANA_AGENT_APP_NAME,
        channel=GRAFANA_AGENT_APP_CHANNEL,
    )


async def _deploy_traefik(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        TRAEFIK_CHARM_NAME,
        application_name=TRAEFIK_CHARM_NAME,
        channel=TRAEFIK_CHARM_CHANNEL,
        trust=True,
    )


async def configure_traefik(ops_test: OpsTest, traefik_ip: str) -> None:
    assert ops_test.model
    traefik = ops_test.model.applications[TRAEFIK_CHARM_NAME]
    assert traefik
    await traefik.set_config(
        {"external_hostname": f"{traefik_ip}.nip.io", "routing_mode": "subdomain"}
    )
    await ops_test.model.wait_for_idle(
        apps=[TRAEFIK_CHARM_NAME],
        status="active",
        timeout=TIMEOUT,
    )


async def _deploy_sdcore_upf(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        UPF_CHARM_NAME,
        application_name=UPF_CHARM_NAME,
        channel=UPF_CHARM_CHANNEL,
        trust=True,
    )


async def _deploy_nrf(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        NRF_CHARM_NAME,
        application_name=NRF_CHARM_NAME,
        channel=NRF_CHARM_CHANNEL,
    )
    await ops_test.model.integrate(
        relation1=f"{NRF_CHARM_NAME}:database", relation2=f"{DATABASE_APP_NAME}"
    )
    await ops_test.model.integrate(relation1=NRF_CHARM_NAME, relation2=TLS_PROVIDER_CHARM_NAME)


async def _deploy_sdcore_gnbsim(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        GNBSIM_CHARM_NAME,
        application_name=GNBSIM_CHARM_NAME,
        channel=GNBSIM_CHARM_CHANNEL,
        trust=True,
    )


async def _deploy_self_signed_certificates(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        TLS_PROVIDER_CHARM_NAME,
        application_name=TLS_PROVIDER_CHARM_NAME,
        channel=TLS_PROVIDER_CHARM_CHANNEL,
    )


async def _deploy_amf(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        AMF_CHARM_NAME,
        application_name=AMF_CHARM_NAME,
        channel=AMF_CHARM_CHANNEL,
        trust=True,
    )
    await ops_test.model.integrate(relation1=AMF_CHARM_NAME, relation2=NRF_CHARM_NAME)
    await ops_test.model.integrate(relation1=AMF_CHARM_NAME, relation2=GNBSIM_CHARM_NAME)
    await ops_test.model.integrate(relation1=AMF_CHARM_NAME, relation2=TLS_PROVIDER_CHARM_NAME)


async def get_traefik_proxied_endpoints(ops_test: OpsTest) -> dict:
    """Retrieve the endpoints by using Traefik's `show-proxied-endpoints` action."""
    assert ops_test.model
    traefik = ops_test.model.applications[TRAEFIK_CHARM_NAME]
    assert traefik
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
            return proxied_endpoints
        else:
            logger.info("Traefik did not return proxied endpoints yet")
        time.sleep(2)

    raise TimeoutError("Traefik did not return proxied endpoints")


async def get_traefik_ip_address(ops_test: OpsTest) -> str:
    endpoints = await get_traefik_proxied_endpoints(ops_test)
    return _get_host_from_url(endpoints[TRAEFIK_CHARM_NAME]["url"])


async def get_sdcore_nms_endpoint(ops_test: OpsTest) -> str:
    endpoints = await get_traefik_proxied_endpoints(ops_test)
    return endpoints[APP_NAME]["url"]


def _get_host_from_url(url: str) -> str:
    """Return the host from a URL formatted as http://<host>:<port>/ or as http://<host>/."""
    return url.split("//")[1].split(":")[0].split("/")[0]


def ui_is_running(nms_endpoint: str) -> bool:
    url = f"{nms_endpoint}network-configuration"
    t0 = time.time()
    timeout = 300  # seconds
    while time.time() - t0 < timeout:
        try:
            response = requests.get(url=url, timeout=5)
            response.raise_for_status()
            logger.info(response.content.decode("utf-8"))
            if "5G NMS" in response.content.decode("utf-8"):
                return True
        except Exception as e:
            logger.error(f"UI is not running yet: {e}")
        time.sleep(2)
    return False


def get_nms_inventory_resource(url: str) -> List:
    t0 = time.time()
    timeout = 100  # seconds
    while time.time() - t0 < timeout:
        try:
            response = requests.get(url=url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Cannot connect to the nms inventory: %s", e)
        time.sleep(2)
    return []


@pytest.fixture(scope="module")
@pytest.mark.abort_on_fail
async def deploy(ops_test: OpsTest, request):
    """Deploy required components."""
    charm = Path(request.config.getoption("--charm_path")).resolve()
    resources = {
        "nms-image": METADATA["resources"]["nms-image"]["upstream-source"],
    }
    assert ops_test.model
    await ops_test.model.deploy(
        charm,
        resources=resources,
        application_name=APP_NAME,
        trust=True,
    )
    await _deploy_database(ops_test)
    await _deploy_grafana_agent(ops_test)
    await _deploy_traefik(ops_test)
    await _deploy_self_signed_certificates(ops_test)
    await _deploy_nrf(ops_test)
    await _deploy_sdcore_gnbsim(ops_test)
    await _deploy_amf(ops_test)
    await _deploy_sdcore_upf(ops_test)


@pytest.mark.abort_on_fail
async def test_given_charm_is_built_when_deployed_then_status_is_blocked(
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME],
        status="blocked",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_relate_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{COMMON_DATABASE_RELATION_NAME}", relation2=DATABASE_APP_NAME
    )
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{AUTH_DATABASE_RELATION_NAME}", relation2=DATABASE_APP_NAME
    )
    await ops_test.model.integrate(relation1=APP_NAME, relation2=TLS_PROVIDER_APP_NAME)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{LOGGING_RELATION_NAME}", relation2=GRAFANA_AGENT_APP_NAME
    )
    await ops_test.model.integrate(relation1=APP_NAME, relation2=NRF_CHARM_NAME)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{GNBSIM_RELATION_NAME}", relation2=GNBSIM_CHARM_NAME
    )
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{UPF_RELATION_NAME}", relation2=UPF_CHARM_NAME
    )
    await ops_test.model.integrate(relation1=APP_NAME, relation2=AMF_CHARM_NAME)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:ingress", relation2=f"{TRAEFIK_CHARM_NAME}:ingress"
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME, TRAEFIK_CHARM_NAME],
        status="active",
        timeout=TIMEOUT,
    )


@pytest.mark.skip(
    reason="Bug in MongoDB: https://github.com/canonical/mongodb-k8s-operator/issues/218"
)
@pytest.mark.abort_on_fail
async def test_remove_database_and_wait_for_blocked_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.remove_application(DATABASE_APP_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="blocked", timeout=TIMEOUT)


@pytest.mark.skip(
    reason="Bug in MongoDB: https://github.com/canonical/mongodb-k8s-operator/issues/218"
)
@pytest.mark.abort_on_fail
async def test_restore_database_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await _deploy_database(ops_test)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{COMMON_DATABASE_RELATION_NAME}", relation2=DATABASE_APP_NAME
    )
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{AUTH_DATABASE_RELATION_NAME}", relation2=DATABASE_APP_NAME
    )
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)

@pytest.mark.abort_on_fail
async def test_remove_tls_and_wait_for_blocked_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.remove_application(TLS_PROVIDER_APP_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="blocked", timeout=60)


@pytest.mark.abort_on_fail
async def test_restore_tls_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await _deploy_tls_provider(ops_test)
    await ops_test.model.integrate(relation1=APP_NAME, relation2=TLS_PROVIDER_APP_NAME)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_given_related_to_traefik_when_fetch_ui_then_returns_html_content(
    ops_test: OpsTest, deploy
):
    # Workaround for Traefik issue: https://github.com/canonical/traefik-k8s-operator/issues/361
    traefik_ip = await get_traefik_ip_address(ops_test)
    logger.info(traefik_ip)
    await configure_traefik(ops_test, traefik_ip)
    nms_url = await get_sdcore_nms_endpoint(ops_test)
    assert ui_is_running(nms_endpoint=nms_url)


@pytest.mark.abort_on_fail
async def test_given_nms_related_to_gnbsim_and_gnbsim_status_is_active_then_nms_inventory_contains_gnb_information(  # noqa: E501
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    await ops_test.model.wait_for_idle(apps=[GNBSIM_CHARM_NAME], status="active", timeout=TIMEOUT)
    nms_url = await get_sdcore_nms_endpoint(ops_test)
    nms_client = NMS(url=nms_url)

    gnbs = nms_client.list_gnbs()

    expected_gnb_name = f"{ops_test.model.name}-gnbsim-{GNBSIM_CHARM_NAME}"
    expected_gnb = GnodeB(name=expected_gnb_name, tac=1)
    assert gnbs == [expected_gnb]


@pytest.mark.abort_on_fail
async def test_given_nms_related_to_upf_and_upf_status_is_active_then_nms_inventory_contains_upf_information(  # noqa: E501
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    await ops_test.model.wait_for_idle(apps=[UPF_CHARM_NAME], status="active", timeout=TIMEOUT)
    nms_url = await get_sdcore_nms_endpoint(ops_test)
    nms_client = NMS(url=nms_url)

    upfs = nms_client.list_upfs()

    expected_upf_hostname = f"{UPF_CHARM_NAME}-external.{ops_test.model.name}.svc.cluster.local"
    expected_upf = Upf(hostname=expected_upf_hostname, port=8805)
    assert upfs == [expected_upf]


@pytest.mark.abort_on_fail
async def test_given_gnb_and_upf_are_remove_then_nms_inventory_does_not_contain_upf_nor_gnb_information(  # noqa: E501
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    await ops_test.model.remove_application(UPF_CHARM_NAME, block_until_done=False)
    await ops_test.model.remove_application(GNBSIM_CHARM_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)
    nms_url = await get_sdcore_nms_endpoint(ops_test)
    nms_client = NMS(url=nms_url)

    gnbs = nms_client.list_gnbs()
    assert gnbs == []

    upfs = nms_client.list_upfs()
    assert upfs == []


@pytest.mark.abort_on_fail
async def test_when_scale_app_beyond_1_then_only_one_unit_is_active(ops_test: OpsTest, deploy):
    assert ops_test.model
    assert isinstance(app := ops_test.model.applications[APP_NAME], Application)
    await app.scale(3)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], timeout=TIMEOUT, wait_for_at_least_units=3)
    unit_statuses = Counter(unit.workload_status for unit in app.units)
    assert unit_statuses.get("active") == 1
    assert unit_statuses.get("blocked") == 2


async def test_remove_app(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.remove_application(APP_NAME, block_until_done=True)
