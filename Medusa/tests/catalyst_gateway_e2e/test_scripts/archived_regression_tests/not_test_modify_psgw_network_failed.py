"""
This is automation script to test the bugfix AT-13284
Automation Test Ticket: AT-13569

Steps:

1. Deploy PSG and wait for it to be OK and Connected
2. Then edit the PSGs network to use one of the active IPs (could be of a VM or active PSG VM)

Expected Behavior:

The task should fail with an appropriate error and PSG should be in OK state
"""

import logging
import re
import pytest
from lib.common.enums.psg import HealthState, HealthStatus
from pytest import mark
from requests import codes
from waiting import wait

from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.vcenter_steps import create_vm_and_refresh_vcenter_inventory
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
)
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from tests.steps.tasks import tasks

logger = logging.getLogger()


@pytest.fixture(scope="module")
def context():
    test_context = Context()
    create_vm_and_refresh_vcenter_inventory(test_context)
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


def _get_used_ip_by_vm(context: Context) -> str:
    """Find first used IP by VM on VCenter, validate if is valid and return"""
    ip_address = VMwareSteps(
        context.vcenter["ip"], context.vcenter["username"], context.vcenter["password"]
    ).get_vm_ip_by_name(context.vm_name)
    match = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", str(ip_address))
    assert bool(match), f"{ip_address} is not valid IP Address"
    for part in ip_address.split("."):
        assert 0 <= int(part) <= 255, f"{ip_address} is not valid IP Address"
    return ip_address


def _update_network_address_psgw_failed(context: Context):
    _TIMEOUT = 1000
    _EXPECTED_TASK_MESSAGE = "Network reconfiguration has failed."
    _EXPECTED_TASK_LOGS = [
        "error updating network reconfig state",
        "Network reconfiguration has failed.",
    ]
    atlas = context.catalyst_gateway
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert "id" in psgw, "Failed to find PSGW ID"
    response = atlas.get_catalyst_gateway(psgw["id"])
    assert response.status_code == codes.ok
    network = {"nic": response.json()["network"]["nics"][-1]}
    network["nic"]["networkAddress"] = context.network
    response = atlas.update_network_interface(psgw["id"], network)

    assert response.status_code == codes.accepted, "Failed to update the network address of PSGW VM"
    task_id = tasks.get_task_id(response)
    status = tasks.wait_for_task(task_id, context.user, timeout=_TIMEOUT)
    logger.info(f"Network address successfully updated to {context.network}")
    assert status == "failed", f"Network update task failed. Task id: {task_id}"
    task_message = tasks.get_task_error(task_id, context.user)
    task_logs = tasks.get_task_logs(task_id, context.user)
    assert task_message == _EXPECTED_TASK_MESSAGE
    assert task_logs[0]["message"] == _EXPECTED_TASK_LOGS[0]
    assert task_logs[1]["message"] == _EXPECTED_TASK_LOGS[1]


def _validate_health(context: Context):
    catalyst_gateway = context.catalyst_gateway
    wait(
        lambda: catalyst_gateway.get_catalyst_gateway_health_state(context.psgw_name) == HealthState.OK.value,
        timeout_seconds=300,
        sleep_seconds=10,
    )
    wait(
        lambda: catalyst_gateway.get_catalyst_gateway_health_status(context.psgw_name) == HealthStatus.CONNECTED.value,
        timeout_seconds=300,
        sleep_seconds=10,
    )


@mark.skip(reason="vm ip discovery isnt working")
@mark.order(1100)
def test_modify_psgw_network_failed(context: Context):
    create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    context.network = _get_used_ip_by_vm(context)
    _update_network_address_psgw_failed(context)
    _validate_health(context)
