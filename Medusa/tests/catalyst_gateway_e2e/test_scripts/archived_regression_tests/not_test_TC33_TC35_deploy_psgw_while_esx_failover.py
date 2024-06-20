"""
This test case should be skipped because there is no recovery for a failure during FRW completion, we cannot resume the operation.
Need to delete the PSG and start again.

Reference: https://nimblejira.nimblestorage.com/browse/AT-15480

TC033 Failover on ESX server when Protection Store/Protection Store Gateway VM creation is in progress
(psgw vm should change esx host when psgw host is rebooting) HA and DRS on
TC035 Deploy Protection Store/Protection Store Gateway VMwhen ESX server is rebooted
(psgw vm should continue PSGW deployment when esx host is back online) HA and DRS off
"""

import logging
from waiting import wait, TimeoutExpired
from pytest import fixture, mark, exit
from requests import codes
from lib.common.enums.psg import HealthState, HealthStatus
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.psgw_steps import delete_protection_store_gateway_vm, cleanup_psgw_vm
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from tests.steps.tasks import tasks
from lib.common.enums.vm_power_option import VmPowerOption
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def _cleanup(context):
    context.vcenter_control.set_cluster_ha_status(context.ha_status)
    context.vcenter_control.set_cluster_drs_status(context.drs_status)
    context.vcenter_control.wait_for_host_power_status(context.hypervisor_name, VmPowerOption.on)
    _cleanup_psgw(context)
    context.vcenter_control.set_vms_power(context.vms_powered_on, VmPowerOption.on)


def _cleanup_psgw(context):
    psgw = context.catalyst_gateway.get_catalyst_gateway_by_name(context.psgw_name)
    if "id" in psgw:
        delete_protection_store_gateway_vm(context, verify=True)
    cleanup_psgw_vm(context)


def _check_hosts_are_available(context):
    hosts = context.vcenter_control.get_all_hosts(VmPowerOption.on)
    if len(hosts) < 2:
        msg = "Not enough esx host in cluster"
        logger.error(msg)
        exit(msg)


@fixture(scope="module")
def context():
    test_context = Context(skip_inventory_exception=True)
    test_context.vcenter_control = VMwareSteps(
        test_context.vcenter_name,
        test_context.vcenter_username,
        test_context.vcenter_password,
    )
    test_context.vms_powered_on = test_context.vcenter_control.get_all_vms(VmPowerOption.on)
    test_context.drs_status = test_context.vcenter_control.get_cluster_drs_status()
    test_context.ha_status = test_context.vcenter_control.get_cluster_ha_status()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    test_context.vcenter_control = VMwareSteps(
        test_context.vcenter_name,
        test_context.vcenter_username,
        test_context.vcenter_password,
    )
    _cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


def _create_protection_store_gateway_vm(context: Context):
    atlas = context.catalyst_gateway
    disk_space = context.__dict__.get("disk_size_tib", 1.0)
    logger.info(f"Create {context.psgw_name} VM on {context.vcenter_name}")
    response = atlas.create_catalyst_gateway_vm(
        context.psgw_name,
        context.vcenter_id,
        context.datastore_id,
        context.esxhost_id,
        context.network_name,
        context.network,
        context.netmask,
        context.gateway,
        disk_space,
        context.network_type,
    )
    logger.info(response.text)
    assert response.status_code == codes.created, f"{response.content}"
    task_id = tasks.get_task_id(response)
    logger.info(f"Create protection store gateway. Task ID: {task_id}")

    response = atlas.post_copypools(task_id)
    assert response.status_code == codes.accepted, "POST: local store creation succeed but should fail"
    local_copy_pool_task_id = tasks.get_task_id(response)

    try:
        wait(
            lambda: atlas.get_catalyst_gateway_health_state(context.psgw_name) == HealthState.REGISTERING.value,
            timeout_seconds=300,
            sleep_seconds=5,
        )
    except TimeoutExpired:
        raise AssertionError("PSGW VM health status is not the expected")

    return task_id, local_copy_pool_task_id


def _check_create_protection_store_gateway_vm(context: Context, task_id, local_copy_pool_task_id, expected_result):
    timeout = TimeoutManager.create_psgw_timeout
    atlas = context.catalyst_gateway
    message = lambda place, timeout: f"{place} copy pool creation time exceed {timeout / 60:.1f} minutes"
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        message=f"Catalyst Gateway creation time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status == expected_result, f"Deploy protection store gateway-{context.psgw_name} Task: {status}"

    local_copy_pool_status = tasks.wait_for_task(
        local_copy_pool_task_id,
        context.user,
        timeout,
        message=message("local", timeout),
    )
    assert local_copy_pool_status == expected_result, f"Create local protection store, Task: {local_copy_pool_status}"
    try:
        wait(
            lambda: atlas.get_catalyst_gateway_health_status(context.psgw_name) == HealthStatus.CONNECTED.value,
            timeout_seconds=TimeoutManager.standard_task_timeout,
            sleep_seconds=15,
        )
    except TimeoutExpired:
        raise AssertionError("PSGW VM health status is not the expected")
    if atlas.get_catalyst_gateway_health_state(context.psgw_name) == HealthState.WARNING.value:
        logger.warning("Protection Store is in WARNING state after deployment")
    logger.info("Protection store gateway creation success")


@mark.skip(
    reason="Should be skipped because there is no recovery for a failure during FRW completion, "
    "we cannot resume the operation."
)
@mark.order(330)
@mark.deploy
@mark.parametrize(
    "drs_status, ha_status",
    [
        (True, True),  # TC 33
        (False, False),  # TC 35
    ],
)
def test_tc033(context, drs_status, ha_status):
    context.vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    _cleanup_psgw(context)
    _check_hosts_are_available(context)
    context.vcenter_control.set_cluster_ha_status(ha_status)
    context.vcenter_control.set_cluster_drs_status(drs_status)
    context.vcenter_control.set_vms_power(context.vms_powered_on, VmPowerOption.off)
    task_id, local_copy_pool_task_id = _create_protection_store_gateway_vm(context)
    host_name = context.vcenter_control.get_vm_host(context.psgw_name)
    context.hypervisor_name = host_name
    context.vcenter_control.reboot_host_and_wait(host_name)
    if not ha_status:
        context.vcenter_control.set_vms_power([context.psgw_name], VmPowerOption.on)
    _check_create_protection_store_gateway_vm(context, task_id, local_copy_pool_task_id, "succeeded")
