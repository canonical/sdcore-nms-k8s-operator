#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import logging
import time
from base64 import b64decode
from collections import Counter
from pathlib import Path

import pytest
import requests
import yaml
from juju.application import Application
from juju.client.client import SecretsFilter
from pytest_operator.plugin import OpsTest

from charm import NMS_LOGIN_SECRET_LABEL
from nms import NMS, GnodeB, Upf

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
ANY_CHARM_PATH = "./tests/integration/any_charm.py"
AMF_MOCK = "amf-mock"
APP_NAME = METADATA["name"]
DATABASE_APP_NAME = "mongodb-k8s"
DATABASE_APP_CHANNEL = "6/stable"
COMMON_DATABASE_RELATION_NAME = "common_database"
AUTH_DATABASE_RELATION_NAME = "auth_database"
WEBUI_DATABASE_RELATION_NAME = "webui_database"
LOGGING_RELATION_NAME = "logging"
GNBSIM_CHARM_NAME = "sdcore-gnbsim-k8s"
GNBSIM_CHARM_CHANNEL = "1.6/edge"
GNBSIM_RELATION_NAME = "fiveg_core_gnb"
GRAFANA_AGENT_APP_NAME = "grafana-agent-k8s"
GRAFANA_AGENT_APP_CHANNEL = "latest/stable"
UPF_CHARM_NAME = "sdcore-upf-k8s"
UPF_CHARM_CHANNEL = "1.6/edge"
UPF_RELATION_NAME = "fiveg_n4"
TLS_PROVIDER_CHARM_NAME = "self-signed-certificates"
TLS_PROVIDER_CHARM_CHANNEL = "latest/stable"
TRAEFIK_CHARM_NAME = "traefik-k8s"
TRAEFIK_CHARM_CHANNEL = "latest/stable"
SDCORE_CHARMS_BASE = "ubuntu@24.04"
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
    # TODO: This is a workaround so Traefik has the same CA as NMS.
    # This should be removed and V1 of the certificate transfer interface should be used instead
    # The following PR is needed to get Traefik to implement V1 of certificate transfer interface:
    # https://github.com/canonical/traefik-k8s-operator/issues/407
    await ops_test.model.integrate(
        relation1=f"{TRAEFIK_CHARM_NAME}:certificates", relation2=TLS_PROVIDER_CHARM_NAME
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
        series="noble",  # TODO: This should be replaced with base=SDCORE_CHARMS_BASE once it's properly supported  # noqa: E501
    )


async def _deploy_sdcore_gnbsim(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        GNBSIM_CHARM_NAME,
        application_name=GNBSIM_CHARM_NAME,
        channel=GNBSIM_CHARM_CHANNEL,
        trust=True,
        base=SDCORE_CHARMS_BASE,
    )
    await ops_test.model.integrate(relation1=f"{GNBSIM_CHARM_NAME}:fiveg-n2", relation2=AMF_MOCK)


async def _deploy_self_signed_certificates(ops_test: OpsTest):
    assert ops_test.model
    await ops_test.model.deploy(
        TLS_PROVIDER_CHARM_NAME,
        application_name=TLS_PROVIDER_CHARM_NAME,
        channel=TLS_PROVIDER_CHARM_CHANNEL,
    )

async def _deploy_amf_mock(ops_test: OpsTest):
    fiveg_n2_lib_url = "https://github.com/canonical/sdcore-amf-k8s-operator/raw/main/lib/charms/sdcore_amf_k8s/v0/fiveg_n2.py"
    fiveg_n2_lib = requests.get(fiveg_n2_lib_url, timeout=10).text
    any_charm_src_overwrite = {
        "fiveg_n2.py": fiveg_n2_lib,
        "any_charm.py": Path(ANY_CHARM_PATH).read_text(),
    }
    assert ops_test.model
    await ops_test.model.deploy(
        "any-charm",
        application_name=AMF_MOCK,
        channel="beta",
        config={
            "src-overwrite": json.dumps(any_charm_src_overwrite),
            "python-packages": "ops==2.17.1\npytest-interface-tester"
        },
    )


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


async def get_sdcore_nms_external_endpoint(ops_test: OpsTest) -> str:
    endpoints = await get_traefik_proxied_endpoints(ops_test)
    return endpoints[APP_NAME]["url"].rstrip("/")


def _get_host_from_url(url: str) -> str:
    """Return the host from a URL formatted as http://<host>:<port>/ or as http://<host>/."""
    return url.split("//")[1].split(":")[0].split("/")[0]


def ui_is_running(nms_endpoint: str) -> bool:
    url = f"{nms_endpoint}/network-configuration"
    logger.info(f"Reaching NMS UI at {url}")
    t0 = time.time()
    timeout = 300  # seconds
    while time.time() - t0 < timeout:
        try:
            response = requests.get(url=url, timeout=5, verify=False)
            response.raise_for_status()
            logger.info(response.content.decode("utf-8"))
            if "5G NMS" in response.content.decode("utf-8"):
                return True
        except Exception as e:
            logger.error(f"UI is not running yet: {e}")
        time.sleep(2)
    return False


async def get_nms_credentials(ops_test: OpsTest) -> dict[str, str]:
    assert ops_test.model
    secrets = await ops_test.model.list_secrets(
        filter=SecretsFilter(label=NMS_LOGIN_SECRET_LABEL), show_secrets=True
    )
    return {
        field: b64decode(secrets[0].value.data[field]).decode("utf-8")
        for field in ["username", "password", "token"]
    }


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
    await _deploy_self_signed_certificates(ops_test)
    await _deploy_amf_mock(ops_test)
    await _deploy_sdcore_gnbsim(ops_test)
    await _deploy_sdcore_upf(ops_test)
    await _deploy_grafana_agent(ops_test)
    await _deploy_traefik(ops_test)


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
    await ops_test.model.integrate(relation1=APP_NAME, relation2=TLS_PROVIDER_CHARM_NAME)
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{WEBUI_DATABASE_RELATION_NAME}", relation2=DATABASE_APP_NAME
    )
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{LOGGING_RELATION_NAME}", relation2=GRAFANA_AGENT_APP_NAME
    )
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{GNBSIM_RELATION_NAME}", relation2=GNBSIM_CHARM_NAME
    )
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{UPF_RELATION_NAME}", relation2=UPF_CHARM_NAME
    )
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:ingress", relation2=f"{TRAEFIK_CHARM_NAME}:ingress"
    )
    await ops_test.model.wait_for_idle(
        apps=[APP_NAME, TRAEFIK_CHARM_NAME],
        status="active",
        timeout=TIMEOUT,
    )


@pytest.mark.abort_on_fail
async def test_given_related_to_traefik_when_fetch_ui_then_returns_html_content(
    ops_test: OpsTest, deploy
):
    # Workaround for Traefik issue: https://github.com/canonical/traefik-k8s-operator/issues/361
    traefik_ip = await get_traefik_ip_address(ops_test)
    await configure_traefik(ops_test, traefik_ip)
    nms_url = await get_sdcore_nms_external_endpoint(ops_test)
    assert nms_url.startswith("https")
    assert ui_is_running(nms_endpoint=nms_url)


@pytest.mark.abort_on_fail
async def test_given_nms_related_to_gnbsim_and_gnbsim_status_is_active_then_nms_inventory_contains_gnb_information(  # noqa: E501
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    nms_url = await get_sdcore_nms_external_endpoint(ops_test)
    nms_client = NMS(url=nms_url)

    t0 = time.time()
    timeout = 180  # seconds
    gnbs = []
    while time.time() - t0 < timeout:
        admin_credentials = await get_nms_credentials(ops_test)
        token = admin_credentials.get("token")
        assert token
        gnbs = nms_client.list_gnbs(token=token)
        if gnbs:
            break
        logger.info("Waiting for gNBs to be synchronized")
        time.sleep(10)

    expected_gnb_name = f"{ops_test.model.name}-gnbsim-{GNBSIM_CHARM_NAME}"
    expected_gnb = GnodeB(name=expected_gnb_name, tac=1)
    assert gnbs == [expected_gnb]


@pytest.mark.abort_on_fail
async def test_given_nms_related_to_upf_and_upf_status_is_active_then_nms_inventory_contains_upf_information(  # noqa: E501
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    await ops_test.model.wait_for_idle(apps=[UPF_CHARM_NAME], status="active", timeout=TIMEOUT)
    nms_url = await get_sdcore_nms_external_endpoint(ops_test)
    nms_client = NMS(url=nms_url)

    t0 = time.time()
    timeout = 180  # seconds
    upfs = []
    while time.time() - t0 < timeout:
        admin_credentials = await get_nms_credentials(ops_test)
        token = admin_credentials.get("token")
        assert token
        upfs = nms_client.list_upfs(token=token)
        if upfs:
            break
        logger.info("Waiting for UPFs to be synchronized")
        time.sleep(10)

    expected_upf_hostname = f"{UPF_CHARM_NAME}-external.{ops_test.model.name}.svc.cluster.local"
    expected_upf = Upf(hostname=expected_upf_hostname, port=8805)
    assert upfs == [expected_upf]


@pytest.mark.abort_on_fail
async def test_given_gnb_and_upf_are_remove_then_nms_inventory_does_not_contain_upf_nor_gnb_information(  # noqa: E501
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    admin_credentials = await get_nms_credentials(ops_test)
    token = admin_credentials.get("token")
    assert token
    await ops_test.model.remove_application(UPF_CHARM_NAME, block_until_done=False)
    await ops_test.model.remove_application(GNBSIM_CHARM_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)
    nms_url = await get_sdcore_nms_external_endpoint(ops_test)

    nms_client = NMS(url=nms_url)

    gnbs = nms_client.list_gnbs(token=token)
    assert gnbs == []

    upfs = nms_client.list_upfs(token=token)
    assert upfs == []


@pytest.mark.abort_on_fail
async def test_remove_database_and_wait_for_blocked_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.remove_application(DATABASE_APP_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="blocked", timeout=TIMEOUT)


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
    await ops_test.model.integrate(
        relation1=f"{APP_NAME}:{WEBUI_DATABASE_RELATION_NAME}", relation2=DATABASE_APP_NAME
    )
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


@pytest.mark.abort_on_fail
async def test_given_db_restored_then_credentials_are_restored_and_valid(
    ops_test: OpsTest, deploy
):
    assert ops_test.model
    admin_credentials = await get_nms_credentials(ops_test)
    username = admin_credentials.get("username")
    password = admin_credentials.get("password")
    assert username
    assert password
    nms_url = await get_sdcore_nms_external_endpoint(ops_test)
    nms_client = NMS(url=nms_url)
    token = nms_client.login(username=username, password = password)
    assert token


@pytest.mark.abort_on_fail
async def test_remove_tls_and_wait_for_blocked_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await ops_test.model.remove_application(TLS_PROVIDER_CHARM_NAME, block_until_done=True)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="blocked", timeout=60)


@pytest.mark.abort_on_fail
async def test_restore_tls_and_wait_for_active_status(ops_test: OpsTest, deploy):
    assert ops_test.model
    await _deploy_self_signed_certificates(ops_test)
    await ops_test.model.integrate(relation1=APP_NAME, relation2=TLS_PROVIDER_CHARM_NAME)
    await ops_test.model.wait_for_idle(apps=[APP_NAME], status="active", timeout=TIMEOUT)


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
