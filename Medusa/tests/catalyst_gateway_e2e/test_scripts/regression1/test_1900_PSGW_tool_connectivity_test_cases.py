"""
    TestRail ID - C57594535
    Validate PSGW tool connectivity when PSG deployment is in progress

    TestRail ID - C57592918
    Check PSGW tooling connectivity to vCenter through ping and traceroute

    TestRail ID - C57592919
    Check PSGW tooling connectivity to DO through ping and traceroute

    TestRail ID - C57592920
    Check PSGW tooling connectivity to esxi host through ping and traceroute

    TestRail ID - C57593904
    Validate PSGW tooling connectivity through ping to invalid address

    TestRail ID - C57594158
    Check PSGW tooling connectivity to DNS server through ping and traceroute

    TestRail ID - C57594160
    Check PSGW tooling connectivity to one of the NTP server through ping and traceroute

    TestRail ID - C57594162
    Validate PSGW tooling connectivity to multiple servers simultaneously through ping

    TestRail ID - C57594167
    Validate PSGW tooling connectivity to proxy server through ping

    TestRail ID - C57594536
    Check PSGW tooling connectivity to target backup VM

    TestRail ID - C57594168
    Check PSGW tooling connectivity to PSGW deployed in another vcenter

    TestRail ID - C57594156
    Validate PSGW tooling connectivity with OK and CONNECTED PSGW to UNKNOWN and DISCONNECTED PSGW through ping
    
    TestRail ID - C57592921
    Validate PSGW tooling connectivity when PSG is in OFFLINE state
"""

import logging
from pytest import fixture, mark
from lib.common.error_messages import (
    ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_TO_INVALID_ADDRESS_WITH_BAD_REQUEST,
    ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_WHEN_PSGW_IS_IN_OFFLINE_STATE,
)
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    select_or_create_protection_store_gateway_vm,
    create_protection_store_gateway_vm,
    validate_psgw_tooling_connectivity,
    wait_to_get_psgw_to_powered_off,
    delete_protection_store_gateway_vm_from_vcenter,
    wait_for_psg,
)
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.psg import HealthState, HealthStatus, State
from requests import codes

logger = logging.getLogger()


@fixture(scope="module")
def context():
    context_1 = Context()
    excluded_vcenters = context_1.excluded_vcenters.copy()
    excluded_vcenters.append(context_1.vcenter_name)
    context_2 = Context(excluded_vcenters=excluded_vcenters)
    yield context_1, context_2
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(context_1)
    perform_cleanup(context_2)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(1900)
@mark.dependency()
def test_check_psgw_tooling_connectivity_to_vCenter_through_ping_and_traceroute(context):
    """TestRail ID - C57592918
    Check PSGW tooling connectivity to vCenter through ping and traceroute
    """
    context1 = context[0]
    create_protection_store_gateway_vm(context1)
    logger.info("PSGW created and validated with 0 local protection stores.")
    logger.info("Checking PSGW tooling connectivity to vCenter...")
    validate_psgw_tooling_connectivity(context1, target_address=context1.vcenter_name)


@mark.order(1905)
@mark.dependency()
def test_check_psgw_tooling_connectivity_to_DO_through_ping_and_traceroute(context):
    """TestRail ID - C57592919
    Check PSGW tooling connectivity to DO through ping and traceroute
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    logger.info("Checking PSGW tooling connectivity to DO...")
    validate_psgw_tooling_connectivity(context1, target_address="DO_ip")


@mark.order(1910)
@mark.dependency()
def test_check_psgw_tooling_connectivity_to_esxi_host_through_ping_and_traceroute(context):
    """TestRail ID - C57592920
    Check PSGW tooling connectivity to esxi host through ping and traceroute
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    logger.info("Checking PSGW tooling connectivity to esxi host...")
    validate_psgw_tooling_connectivity(context1, target_address=context1.hypervisor_name)


@mark.order(1915)
@mark.dependency()
def test_validate_psgw_tooling_connectivity_to_invalid_address(context):
    """TestRail ID - C57593904
    Validate PSGW tooling connectivity through ping to invalid address
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    logger.info("Checking PSGW tooling connectivity to invalid address/host...")
    validate_psgw_tooling_connectivity(
        context1, target_address="256.168.0.1", exp_task_err=True, check_traceroute=False
    )


@mark.order(1920)
@mark.dependency()
def test_validate_psgw_tooling_connectivity_to_DNS_server(context):
    """TestRail ID - C57594158
    Check PSGW tooling connectivity to DNS server through ping and traceroute
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    logger.info("Checking PSGW tooling connectivity to DNS server...")
    validate_psgw_tooling_connectivity(context1, target_address=context1.dns)


@mark.order(1925)
@mark.dependency()
def test_validate_psgw_tooling_connectivity_to_NTP_server(context):
    """TestRail ID - C57594160
    Check PSGW tooling connectivity to one of the NTP server through ping and traceroute
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    logger.info("Checking PSGW tooling connectivity to NTP server...")
    validate_psgw_tooling_connectivity(context1, target_address=context1.ntp_server_address)


@mark.order(1930)
@mark.dependency()
def test_validate_psgw_tooling_connectivity_to_multiple_servers_simultaneously(context):
    """TestRail ID - C57594162
    Validate PSGW tooling connectivity to multiple servers simultaneously through ping
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    target_address = f"{context1.dns}, {context1.dns2}"
    exp_res_err = codes.bad_request
    exp_err_msg = ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_TO_INVALID_ADDRESS_WITH_BAD_REQUEST
    logger.info("Checking PSGW tooling connectivity to multiple DNS servers simultaneously...")
    validate_psgw_tooling_connectivity(
        context1,
        target_address=target_address,
        exp_res_err=exp_res_err,
        check_traceroute=False,
        exp_err_msg=exp_err_msg,
    )


@mark.order(1935)
@mark.dependency()
def test_validate_psgw_tooling_connectivity_to_proxy_server(context):
    """TestRail ID - C57594167
    Validate PSGW tooling connectivity to proxy server through ping
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    exp_res_err = codes.bad_request
    exp_err_msg = ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_TO_INVALID_ADDRESS_WITH_BAD_REQUEST
    logger.info("Checking PSGW tooling connectivity to Proxy server...")
    validate_psgw_tooling_connectivity(
        context1,
        target_address=context1.proxy,
        exp_res_err=exp_res_err,
        check_traceroute=False,
        exp_err_msg=exp_err_msg,
    )


@mark.order(1940)
@mark.dependency()
def test_check_psgw_tooling_connectivity_to_target_backup_VM(context):
    """TestRail ID - C57594536
    Check PSGW tooling connectivity to target backup VM
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    logger.info("Checking PSGW tooling connectivity to target backup VM...")
    validate_psgw_tooling_connectivity(context1, target_address="vm_ip")


@mark.order(1945)
@mark.dependency()
def test_validate_psgw_tooling_connectivity_to_PSGW_deployed_in_another_vcenter(context):
    """TestRail ID - C57594168
    Check PSGW tooling connectivity to PSGW deployed in another vcenter
    """
    context1, context2 = context
    select_or_create_protection_store_gateway_vm(context1)
    create_protection_store_gateway_vm(context2, add_data_interface=False, multiple_local_protection_store=0)
    logger.info("Checking PSGW tooling connectivity to PSGW deployed in another vcenter...")
    validate_psgw_tooling_connectivity(context1, target_address=context2.network)


@mark.order(1950)
@mark.dependency(depends=["test_validate_psgw_tooling_connectivity_to_PSGW_deployed_in_another_vcenter"])
def test_validate_psgw_tooling_connectivity_with_OK_PSGW_to_UNKNOWN_PSGW(context):
    """TestRail ID - C57594156
    Validate PSGW tooling connectivity with OK and CONNECTED PSGW to UNKNOWN and DISCONNECTED PSGW through ping
    """
    context1, context2 = context
    # Delete PSG VM from vCenter2
    delete_protection_store_gateway_vm_from_vcenter(context2, force=True)
    logger.info("Checking PSGW tooling connectivity to deleted PSGW from another vcenter...")
    validate_psgw_tooling_connectivity(
        context1, target_address=context2.network, exp_task_err=True, check_traceroute=False
    )


@mark.order(1955)
@mark.dependency()
def test_validate_psgw_tooling_connectivity_when_psgw_is_in_OFFLINE_state(context: Context):
    """TestRail ID - C57592921
    Validate PSGW tooling connectivity when PSG is in OFFLINE state
    """
    context1 = context[0]
    select_or_create_protection_store_gateway_vm(context1)
    logger.info(f"Powering OFF PSGW {context1.psgw_name}...")
    wait_to_get_psgw_to_powered_off(context1)
    exp_res_err = codes.precondition_failed
    exp_err_msg = ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_WHEN_PSGW_IS_IN_OFFLINE_STATE
    logger.info("Checking PSGW tooling connectivity to vcenter...")
    validate_psgw_tooling_connectivity(
        context1, target_address=context1.vcenter_name, exp_res_err=exp_res_err, exp_err_msg=exp_err_msg
    )


@mark.order(1960)
@mark.dependency()
def test_check_psgw_tooling_connectivity_when_PSG_deployment_is_in_progress(context):
    """TestRail ID - C57594535
    Validate PSGW tool connectivity when PSG deployment is in progress
    """
    context1 = context[0]
    response = create_protection_store_gateway_vm(
        context1, add_data_interface=False, return_response=True, multiple_local_protection_store=0
    )
    logger.info(f"Creation of protection store gateway VM response: {response.text}")
    logger.info("Waiting for PSGW to reach DEPLOYING and DISCONNECTED state.")
    wait_for_psg(
        context1, state=State.DEPLOYING, health_state=HealthState.DEPLOYING, health_status=HealthStatus.DISCONNECTED
    )
    exp_res_err = codes.precondition_failed
    exp_err_msg = ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_WHEN_PSGW_IS_IN_OFFLINE_STATE
    logger.info("Checking PSGW tooling connectivity to vCenter...")
    validate_psgw_tooling_connectivity(
        context1, target_address=context1.vcenter_name, exp_res_err=exp_res_err, exp_err_msg=exp_err_msg
    )
