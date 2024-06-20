"""
    TestRail ID - C57582024
    Deploy Protection Store/Protection Store Gateway VM when device interface is not reachable

    TestRail ID - C57582032
    Monitor Protection Store/Protection Store Gateway VM when device interface is not reachable

    TestRail ID - C57582036
    Delete Protection Store/Protection Store Gateway VM when device interface is not reachable
"""

import logging
from pytest import fixture, mark
from requests import codes
from waiting import wait
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.vm_power_option import VmPowerOption
from lib.common.error_messages import (
    ERROR_MESSAGE_DURING_DEPLOYMENT,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    delete_protection_store_gateway_vm,
    select_or_create_protection_store_gateway_vm,
    disconnect_nic_and_validate_psg_creation,
    validate_psgvm_after_disconnect_nic_and_wait_for_UNKNOWN_state,
    validate_psgvm_after_reconnect_nic_and_wait_for_OK_state,
    delete_nic_during_deletion_of_psg_and_validate_deletion,
)
from tests.steps.vm_protection.common_steps import perform_cleanup

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(v_center_type="VCENTER2")
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(2500)
def test_deploy_psgw_while_nic_disconnected(context):
    """
    TestRail ID - C57582024
    Deploy Protection Store/Protection Store Gateway VM when device interface is not reachable
    """
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
    )
    disconnect_nic_and_validate_psg_creation(context, response)
    # deleting psgw which is partially deployed
    delete_protection_store_gateway_vm(context)


@mark.order(2505)
def test_monitor_psg_while_nic_disconnected(context):
    """
    TestRail ID - C57582032
    Monitor Protection Store/Protection Store Gateway VM when device interface is not reachable
    """
    # create and validate (psgw this has to be a new psg deployment so using this step)
    create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    # disconnecting NIC of psgw from vcenter
    validate_psgvm_after_disconnect_nic_and_wait_for_UNKNOWN_state(context)
    # reconnecting NIC of psgw from vcenter
    validate_psgvm_after_reconnect_nic_and_wait_for_OK_state(context)


@mark.order(2510)
def test_disconnect_nic_while_deleting_psg(context):
    """
    TestRail ID - C57582036
    Delete Protection Store/Protection Store Gateway VM when device interface is not reachable
    """
    create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    response = delete_protection_store_gateway_vm(context, verify=False)
    delete_nic_during_deletion_of_psg_and_validate_deletion(context, response)
