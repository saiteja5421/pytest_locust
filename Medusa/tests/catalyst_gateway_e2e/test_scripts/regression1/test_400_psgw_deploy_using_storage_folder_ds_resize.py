"""
TestRail ID: C57581946
    Deploy Protection Store Gateway VM when datastore is in inside the storage folder on a vcenter
TestRail ID - C57582188
    Validate Resize PSGW functionality
"""

import logging

from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    select_or_create_protection_store_gateway_vm,
    validate_existing_psgw_resize_functionality,
    validate_existing_psgw_resize_functionality_max_min_cloud_retention_days,
    validate_existing_psgw_resize_functionality_max_min_local_retention_days,
    validate_psgw_resources_post_update,
    delete_protection_store_gateway_vm,
    verify_the_error_msg_min_max_onprem_cloud_retention_days,
)
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
)
from tests.steps.vm_protection.backup_steps import run_backup
from tests.steps.vm_protection.common_steps import perform_cleanup
from lib.common.enums.aws_regions import AwsStorageLocation
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")
    perform_cleanup(test_context)
    logger.info(10 * "=" + "Teardown Complete !!!" + 10 * "=")


@mark.order(400)
@mark.deploy
def test_deploy_psgw_with_ds_in_storage_folder(context, vm_deploy):
    """TestRail ID: C57581946
    Deploy Protection Store Gateway VM when datastore is in inside the storage folder on a vcenter
    """
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS-STG-FLDR"
    context.datastore_id = context.hypervisor_manager.get_datastore_id(ds_name, context.vcenter_name)
    logger.warning(
        f"We should create a datastore {ds_name} and this must be in a storage folder on vCenter: {context.vcenter_name} otherwise test expectation will be deviated"
    )
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=298,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=199,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_canadacentral)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.local)


@mark.order(405)
def test_deloy_psgw_with_max_onprem_cloud_retention_days(context):
    """
    TestRail ID: C57589138
    Deploy PSG with max on-prem and cloud retention period
    """
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=3650,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=2555,
    )
    validate_protection_store_gateway_vm(context)
    delete_protection_store_gateway_vm(context)


@mark.order(410)
def test_deploy_psg_more_then_vaild_max_onprem_cloud_retention_days(context):
    """
    TestRail ID: C57589139/C57591913
    Deploy PSG with more then valid max on-prem and cloud period values/
    Deploy PSG with more then valid min on-prem and cloud period values
    """
    verify_the_error_msg_min_max_onprem_cloud_retention_days(context)


@mark.resize
@mark.order(415)
def test_valildate_resize_psgw_functionality(context):
    """
    TestRail ID - C57582188
    Validate Resize PSGW functionality
    """
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    datastore_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS-62TB"
    context.datastore_id = context.hypervisor_manager.get_datastore_id(datastore_name, context.vcenter_name)
    logger.warning(
        f"We need to create datastores to accomodate psgw capacity and datastore name must contains: {datastore_name} on vcenter: {context.vcenter_name}, otherwise test expected to fail"
    )
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=298,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=199,
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


@mark.order(420)
def test_valildate_resize_psgw_functionality_with_max_retention_days(context):
    """
    TestRail ID - C57589140
    Resize the PSG to max. on-perm and cloud retention period
    """
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
    )
    validate_protection_store_gateway_vm(context)
    max_cld_dly_prtctd_data = 10.0
    max_cld_rtn_days = 3650
    max_onprem_dly_prtctd_data = 5.0
    max_onprem_rtn_days = 2555
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


@mark.order(425)
def test_valildate_resize_psgw_functionality_more_than_onprem_cloud_retention_period(context):
    """
    TestRail ID - C57589140/C57591912
    Resize the PSG to max. on-perm and cloud retention period/Resize PSG with valid min on-prem and cloud period values
    """
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=298,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=199,
    )
    validate_protection_store_gateway_vm(context)
    validate_existing_psgw_resize_functionality_max_min_local_retention_days(
        context,
        additional_ds_required=False,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=3650,
        max_onprem_dly_prtctd_data=15.0,
        max_onprem_rtn_days=2556,
    )
    logger.info("Successfully vaildated the error message for maximum local value")
    validate_existing_psgw_resize_functionality_max_min_local_retention_days(
        context,
        additional_ds_required=False,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=3650,
        max_onprem_dly_prtctd_data=15.0,
        max_onprem_rtn_days=0,
    )
    logger.info("Successfully vaildated the error message for minimum local value")
    validate_existing_psgw_resize_functionality_max_min_cloud_retention_days(
        context,
        additional_ds_required=False,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=3651,
        max_onprem_dly_prtctd_data=15.0,
        max_onprem_rtn_days=2555,
    )
    logger.info("Successfully vaildated the error message for maximum could value")
    validate_existing_psgw_resize_functionality_max_min_cloud_retention_days(
        context,
        additional_ds_required=False,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=0,
        max_onprem_dly_prtctd_data=15.0,
        max_onprem_rtn_days=2555,
    )
    logger.info("Successfully vaildated the error message for minimum colud value")
