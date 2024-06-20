"""
TC75: Monitor local storage after backup
TC76: Monitor local storage after backup deletion
TC79: Monitor cloud storage after backup
TC80: Monitor cloud storage after backup deletion
"""
import logging

from pytest import fixture, mark


from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    unassign_protecion_policy_from_vm,
    create_protection_template,
    assign_protection_template_to_vm,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
)
from tests.steps.vm_protection.backup_steps import run_backup_and_check_usage, delete_backup_and_check_usage
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.aws_regions import AWSRegions

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(skip_inventory_exception=True)
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context, clean_vm=False)
    logger.info("Teardown Complete".center(20, "*"))


@mark.skip(reason="delete backup sho metrics of totalDiskBytes increased")
@mark.order(750)
def test_tc75_tc76_tc79_tc80(context):
    create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AWSRegions.AWS_US_EAST_1)
    for name in context.vm_name_size_monitoring_list:
        context.vm_name = name
        context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
        assign_protection_template_to_vm(context)
        run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.cloud)
        delete_backup_and_check_usage(context, backup_type=BackupTypeScheduleIDs.cloud)
        unassign_protecion_policy_from_vm(context)
