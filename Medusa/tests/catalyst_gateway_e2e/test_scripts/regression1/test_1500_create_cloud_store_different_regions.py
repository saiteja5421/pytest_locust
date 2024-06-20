"""
    TestRail ID - C57581985
    Create more than two Cloud Store using Protection template-different regions same vcenter
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
    test_context = Context()
    policy_suffix = "".join(random.choice(string.ascii_letters) for _ in range(10))
    policy_name = test_context.test_data["policy_name"]
    test_context.template_list = [
        f"{policy_name}1_{policy_suffix}",
        f"{policy_name}2_{policy_suffix}",
        f"{policy_name}3_{policy_suffix}",
    ]
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@pytest.mark.parametrize(
    "region1, region2, region3",
    [
        (AzureLocations.AZURE_northeurope, AzureLocations.AZURE_norwayeast, AwsStorageLocation.AWS_EU_WEST_2),  # TC 59
    ],
)
@mark.order(1500)
def test_create_more_cloud_store(context, region1, region2, region3, vm_deploy):
    """
    TestRail ID - C57581985
    Create more than two Cloud Store using Protection template-different regions same vcenter
    """
    select_or_create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
    )
    # run backup on region1
    context.local_template = context.template_list[0]
    create_protection_template(context, cloud_region=region1)
    assign_protection_template_to_vm(context)
    run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.cloud)
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    time.sleep(60)
    # run backup on region2
    context.local_template = context.template_list[1]
    create_protection_template(context, cloud_region=region2)
    assign_protection_template_to_vm(context)
    run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.cloud, multiple_stores=True)
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    time.sleep(60)
    # run backup on region3
    context.local_template = context.template_list[2]
    create_protection_template(context, cloud_region=region3)
    assign_protection_template_to_vm(context)
    run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.cloud, multiple_stores=True)
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
