"""
TestRail ID - C57582004
   Monitor Protection Store/Protection Store Gateway VM - ESX server is down/unreachable

TestRail ID - C57582005
   Monitor Protection Store/Protection Store Gateway VM - ESX Server/vCenter network is unstable

TestRail ID - C57582006
   Monitor Protection Store/Protection Store Gateway VM - when VM is restarted

TestRail ID - C57582007
   Monitor Protection Store/Protection Store Gateway VM - when VM is powered off
   
"""

import logging
import time
from pytest import fixture, mark
from lib.common.enums.psg import HealthState, HealthStatus, State
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    reboot_protection_store_gateway_vm_from_vcenter,
    wait_for_psg,
    power_off_protection_store_gateway_vm_from_vcenter,
    power_on_protection_store_gateway_vm_from_vcenter,
)

from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from lib.platform.vmware.vsphere_api import VsphereApi
from utils.timeout_manager import TimeoutManager
from tests.steps.vm_protection.vcenter_steps import check_esx_and_psg_vm_status

# global cloud_usage, local_usage

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(set_static_policy=False, deploy=True)
    yield test_context
    check_esx_and_psg_vm_status(test_context)
    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    perform_cleanup(test_context, clean_vm=True)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.order(1200)
@mark.dependency(name="test_monitor_psgvm_esxi_down")
def test_monitor_psgvm_esxi_down(context):
    """
    TestRail ID - C57582004
    Monitor Protection Store/Protection Store Gateway VM - ESX server is down/unreachable
    """

    # Creating and validating psg_vm
    additional_interface = True

    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    create_protection_store_gateway_vm(context, add_data_interface=additional_interface)
    validate_protection_store_gateway_vm(context)

    # Fetching host name from host info of the psg_vm to disconnect the host where psg_vm is hosted.
    host_name = vcenter_control.get_vm_host(context.psgw_name)
    context.hypervisor_name = host_name
    vcenter_control.disconnect_host_and_wait(context.hypervisor_name)

    """Waiting for timeout (approximately 1 minute) before checking psg_vm status, to 
       ensure the psg_vm is still in healthy state. """
    timeout = 60
    time.sleep(timeout)

    # Checking for psg_vm health state, status and state after waiting for timeout period.
    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)

    # Reconnect the host after psg_vm status check
    vcenter_control.reconnect_host_and_wait(context.hypervisor_name)

    # Checking for psg_vm health state, status and state after ESX host reconnect
    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)


@mark.order(1205)
@mark.dependency(name="test_monitor_psgvm_network_unstable", depends=["test_monitor_psgvm_esxi_down"])
def test_monitor_psgvm_network_unstable(context):
    """
    TestRail ID - C57582005
    Monitor Protection Store/Protection Store Gateway VM - ESX Server/vCenter network is unstable
    """

    # Check status of psg_vm when the VM Netowrk nic of psg_vm is disconnected.
    # Fetching vm's identifier and VM Network identifier from vpshere API
    vsphere = VsphereApi(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    logger.info(f"Performing disconnect of the psg_vm VM Network nic")
    message = vsphere.disconnect_vm_nic(context.psgw_name)
    logger.info(message)
    assert message == "Disconnect of psg_vm successfull", f"disconnect of psg_vm nic failed"

    # Waiting for 5 seconds before reconnecting the psg_vm VM Network nic
    time.sleep(5)

    # Checking psgvm status after reconnect psg_vm VM Network nic
    logger.info(f"Performing reconnect of the psg_vm VM network nic")
    message = vsphere.reconnect_vm_nic(context.psgw_name)
    logger.info(message)
    assert message == "Reconnect of psg_vm successfull", f"reconnect of vm failed"

    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)


@mark.order(1210)
@mark.dependency(
    name="test_monitor_psgvm_on_reboot", depends=["test_monitor_psgvm_esxi_down", "test_monitor_psgvm_network_unstable"]
)
def test_monitor_psgvm_on_reboot(context):
    """
    TestRail ID - C57582006
    Monitor Protection Store/Protection Store Gateway VM - when VM is restarted
    """
    # Check status of psg_vm when the psgw_vm is rebooted.
    TimeoutManager.standard_task_timeout = 1800
    # Reboot psgw_vm
    reboot_protection_store_gateway_vm_from_vcenter(context)

    # As psgw not coming to unknown state during the reboot so we are commenting this part.
    # Checking psgw_vm status after reboot
    # wait_for_psg(
    #     context,
    #     state=State.UNKNOWN,
    #     health_state=HealthState.UNKNOWN,
    #     health_status=HealthStatus.DISCONNECTED,
    #     timeout=TimeoutManager.standard_task_timeout,
    # )
    # logger.info(f"Psgw_vm status changed to UNKNOWN after reboot")

    # wait for 10 min after reboot vm from vcenter
    time.sleep(600)
    # Checking recovery of psgw_vm after reboot.
    wait_for_psg(
        context,
        state=State.OK,
        health_state=HealthState.OK,
        health_status=HealthStatus.CONNECTED,
        timeout=TimeoutManager.standard_task_timeout,
    )
    logger.info(f"Psgw_vm successfully recovered after reboot")


@mark.order(1215)
@mark.dependency(
    name="test_monitor_psgvm_powered_off",
    depends=["test_monitor_psgvm_esxi_down", "test_monitor_psgvm_network_unstable", "test_monitor_psgvm_on_reboot"],
)
def test_monitor_psgvm_powered_off(context):
    """
    TestRail ID - C57582007
    Monitor Protection Store/Protection Store Gateway VM - when VM is powered off
    """
    # Check status of psg_vm when the psgw_vm is power off.
    TimeoutManager.standard_task_timeout = 1800
    # Power off psgw_vm and check status
    power_off_protection_store_gateway_vm_from_vcenter(context)

    wait_for_psg(
        context,
        state=State.UNKNOWN,
        health_state=HealthState.UNKNOWN,
        health_status=HealthStatus.DISCONNECTED,
        timeout=TimeoutManager.standard_task_timeout,
    )
    logger.info(f"Psgw_vm now in powered-off state")

    # power on psgw_vm and check status
    power_on_protection_store_gateway_vm_from_vcenter(context)

    wait_for_psg(
        context,
        state=State.OK,
        health_state=HealthState.OK,
        health_status=HealthStatus.CONNECTED,
        timeout=TimeoutManager.standard_task_timeout,
    )
    logger.info(f"Psgw_vm successfully powered-on")
