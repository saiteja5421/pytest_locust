"""
TestRail ID: C57581937
    Deploy Protection Store Gateway VM by registering new vCenter

TestRail ID: C57581954
    Validate Max allowed Local Protection Store Size

TestRail ID: C57581973
    Delete Protection Store Gateway VM and create a new one with same name

TestRail ID: C57582225
    Validate PSGW deployment with morethan supported capacity using override params

TestRail ID - C57582221
    Validate-PSGW-Sizer-fields-override-functionality

TestRail ID - C57582222
    Validate-PSGW-error-cases-for-override-flag
"""

import logging
import random

from pytest import fixture, mark
from requests import codes
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.azure_locations import AzureLocations
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.restore_type import RestoreType
from lib.common.error_messages import (
    ERROR_MESSAGE_OVERRIDE_STORAGE,
    ERROR_MESSAGE_OVERRIDE_CPU,
    ERROR_MESSAGE_OVERRIDE_RAM,
    ERROR_MESSAGE_OVERRIDE_STORAGE,
)
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    validate_psgw_error_messages,
    validate_the_override_functionality,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    restore_virtual_machine,
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


@mark.deploy
@mark.order(300)
def test_validate_psgw_error_cases_override_flag(context):
    """TestRail ID - C57582222
    Validate-PSGW-error-cases-for-override-flag
    """
    logger.info("***Validating min. cpu on override error messages***")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        override_cpu=1,
        override_ram_gib=24,
        override_storage_tib=1,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_CPU,
    )
    logger.info("***Successfully validated  min. cpu on override error messages***")
    logger.info("***Validating max. cpu on override error messages***")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        override_cpu=random.randint(49, 100),
        override_ram_gib=24,
        override_storage_tib=1,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_CPU,
    )
    logger.info("***Successfully validated  max. cpu on override error messages***")
    logger.info("***Validating min. ram on override error messages***")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        override_cpu=8,
        override_ram_gib=random.randint(0, 15),
        override_storage_tib=1,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_RAM,
    )
    logger.info("***Successfully validated  min. ram on override error messages***")
    logger.info("***Validating max. ram on override error messages***")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        override_cpu=8,
        override_ram_gib=random.randint(501, 1000),
        override_storage_tib=1,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_RAM,
    )
    logger.info("***Successfully validated  max. ram on override error messages***")
    logger.info("***Validating min. storage on override error messages***")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        override_cpu=8,
        override_ram_gib=24,
        override_storage_tib=0,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_STORAGE,
    )
    logger.info("***Successfully validated  min. storage on override error messages***")
    logger.info("***Validating max. storage on override error messages***")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        override_cpu=8,
        override_ram_gib=24,
        override_storage_tib=random.randint(501, 1000),
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_STORAGE,
    )
    logger.info("***Successfully validated max. storage on override error messages***")


@mark.order(305)
@mark.deploy
def test_reregiter_vc_deploy_psgw_with_max_capacity(context, clean_start_reregister_vcenters, vm_deploy):
    """TestRail ID - C57581937:
    Deploy Protection Store Gateway VM by registering the vCenter

    TestRail ID - C57582221
    Validate-PSGW-Sizer-fields-override-functionality
    """
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    logger.warning(
        f"We need to create datastores to accomodate psgw capacity and datastore name must contains: {additional_ds_name} on vCenter: {context.vcenter_name} otherwise test expected to fail"
    )
    override_cpu = 28
    override_ram_gib = 150
    override_storage_tib = 500
    create_protection_store_gateway_vm(
        context,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_US_WEST_2)
    validate_the_override_functionality(
        context,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
    )
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.local)


@mark.order(310)
@mark.deploy
def test_deploy_psgw_with_morethan_max_capacity_using_override(context):
    """TestRail ID: C57582225
    Validate PSGW deployment with morethan supported capacity using override params
    """
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    logger.warning(
        f"We need to create datastores to accomodate psgw capacity and datastore name must contains: {additional_ds_name} on vCenter: {context.vcenter_name} otherwise test expected to fail"
    )
    response = create_protection_store_gateway_vm(
        context,
        override_cpu=28,
        override_ram_gib=150,
        override_storage_tib=501,
        return_response=True,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_STORAGE,
    )


@mark.deploy
@mark.order(315)
def test_delete_psgw_redeploy_with_same_content(context):
    """TestRail ID: C57581973
    Delete Protection Store Gateway VM and create a new one with same name
    """
    perform_cleanup(
        context,
        clean_vm=False,
        clean_psgw=True,
    )
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    logger.warning(
        f"We need to create datastores to accomodate psgw capacity and datastore name must contains: {additional_ds_name} on vCenter: {context.vcenter_name} otherwise test expected to fail"
    )
    create_protection_store_gateway_vm(
        context,
        override_cpu=28,
        override_ram_gib=150,
        override_storage_tib=500,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_australiaeast)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.local)
    restore_virtual_machine(context, RestoreType.existing, "local", quite_time=120)
