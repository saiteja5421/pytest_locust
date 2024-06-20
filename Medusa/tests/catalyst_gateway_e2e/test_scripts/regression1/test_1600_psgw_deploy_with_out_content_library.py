"""
TestRail ID - C57581935:
    Deploy protection store gateway VM with no image in the content library

TestRail ID - C57582306:
    Unable to deploy PSG - Error: OVA Upload to Content Library is already in progress by another request-(ESC-10716)
"""

import logging
from requests import codes

from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations

from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.restore_type import RestoreType
from lib.common.enums.aws_regions import AwsStorageLocation
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    validate_protection_store_gateway_vm,
    select_or_create_protection_store_gateway_vm,
    validate_deploy_psgw_when_upload_to_content_library_is_already_in_progress,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    restore_virtual_machine,
)
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
)
from tests.catalyst_gateway_e2e.test_context import Context

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(1600)
@mark.deploy
def test_validate_deploy_psgw_when_upload_to_content_library_is_already_in_progress(context, vm_deploy):
    """TestRail ID - C57582306:
    Unable to deploy PSG - Error: OVA Upload to Content Library is already in progress by another request-(ESC-10716)
    """
    validate_deploy_psgw_when_upload_to_content_library_is_already_in_progress(context)


@mark.order(1605)
@mark.deploy
def test_validate_deploy_psgw_with_out_content_library(context):
    """TestRail ID - C57581935:
    Deploy protection store gateway VM with no image in the content library
    """
    select_or_create_protection_store_gateway_vm(
        context,
        clear_content_library=True,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_polandcentral)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    restore_virtual_machine(context, RestoreType.new, "local")
