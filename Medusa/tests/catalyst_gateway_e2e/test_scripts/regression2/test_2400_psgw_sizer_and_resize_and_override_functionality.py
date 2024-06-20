"""
TestRail ID - 	C57582182
    Validate the PSGW Resize, size wizard moderate values for maxDailyProtectedDataTiB, maxLocalRetentionDays and
    maxCloudRetentionDays

TestRail ID - 	C57582183
    Validate PSGW Resize, size wizard error cases for maxDailyProtectedDataTiB, maxLocalRetentionDays and
    maxCloudRetentionDays
    
TestRail ID - C57582185
    Execute the size wizard error cases tests together and observe the behavior of Required resources
    (such as vCpu, Memory, Storage Capacity and Storage iops)

TestRail ID - C57582188
    Validate Resize PSGW functionality

TestRail ID - C57582194
    Validate the resize operation of a PSG with a protection workflow

TestRail ID - C57582191
    Resize a PSG when PSG is in power off state

TestRail ID - C57582197
    Validate PSG state, During and after PSG storage expansion.

TestRail ID - C57582199 
    Validate the PSGW scale up operation with some backups in the local/cloud store

TestRail ID - C57582186
    Validate the PSGW Resize, datastore wizard

TestRail ID - C57582189
    Validate the scale up storage capacity of a PSG with bunch of datastores and with mixed capacities

TestRail ID - C57582202
    Validate the PSGW scale up operation with the datastores already in use

TestRail ID - C57582207 
    Validate-PSGW-Sizer-fields-override-functionality

TestRail ID - C57582208 
    Validate-PSGW-error-cases-for-override-flag

TestRail ID - C57582206
    Validate-PSGW-Resize-with-equal-storage-capacity

TestRail ID - C57582203
    Validate-PSGW-resize-with-lesser-capacity-than-existing

TestRail ID - C57582210
    Validate-PSGW-resize-by-modifying-Vcenter-creds-with-admin-privilage
"""

import logging
import random
from pytest import fixture, mark
from requests import codes
from lib.common.enums.azure_locations import AzureLocations
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    validate_psgw_sizer_fields,
    validate_psgw_sizer_fields_error_messages,
    select_or_create_protection_store_gateway_vm,
    validate_existing_psgw_resize_functionality,
    validate_psgw_resources_post_update,
    validate_psg_health_state_along_with_resize,
    wait_to_get_psgw_to_powered_off,
    get_existing_psgw_resize_req_response,
    get_resize_psg_task_status,
    validate_the_override_functionality,
    validate_psgw_error_messages,
)
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    restore_virtual_machine,
)
from tests.steps.vm_protection.vcenter_steps import change_vcenter_credentials
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.restore_type import RestoreType
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.error_messages import (
    ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA,
    ERROR_MESSAGE_INVALID_CLOUD_PRTCTD_DATA_FIELD_STRING,
    ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_STRING,
    ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_FLOAT,
    ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    ERROR_MESSAGE_INVALID_ONPREM_PRTCTD_DATA_FIELD_STRING,
    ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_STRING,
    ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_FLOAT,
    ERROR_MESSAGE_OVERRIDE_CPU,
    ERROR_MESSAGE_OVERRIDE_RAM,
    ERROR_MESSAGE_OVERRIDE_STORAGE,
    ERROR_RESIZE_PSGW_EQUAL_STORAGE,
    ERROR_RESIZE_PSGW_LESSER_STORAGE,
)
from tests.catalyst_gateway_e2e.test_context import Context

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    change_vcenter_credentials(test_context, test_context.vcenter_username, test_context.vcenter_password)
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.resize
@mark.order(2400)
def test_valildate_psgw_moderate_size_fields(context):
    """
    TestRail ID - C57582182
    Validate the PSGW Resize, size wizard moderate values for maxDailyProtectedDataTiB, maxLocalRetentionDays and
      maxCloudRetentionDays
    """
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
    )
    validate_protection_store_gateway_vm(context)
    validate_psgw_sizer_fields(
        context,
        max_cld_dly_prtctd_data=10,
        max_cld_rtn_days=999,
        max_onprem_dly_prtctd_data=38.0,
        max_onprem_rtn_days=500,
        exp_required_fields={
            "vCpu": 16,
            "ramInGiB": 32,
            "iops": 1000,
            "storageInTiB": 77,
            "bandwidthMegabitsPerSecond": 153,
        },
    )
    validate_psgw_sizer_fields(
        context,
        max_cld_dly_prtctd_data=25,
        max_cld_rtn_days=2000,
        max_onprem_dly_prtctd_data=78.0,
        max_onprem_rtn_days=1000,
        exp_required_fields={
            "vCpu": 32,
            "ramInGiB": 64,
            "iops": 2000,
            "storageInTiB": 198,
            "bandwidthMegabitsPerSecond": 382,
        },
    )


@mark.resize
@mark.order(2405)
def test_valildate_psgw_size_fields_error_cases(context):
    """
    TestRail ID - C57582183
    Validate PSGW Resize, size wizard error cases for maxDailyProtectedDataTiB, maxLocalRetentionDays and
      maxCloudRetentionDays
    """
    logger.info("***Validating max cloud daily protected data field error messages***")
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
    )
    validate_protection_store_gateway_vm(context)
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_dly_prtctd_data=0,
        exp_error_msg=ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_dly_prtctd_data=31,
        exp_error_msg=ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_dly_prtctd_data="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_PRTCTD_DATA_FIELD_STRING,
    )
    logger.info("***Successfully validated max cloud daily protected data field error messages***")
    logger.info("***Validating max cloud retention field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_rtn_days=0,
        exp_error_msg=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_rtn_days=3651,
        exp_error_msg=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_rtn_days="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_STRING,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_rtn_days=10.0,
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_FLOAT,
    )
    logger.info("***Successfully validated max cloud retention field error messages***")
    logger.info("***Validating max onprem daily protected data field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_dly_prtctd_data=0,
        exp_error_msg=ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_dly_prtctd_data=101,
        exp_error_msg=ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_dly_prtctd_data="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_PRTCTD_DATA_FIELD_STRING,
    )
    logger.info("***Successfully validated max onprem daily protected data field error messages***")
    logger.info("***Validating max onprem retention field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_rtn_days=0,
        exp_error_msg=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_rtn_days=2556,
        exp_error_msg=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_rtn_days="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_STRING,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_rtn_days=12.90,
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_FLOAT,
    )
    logger.info("***Successfully validated max onprem retention field error messages***")


@mark.resize
@mark.order(2410)
def test_valildate_resize_psgw_functionality(context):
    """
    TestRail ID - C57582188
    Validate Resize PSGW functionality
    """
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
    )
    validate_protection_store_gateway_vm(context)
    max_cld_dly_prtctd_data = 10.0
    max_cld_rtn_days = 450
    max_onprem_dly_prtctd_data = 15.0
    max_onprem_rtn_days = 499
    validate_existing_psgw_resize_functionality(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )


@mark.resize
@mark.order(2415)
def test_validate_psgw_resize_with_protection_workflow(context, vm_deploy):
    """
    TestRail ID - C57582194
    Validate the resize operation of a PSG with a protection workflow
    """
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=450,
        max_onprem_dly_prtctd_data=15.0,
        max_onprem_rtn_days=499,
    )
    validate_protection_store_gateway_vm(context)
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    max_cld_dly_prtctd_data = 18.0
    max_cld_rtn_days = 900
    max_onprem_dly_prtctd_data = 35.0
    max_onprem_rtn_days = 490
    logger.warning(
        f"We need to create datastores to accomodate psgw storage capcity and datastore name must contains: \
            {additional_ds_name}, otherwise test expected to fail"
    )
    validate_existing_psgw_resize_functionality(
        context,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_WEST_2)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    restore_virtual_machine(context, RestoreType.new, "local")
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)


@mark.resize
@mark.order(2420)
def test_validate_psgw_resize_when_shutdown(context):
    """
    TestRail ID - C57582191
    Resize a PSG when PSG is in power off state
    """
    select_or_create_protection_store_gateway_vm(
        context,
        override_cpu=26,
        override_ram_gib=54,
        override_storage_tib=19,
    )
    validate_protection_store_gateway_vm(context)
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    max_cld_dly_prtctd_data = 20.0
    max_cld_rtn_days = 1600
    max_onprem_dly_prtctd_data = 57.0
    max_onprem_rtn_days = 670
    logger.warning(
        f"We need to create datastores to accomodate psgw storage capcity and datastore name must contains: \
            {additional_ds_name}, otherwise test expected to fail"
    )
    wait_to_get_psgw_to_powered_off(context)
    validate_existing_psgw_resize_functionality(
        context,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )


@mark.resize
@mark.order(2425)
def test_validate_psgw_state_during_resize(context):
    """
    TestRail ID - C57582197
    Validate PSG state, During and after PSG storage expansion.
    """
    select_or_create_protection_store_gateway_vm(
        context,
        override_cpu=39,
        override_ram_gib=49,
        override_storage_tib=59,
    )
    validate_protection_store_gateway_vm(context)
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    max_cld_dly_prtctd_data = 24.0
    max_cld_rtn_days = 1955
    max_onprem_dly_prtctd_data = 63.0
    max_onprem_rtn_days = 790
    logger.warning(
        f"We need to create datastores to accomodate psgw storage capcity and datastore name must \
            contains: {additional_ds_name}, otherwise test expected to fail"
    )
    response = get_existing_psgw_resize_req_response(
        context,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_psg_health_state_along_with_resize(context)
    get_resize_psg_task_status(context, response)
    validate_psg_health_state_along_with_resize(context, post_resize_state=True)
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )


@mark.resize
@mark.order(2430)
@mark.dependency()
def test_validate_psgw_resize_with_backups_in_local_store(context):
    """TestRail ID - C57582199
    Validate the PSGW scale up operation with some backups in the local/cloud store.
    """
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_uaenorth)
    assign_protection_template_to_vm(context)
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    max_cld_dly_prtctd_data = 30.0
    max_cld_rtn_days = 2433
    max_onprem_dly_prtctd_data = 80.0
    max_onprem_rtn_days = 1000
    logger.warning(
        f"We need to create datastores to accomodate psgw storage capcity and datastore name must \
            contains: {additional_ds_name}, otherwise test expected to fail"
    )
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    validate_existing_psgw_resize_functionality(
        context,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    restore_virtual_machine(context, RestoreType.new, "local")
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)
    perform_cleanup(context)


@mark.resize
@mark.order(2435)
def test_validate_resize_psgw_error_cases_for_override_flag(context):
    """
    TestRail ID - C57582208
    Validate-PSGW-error-cases-for-override-flag

    TestRail ID - C57582203
    Validate-PSGW-resize-with-lesser-capacity-than-existing
    """
    logger.info("***Validating min. storage on override error messages***")
    response = create_protection_store_gateway_vm(
        context,
        override_cpu=8,
        override_ram_gib=24,
        override_storage_tib=0,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_STORAGE,
    )
    logger.info("***Successfully validated  min. storage on override error messages***")
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
        override_cpu=16,
        override_ram_gib=24,
        override_storage_tib=16,
    )
    validate_protection_store_gateway_vm(context)
    logger.info("***Validating max. storage on override error messages***")
    response = get_existing_psgw_resize_req_response(
        context,
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
    logger.info("***Validating min. cpu on override error messages***")
    response = get_existing_psgw_resize_req_response(
        context,
        override_cpu=1,
        override_ram_gib=24,
        override_storage_tib=16,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_CPU,
    )
    logger.info("***Successfully validated  min. cpu on override error messages***")
    logger.info("***Validating max. cpu on override error messages***")
    response = get_existing_psgw_resize_req_response(
        context,
        override_cpu=random.randint(49, 100),
        override_ram_gib=24,
        override_storage_tib=16,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_CPU,
    )
    logger.info("***Successfully validated  max. cpu on override error messages***")
    logger.info("***Validating min. ram on override error messages***")
    response = get_existing_psgw_resize_req_response(
        context,
        override_cpu=8,
        override_ram_gib=random.randint(0, 15),
        override_storage_tib=16,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_RAM,
    )
    logger.info("***Successfully validated  min. ram on override error messages***")
    logger.info("***Validating max. ram on override error messages***")
    response = get_existing_psgw_resize_req_response(
        context,
        override_cpu=8,
        override_ram_gib=random.randint(501, 1000),
        override_storage_tib=16,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_RAM,
    )
    logger.info("***Successfully validated  max. ram on override error messages***")
    logger.info("***Validating resize psg resize with lesser capacity than existing***")
    response = get_existing_psgw_resize_req_response(
        context,
        override_cpu=8,
        override_ram_gib=26,
        override_storage_tib=1,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_RESIZE_PSGW_LESSER_STORAGE,
    )
    logger.info("***Successfully validated psgw resize error messages***")


@mark.resize
@mark.order(2440)
@mark.dependency()
def test_validate_psgw_resize_with_equal_storage(context):
    """
    TestRail ID - C57582206
        Validate-PSGW-Resize-with-equal-storage-capacity
    """
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
        override_cpu=16,
        override_ram_gib=24,
        override_storage_tib=16,
    )
    atlas = CatalystGateway(context.user)
    psg_size = atlas.psgw_total_disk_size_tib(context.psgw_name)
    logger.info(f"Existing PSGW storage capacity: {psg_size}")
    psg_compute_info = atlas.psgw_compute_info(context.user, context.psgw_name)
    logger.info(f"Existing PSGW compute capacity: {psg_compute_info}")
    response = get_existing_psgw_resize_req_response(
        context,
        override_cpu=psg_compute_info["numCpuCores"],
        override_ram_gib=int(float(psg_compute_info["memorySizeInMib"]) / 1024),
        override_storage_tib=psg_size,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_RESIZE_PSGW_EQUAL_STORAGE,
    )
    logger.info("***Successfully validated psgw resize error messages***")


@mark.resize
@mark.order(2445)
@mark.dependency()
def test_validate_psgw_sizer_field_override_functionality(context):
    """
    TestRail ID - C57582207
        Validate-PSGW-Sizer-fields-override-functionality
    """
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
    )
    validate_protection_store_gateway_vm(context)
    # resizing psgw with override
    override_cpu = 8
    override_ram_gib = 26
    override_storage_tib = 16
    validate_existing_psgw_resize_functionality(
        context,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
    )
    validate_the_override_functionality(context, override_cpu, override_ram_gib, override_storage_tib)


@mark.resize
@mark.order(2450)
@mark.dependency()
def test_validate_psg_resize_by_modifying_vCenter_creds(context):
    """
    TestRail ID - C57582210\C57582205

        Validate-PSGW-resize-by-modifying-Vcenter-creds-with-admin-privilage

    This Test case should be at last in test suite/test file, Otherwise this test case should fail,
    because we are updating the vCenter credentials.
    """
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
    )
    validate_protection_store_gateway_vm(context)
    change_vcenter_credentials(
        context,
        context.ad_username,
        context.ad_password,
    )

    # Resize the psgw_vm after successfully updated vcenter credentials.
    max_cld_dly_prtctd_data = 12.0
    max_cld_rtn_days = 2000
    max_onprem_dly_prtctd_data = 30.0
    max_onprem_rtn_days = 360

    validate_existing_psgw_resize_functionality(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
