"""
    TestRail ID - C57581982
    Create Cloud Store using Protection template - different regions same vcenter

    TestRail ID - C57581986
    Create Cloud Store using Protection Template - same vcenter- same region

    TestRail ID - C57581983
    Create Cloud Store using Protection template-same region different vcenter

    TestRail ID - C57581984
    Create Cloud Store using Protection template-different region different vcenter
"""

import logging
import random
import string
import time
import pytest
from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    unassign_protecion_policy_from_vm,
    assign_protection_template_to_vm,
    delete_unassinged_protection_policy,
    delete_unassinged_protection_policy_list,
)
from tests.steps.vm_protection.backup_steps import run_backup_and_check_usage
from tests.steps.vm_protection.psgw_steps import (
    select_or_create_protection_store_gateway_vm,
)
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from tests.catalyst_gateway_e2e.test_context import Context

logger = logging.getLogger()


def cleanup(context):
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy_list(context, context.template_list)
    perform_cleanup(context)


@fixture(scope="module")
def context():
    context_1 = Context(v_center_type="VCENTER1")
    context_2 = Context(v_center_type="VCENTER2")
    context_2.psgw_name += f"_{context_2.secondary_psgw_ip}"
    context_2.network = context_2.secondary_psgw_ip
    context_2.nic_primary_interface["network_address"] = context_2.nic_primary_interface["additional_network_address1"]
    policy_suffix = "".join(random.choice(string.ascii_letters) for _ in range(10))
    policy_name = context_1.test_data["policy_name"]
    policy_name = context_2.test_data["policy_name"]
    context_1.template_list = [f"{policy_name}_{policy_suffix}_1", f"{policy_name}_{policy_suffix}_2"]
    context_2.template_list = [f"{policy_name}_{policy_suffix}_1", f"{policy_name}_{policy_suffix}_2"]
    yield context_1, context_2
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(context_1)
    perform_cleanup(context_2)
    logger.info("Teardown Complete".center(20, "*"))


def _create_protection_templete_and_take_backup_unassign(context, region):
    """this is commonly using in multiple tests so keepingg it here.

    Args:
        context (Context): Context Object
        region (AwsStorageLocation): cloud region on which protection template has to create.
    """
    create_protection_template(context, cloud_region=region)
    assign_protection_template_to_vm(context)
    run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.cloud)
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)


@pytest.mark.parametrize(
    "region1, region2",
    [
        (AwsStorageLocation.AWS_US_WEST_2, AwsStorageLocation.AWS_US_EAST_2),
        (AzureLocations.AZURE_uksouth, AzureLocations.AZURE_uksouth),
    ],
)
@mark.order(2700)
def test_creation_of_cloud_protection_on_same_vcenter(context: Context, region1, region2, vm_deploy):
    """
    TestRail ID - C57581982
    Create Cloud Store using Protection template-different regions same vcenter

    TestRail ID - C57581986
    Create Cloud Store using Protection Template - same vcenter- same region
    """
    context1, context2 = context
    select_or_create_protection_store_gateway_vm(context1, add_data_interface=False)
    # run backup on region1
    context1.local_template = context1.template_list[0]
    _create_protection_templete_and_take_backup_unassign(context1, region1)
    time.sleep(30)
    # run backup on region2
    context1.local_template = context1.template_list[1]
    _create_protection_templete_and_take_backup_unassign(context1, region2)


@pytest.mark.parametrize(
    "region1, region2",
    [
        (AzureLocations.AZURE_uksouth, AzureLocations.AZURE_uksouth),  # TC 57
        (AwsStorageLocation.AWS_US_WEST_2, AwsStorageLocation.AWS_US_EAST_2),  # TC 58
    ],
)
@mark.order(2705)
def test_creation_of_cloud_protection_on_different_vcenter(context: Context, region1, region2, vm_deploy):
    """
    TestRail ID - C57581983
    Create Cloud Store using Protection template-same region different vcenter

    TestRail ID - C57581984
    Create Cloud Store using Protection template-different region different vcenter
    """
    context1, context2 = context
    unassign_protecion_policy_from_vm(context1)
    delete_unassinged_protection_policy_list(context1, context1.template_list)
    select_or_create_protection_store_gateway_vm(context1, add_data_interface=False)
    context1.local_template = context1.template_list[0]
    _create_protection_templete_and_take_backup_unassign(context1, region1)
    unassign_protecion_policy_from_vm(context2)
    delete_unassinged_protection_policy_list(context2, context2.template_list)
    select_or_create_protection_store_gateway_vm(context2)
    context2.local_template = context2.template_list[1]
    _create_protection_templete_and_take_backup_unassign(context2, region2)
