"""
    TestRail ID - C57582338
    This test is to verify vmotion/relocate of datastore1 to datastore2 for psgw

    TestRail ID - C57582339
    This test will perform resize with updated datastore after vmotion.

    TestRail ID - C57582340
    This test will perform backup and recovery with updated datastore after vmotion.
"""

import logging
import time
from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.vcenter_steps import (
    vm_relocate_on_datastore,
    refresh_vcenter_inventory,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    verify_psgw_datastore_info,
    validate_existing_psgw_resize_functionality,
    validate_psgw_resources_post_update,
    delete_protection_store_gateway_vm_from_vcenter,
    validate_protection_store_gateway_vm,
    recover_protection_store_gateway_vm,
    wait_for_psg,
)
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from tests.steps.vm_protection.backup_steps import (
    run_backup,
)
from lib.common.enums.psg import HealthState, HealthStatus, State

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(1700)
@mark.dependency()
def test_vmotion_psgw_storage(context, vm_deploy):
    """
    TestRail ID - C57582338
    This method is used to move datastore1 to datastore2 for psgw
    """
    create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
        max_cld_dly_prtctd_data=5.0,
        max_cld_rtn_days=200,
        max_onprem_dly_prtctd_data=10.0,
        max_onprem_rtn_days=250,
    )
    validate_protection_store_gateway_vm(context)
    datastore_name = context.datastore_name
    # verify datastore1 is present  in psgw  gateway
    verify_psgw_datastore_info(context, datastore_name)
    assert context.datastore_name != context.datastore_62tb, "datastore1 and datastore2 are same use diffrent datastore"
    vm_relocate_on_datastore(context)
    # refresh the vcenter
    refresh_vcenter_inventory(context, context.vcenter_id)
    # wait for 5 mins to update  in the backend
    time.sleep(360)
    datastore_name = context.datastore_62tb
    # verify datastore2 is present in the psgw gateway
    verify_psgw_datastore_info(context, datastore_name)


@mark.order(1710)
@mark.dependency(depends=["test_vmotion_psgw_storage"])
def test_perform_psgw_resize_with_vmotion_storage(context):
    """
    TestRail ID - C57582339
    This test will perform resize with updated datastore after vmotion.
    """
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
    verify_psgw_datastore_info(context, context.datastore_62tb)
    logger.info("PSGW successfully resized with updated datastore.")


@mark.order(1720)
@mark.dependency(depends=["test_vmotion_psgw_storage"])
def test_perform_backup_and_recovery_with_vmotion_storage(context):
    """
    TestRail ID - C57582340
    This test will perform backup and recovery with updated datastore after vmotion.
    """
    create_protection_template(context, cloud_region=AzureLocations.AZURE_qatarcentral)
    assign_protection_template_to_vm(context)
    # create_protection_template_with_multiple_cloud_regions(context, cloud_regions=[AwsStorageLocation.AWS_US_EAST_2])
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    logger.info("Run cloud backup successful.")
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15 min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(15 * 60)
    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnected
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )
    recover_psgw_name = f"recover_{context.psgw_name}"
    recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=recover_psgw_name,
    )

    # Perform asset backup should work well with existing local/cloud stores and also the protection policy
    validate_protection_store_gateway_vm(context)
    verify_psgw_datastore_info(context, context.datastore_62tb)
    logger.info("PSGW successfully recovered with updated datastore.")
