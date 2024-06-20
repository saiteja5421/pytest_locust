"""
TestRail ID - C57582089:
    Deploy Protection Store Gateway with network Mgmt only(VLAN1) subnet and add additional network
    interface as data only subnets(VLAN2 & VLAN3) (Happy Path)
TestRail ID - C57582094:
    Modify IP of Protection Store Gateway
TestRail ID - C57582105:
    Add additional fourth network interface for Protection Store Gateway
TestRail ID - C57582102:
    Delete the Protection Store Gateway's network interface 1
TestRail ID - C57582092:
    Delete the additional network interfaces to Protection Store Gateway deployed with Mgmt
    only (VLAN1) Network and perform backups
"""

import logging
from pytest import fixture, mark
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.azure_locations import AzureLocations
from lib.common.enums.network_interface_type import NetworkInterfaceType
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.backup_steps import run_backup
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
    unassign_protecion_policy_from_vm,
    delete_unassinged_protection_policy,
)
from tests.steps.vm_protection.psgw_steps import (
    check_and_register_unregister_expected_data_nics,
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    add_additional_network_interface_catalyst_gateway_vm,
    update_network_interface_catalyst_gateway_vm,
    delete_network_interface_catalyst_gateway_vm,
    add_fourth_network_interface_and_verify_error,
    select_or_create_protection_store_gateway_vm,
    validate_psg_configured_with_given_nics_count,
    validate_error_msg_when_psg_deploy_only_with_data_nic,
    update_two_network_interface_catalyst_gateway_vm,
)
from utils.ip_utils import find_unused_ip_from_range

logger = logging.getLogger()


def cleanup(context):
    """
    This method performs unassign and delete of protection template and performs cleanup as part of teardown
    Args:
        context (Context): object of a context class
    """
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    perform_cleanup(context)


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


def _create_protection_and_run_backup(context, cloud_region):
    """this method performs create and assign protection template and run backup and unassign and delete protection template.
    This is a local method which we are using in multiple testcases in this test files and not using any assertions so keeping it here.
    Args:
        context (Context): object of a context class
        cloud_region (string): cloud region on which protection template need to create
    """
    create_protection_template(context, cloud_region)
    assign_protection_template_to_vm(context)
    run_backup(context)
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)


@mark.order(1100)
@mark.split_network
@mark.deploy
def test_deploy_psg_with_multipath_network_interfaces(context, vm_deploy):
    """
    TestRail ID - C57582089:
    Deploy Protection Store Gateway with network Mgmt only subnet and add additional network
    interface as data only subnets (Happy Path)
    Args:
        context (Context): object of a context class
        vm_deploy (vm_deploy): this parameter is required to deploy vm
    """
    # Deploy PSG with MGMT Only interface (VM Network)
    create_protection_store_gateway_vm(context, add_data_interface=False)
    validate_protection_store_gateway_vm(context)

    # Verify protection policy creation successful
    create_protection_template(context, cloud_region=AzureLocations.AZURE_francecentral)
    delete_unassinged_protection_policy(context)

    # Add additonal DATA interface (Data1) & protect a VM
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data1)
    _create_protection_and_run_backup(context, cloud_region=AzureLocations.AZURE_germanywestcentral)

    # Add additonal DATA interface (Data2) & Protect a VM
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data2)
    _create_protection_and_run_backup(context, cloud_region=AwsStorageLocation.AWS_US_WEST_2)


@mark.order(1105)
@mark.split_network
def test_modify_two_data_nics_of_psgw(context):
    """
    TestRail ID - C57582094:
    Modify IP of Protection Store Gateway
    Args:
        context (Context): object of a context class
    """
    # Check if NICs amount is expected from previous TC - if not add/remove
    check_and_register_unregister_expected_data_nics(context, [NetworkInterfaceType.data1, NetworkInterfaceType.data2])

    # Update DATA interface (Data1)
    nic = context.nic_data1
    network_address1 = find_unused_ip_from_range(nic["additional_network_address1"])
    update_network_interface_catalyst_gateway_vm(
        context,
        current_address=context.nic_data1_ip,
        network_address=network_address1,
        network_name=nic["network_name"],
        network_type=nic["network_type"],
        netmask=nic["netmask"],
    )
    (
        context.nic_data1_ip,
        network_address1,
    ) = (
        network_address1,
        context.nic_data1_ip,
    )

    # Update DATA interface (Data1)
    nic = context.nic_data2
    network_address2 = find_unused_ip_from_range(nic["additional_network_address1"])
    update_network_interface_catalyst_gateway_vm(
        context,
        current_address=context.nic_data2_ip,
        network_address=network_address2,
        network_name=nic["network_name"],
        network_type=nic["network_type"],
        netmask=nic["netmask"],
    )
    (
        context.nic_data2_ip,
        network_address2,
    ) = (
        network_address2,
        context.nic_data2_ip,
    )

    # Post network update protect a VM
    _create_protection_and_run_backup(context, cloud_region=AwsStorageLocation.AWS_EU_CENTRAL_1)


@mark.order(1110)
@mark.split_network
def test_delete_psg_mgmt_interface_at_multiple_instances(context):
    """
    TestRail ID - C57582102:
    Delete the Protection Store Gateway's network interface 1
    At any situation App should not allow to delete MGMT interface
    Args:
        context (Context): object of a context class
    """
    # Check if NICs amount is expected from previous TC - if not add/remove
    check_and_register_unregister_expected_data_nics(context, [NetworkInterfaceType.data1, NetworkInterfaceType.data2])

    # Delete DATA interface (Data1) - This should be allowed
    delete_network_interface_catalyst_gateway_vm(context, context.nic_data1_ip)

    # Delete DATA interface (Data2) - This should be allowed
    delete_network_interface_catalyst_gateway_vm(context, context.nic_data2_ip)

    # Delete MGMT interface (VM Network) - Expected to FAIL since its not permitted
    delete_network_interface_catalyst_gateway_vm(
        context, context.nic_primary_interface["network_address"], expect_to_fail=True
    )

    # Add additonal DATA interface (Data1) and then validate are we allowed to remove MGMT interface (VM Network)
    # This is not permitted since at any instance app shouldn't allow to delete MGMT interface
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data1)
    delete_network_interface_catalyst_gateway_vm(
        context, context.nic_primary_interface["network_address"], expect_to_fail=True
    )

    # Same removal of MGMT interface to be verified post addition of DATA interface (Data2)
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data2)
    delete_network_interface_catalyst_gateway_vm(
        context, context.nic_primary_interface["network_address"], expect_to_fail=True
    )

    # Post addition/deletion protect a VM
    _create_protection_and_run_backup(context, cloud_region=AwsStorageLocation.AWS_EU_CENTRAL_1)


@mark.order(1115)
@mark.split_network
def test_delete_psg_data_interface(context):
    """
    TestRail ID - C57582092:
    Delete the additional network interfaces to Protection Store Gateway deployed with Mgmt
    only (VLAN1) Network and perform backups
    Args:
        context (Context): object of a context class
    """
    # Check if NICs amount is expected from previous TC - if not add/remove
    check_and_register_unregister_expected_data_nics(context, [NetworkInterfaceType.data1, NetworkInterfaceType.data2])

    # Delete DATA interface (Data1) and protect a VM to verify backup should work with another DATA interface Data2
    delete_network_interface_catalyst_gateway_vm(context, context.nic_data1_ip)
    _create_protection_and_run_backup(context, cloud_region=AzureLocations.AZURE_japaneast)

    # Add Data1 back to the PSG and delete Data2 and then protect a VM to verify backup
    # should work with another DATA interface Data1
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data1)
    delete_network_interface_catalyst_gateway_vm(context, context.nic_data2_ip)
    _create_protection_and_run_backup(context, cloud_region=AwsStorageLocation.AWS_EU_CENTRAL_1)


@mark.order(1120)
@mark.split_network
def test_add_fourth_nic(context, vm_deploy):
    """
    TestRail ID - C57582105:
    Add additional fourth network interface for Protection Store Gateway
    Args:
        context (Context): object of a context class
        vm_deploy (Context): this parameter is required to deploy vm
    """
    select_or_create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    check_and_register_unregister_expected_data_nics(context, [NetworkInterfaceType.data1])
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data2)
    validate_psg_configured_with_given_nics_count(context, 3)
    add_fourth_network_interface_and_verify_error(context)


@mark.order(1125)
def test_deploy_PSG_with_only_data_nic(context):
    """
    TestRail ID - C57582103:
    Create Protection Store Gateway with Data only configured network

    """
    validate_error_msg_when_psg_deploy_only_with_data_nic(context)
    logger.info("Performing cleanup to freeup NIC IP for next test case.")
    perform_cleanup(context, clean_vm=False)


@mark.order(1130)
@mark.dependency()
def test_modify_two_nics_at_the_same_time(context):
    """
    TestRail ID - C57582095:
    Modify two NICs at the same time
    """
    create_protection_store_gateway_vm(context)
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data2)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_US_EAST_2)
    assign_protection_template_to_vm(context)
    run_backup(context)
    nic1 = context.nic_data1
    nic2 = context.nic_data2
    network_address1 = find_unused_ip_from_range(nic1["additional_network_address1"])
    network_address2 = find_unused_ip_from_range(nic2["additional_network_address1"])
    update_two_network_interface_catalyst_gateway_vm(
        context,
        current_address1=context.nic_data1_ip,
        network_address1=network_address1,
        network_name1=nic1["network_name"],
        network_type1=nic1["network_type"],
        netmask1=nic1["netmask"],
        current_address2=context.nic_data2_ip,
        network_address2=network_address2,
        network_name2=nic2["network_name"],
        network_type2=nic2["network_type"],
        netmask2=nic2["netmask"],
    )
    run_backup(context)
