"""
TestRail ID - C57582038 Deletion of PSG associated with Cloud store.
TestRail ID - C57581970 Delete Protection Store which is part of protection template
TestRail ID - C57582037 Delete PSG when local and cloud store has back up
TestRail ID - C57582040 Action-Perform Delete (this test we are covering perform_cleanup in almost all test file so not adding here.)
"""

import logging

from pytest import fixture, mark
from requests import codes
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.azure_locations import AzureLocations
from tests.catalyst_gateway_e2e.test_context import Context
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    verify_delete_psgw_not_allowed_if_backup_exists,
    delete_protection_store_gateway_vm,
    select_or_create_protection_store_gateway_vm,
)
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
    unassign_protecion_policy_from_vm,
    delete_unassinged_protection_policy,
)
from tests.steps.vm_protection.backup_steps import run_backup
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(1000)
@mark.deploy
def test_delete_psgw_with_protection_template(context, vm_deploy, shutdown_all_psgw):
    """
    TestRail ID - C57582038 Deletion of PSG associated with Cloud store.
    TestRail ID - C57581970 Delete Protection Store which is part of protection template
    Args:
        context (Context): object of a context class
        vm_deploy: should provide this parameter when user assign template to a vm
        shutdown_all_psgw: This parameter makes sure all PSGW shutdown
    """
    create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_eastus)
    assign_protection_template_to_vm(context)
    delete_protection_store_gateway_vm(context)
    # this is as part of cleanup for the next testcase test_delete_psgw_with_backup if not add then next test fails
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)


@mark.order(1005)
@mark.deploy
def test_delete_psgw_with_backup(context, vm_deploy):
    """
    TestRail ID - C57582037 Delete PSG when local and cloud store has back up
    Args:
        context (Context): object of a context class
    """
    select_or_create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_eastus2)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    verify_delete_psgw_not_allowed_if_backup_exists(context)
