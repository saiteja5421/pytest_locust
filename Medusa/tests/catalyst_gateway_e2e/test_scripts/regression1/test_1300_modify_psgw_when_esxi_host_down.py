"""
    TestRail ID - C57582011
    vCenter/ESX server hosting VM goes down during modification of Network Interfaces

    TestRail ID - C57582009
    vCenter/ESX server hosting VM goes down during modification of Local protection store size
"""

import logging
from pytest import fixture, mark
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    resize_psgvm_when_esx_disconnected,
    create_psgvm_nic_interface_when_esx_disconnected,
)
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.vcenter_steps import check_esxi_host_status
from tests.steps.vm_protection.vmware_steps import VMwareSteps

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(set_static_policy=False, deploy=True)
    yield test_context
    # Exsi host status after tests completed
    check_esxi_host_status(test_context)

    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    perform_cleanup(test_context, clean_vm=True)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.order(1300)
@mark.dependency(name="test_modify_network_interface_psgw")
def test_modify_network_interface_psgw(context):
    """
    TestRail ID - C57582011
    vCenter/ESX server hosting VM goes down during modification of Network Interfaces
    """
    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)

    # create psg_vm and validate
    max_cld_dly_prtctd_data = 1.0
    max_cld_rtn_days = 1
    max_onprem_dly_prtctd_data = 1.0
    max_onprem_rtn_days = 1
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)

    # Fetching host name from host info of the psgw vm to disconnect the host where psgw vm is hosted.
    host_name = vcenter_control.get_vm_host(context.psgw_name)
    context.hypervisor_name = host_name
    vcenter_control.disconnect_host_and_wait(context.hypervisor_name)

    # Adding additional netowork interface while exsi host is disconnected
    create_psgvm_nic_interface_when_esx_disconnected(context)


@mark.order(1305)
@mark.dependency(name="test_modify_local_psgw_size", depends=["test_modify_network_interface_psgw"])
def test_modify_local_psgw_size(context):
    """
    TestRail ID - C57582009
    vCenter/ESX server hosting VM goes down during modification of Local protection store size
    """
    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    # Resize local psg_vm when Exsi host is disconnected
    resize_psgvm_when_esx_disconnected(context)

    # Reconnect the exsi host
    vcenter_control.reconnect_host_and_wait(context.hypervisor_name)
