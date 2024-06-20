"""
    TestRail ID - C57582067
    Deploy Local Protection Store & Gateway VM and initiate basic local back-up & restore workflow 

    TestRail ID - C57582068
    Deploy Local Protection Store & Gateway VM and initiate basic local & cloud back-up & restore workflow
"""

import logging
from pytest import fixture, mark
from time import sleep
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.backup_steps import run_backup, restore_virtual_machine
from tests.steps.vm_protection.psgw_steps import select_or_create_protection_store_gateway_vm
from tests.steps.vm_protection.vcenter_steps import create_vm_and_refresh_vcenter_inventory
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
)
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.restore_type import RestoreType
from tests.catalyst_gateway_e2e.test_context import Context

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(1400)
def test_restore_vm(context):
    """
    TestRail ID - C57582067
    Deploy Local Protection Store & Gateway VM and initiate basic local back-up & restore workflow

    TestRail ID - C57582068
    Deploy Local Protection Store & Gateway VM and initiate basic local & cloud back-up & restore workflow
    """
    select_or_create_protection_store_gateway_vm(context)
    create_vm_and_refresh_vcenter_inventory(context)
    create_protection_template(
        context, cloud_region=AzureLocations.AZURE_koreacentral, onprem_expire_value=7, cloud_expire_value=10
    )
    assign_protection_template_to_vm(context)
    run_backup(context)
    restore_virtual_machine(context, RestoreType.new, "snapshot")
    restore_virtual_machine(context, RestoreType.new, "local")
    restore_virtual_machine(context, RestoreType.new, "cloud")
    restore_virtual_machine(context, RestoreType.existing, "snapshot")
    sleep(360)
    context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
    restore_virtual_machine(context, RestoreType.existing, "local")
    sleep(360)
    context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
    restore_virtual_machine(context, RestoreType.existing, "cloud")
    context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
