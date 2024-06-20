"""
    TestRail ID - C57582320
    Verify state and stateReason of protection store for disconnected PSG

    TestRail ID - C57582321
    Verify update protection store with same name

    TestRail ID - C57582329
    Create multiple cloud protection stores, run backup and perform restore

    TestRail ID - C57582322
    Create multiple on_prem protection stores, run backup and perform restore

    TestRail ID - C57582323
    Verify state and stateReason of protection store for deleted psg

    TestRail ID - C57582324
    Verify psgw recovery with multiple cloud stores in same region

    TestRail ID - C57582325
    Verify delete of protecion store without deleting protection policy

    TestRail ID - C57582326
    Delete PSGW and reattach cloud protection store to new PSG

    TestRail ID - C57582327
    Reattach cloud protection store from one PSG to another

    TestRail ID - C57582328
    Verify protection store for resized PSGW

    TestRail ID - C57582318
    Delete protection store without backup without force

    TestRail ID  - C57582316
    Delete protection store without  backup using force

    TestRail ID  - C57582317
    Delete protection store with backup using force

    TestRail ID  - 	C57582319
    Delete protection store which is not associated to any policy but having backups without using force

"""

import time
import logging
from pytest import fixture, mark
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.azure_locations import AzureLocations
from lib.common.enums.psg import HealthState, HealthStatus, State
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template_with_multiple_cloud_regions,
    create_protection_template,
    delete_unassinged_protection_policy,
    unassign_protecion_policy_from_vm,
    create_protection_store,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    restore_virtual_machine,
)
from lib.common.enums.copy_pool_types import CopyPoolTypes
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.restore_type import RestoreType
from tests.steps.vm_protection.psgw_steps import (
    select_or_create_protection_store_gateway_vm,
    create_protection_store_gateway_vm,
    delete_protection_stores,
    delete_protection_store_gateway_vm,
    validate_existing_psgw_resize_functionality,
    validate_protection_store_gateway_vm,
    delete_protection_store_gateway_vm_from_vcenter,
    validate_psgw_resources_post_update,
    wait_for_psg,
    wait_to_get_psgw_to_powered_off,
    wait_for_psgw_to_power_on_and_connected,
    recover_protection_store_gateway_vm,
    reattach_cloud_protection_store_to_new_psg,
    verify_state_and_stateReason_of_protection_store,
    verify_delete_store_without_deleting_protection_policy,
    verify_update_store_with_same_name,
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


@mark.order(3500)
@mark.dependency()
def test_verify_state_and_stateReason_of_protection_store_for_disconnected_psg(context, vm_deploy):
    """TestRail ID - C57582323
    Verify state and stateReason of protection store for disconnected PSG
    """
    create_protection_store_gateway_vm(context, multiple_local_protection_store=0)
    validate_protection_store_gateway_vm(context)
    logger.info("PSGW created and validated with 0 local protection stores.")
    logger.info("Creating two cloud proptection stores in same region")
    create_protection_template_with_multiple_cloud_regions(
        context, cloud_regions=[AzureLocations.AZURE_westus2, AwsStorageLocation.AWS_US_EAST_1]
    )
    assign_protection_template_to_vm(context)
    logger.info("PSG powering off:")
    wait_to_get_psgw_to_powered_off(context)
    verify_state_and_stateReason_of_protection_store(
        context, exp_state="OFFLINE", exp_state_reason="Unable to connect to the Protection Store."
    )
    logger.info("PSG powering ON:")
    wait_for_psgw_to_power_on_and_connected(context)


@mark.order(3505)
@mark.dependency(depends=["test_verify_state_and_stateReason_of_protection_store_for_disconnected_psg"])
def test_verify_update_store_with_same_name(context):
    """TestRail ID - C57582321
    Verify update protection store with same name
    """
    verify_update_store_with_same_name(context)


@mark.order(3510)
@mark.dependency(depends=["test_verify_state_and_stateReason_of_protection_store_for_disconnected_psg"])
def test_create_multple_cloud_protection_stores_in_one_region_run_backups_and_restore(context):
    """TestRail ID - C57582329
    Create multiple cloud protection stores, run backup and perform restore
    """

    logger.info("Run backup with multiple cloud protection stores")
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud, multiple_stores=True)

    logger.info("Run cloud backup successful.")

    logger.info("Restorting VM from cloud backups")
    restore_virtual_machine(context, RestoreType.new, "cloud")
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)
    logger.info("Restorting VM from cloud backups succeeded")


@mark.order(3515)
@mark.dependency(depends=["test_verify_state_and_stateReason_of_protection_store_for_disconnected_psg"])
def test_verify_delete_store_and_without_deleting_protection_policy(context):
    """TestRail ID - C57582324
    Verify delete of protecion store without deleting protection policy
    """
    verify_delete_store_without_deleting_protection_policy(context)


@mark.order(3520)
@mark.dependency(depends=["test_verify_state_and_stateReason_of_protection_store_for_disconnected_psg"])
def test_delete_protection_store_with_backup_without_using_force(context):
    """
    TestRail ID  - C57582319
    Delete protection store which is not associated to any policy but having backups without using force
    """
    logger.info("Unassigning and deleting protection policy without deleting the backup.")
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    delete_protection_stores(context, force=False, expected_err=True)


@mark.order(3525)
@mark.dependency(depends=["test_delete_protection_store_with_backup_without_using_force"])
def test_delete_protection_store_with_backup_using_force(context):
    """
    TestRail ID  - C57582317
    Delete protection store with backup using force
    """
    delete_protection_stores(context, force=True)
    logger.info("Performing cleanup for future test cases.")
    perform_cleanup(context, clean_vm=False)


@mark.order(3530)
@mark.dependency()
def test_delete_protection_store_without_backup(context):
    """
    TestRail ID - C57582318
    Delete protection store without backup Without force
    """
    create_protection_store_gateway_vm(context)
    create_protection_store(context, type=CopyPoolTypes.cloud, cloud_region=AwsStorageLocation.AWS_US_EAST_1)
    verify_state_and_stateReason_of_protection_store(context)
    delete_protection_stores(context, force=False)


@mark.order(3535)
@mark.dependency()
def test_delete_protection_store_without_backup_using_force(context):
    """
    TestRail ID - C57582316
    Delete protection store without backup using force
    """
    select_or_create_protection_store_gateway_vm(context)
    create_protection_store(context, type=CopyPoolTypes.cloud, cloud_region=AwsStorageLocation.AWS_US_EAST_1)
    verify_state_and_stateReason_of_protection_store(context)
    delete_protection_stores(context, force=True)


@mark.order(3540)
@mark.dependency()
def test_create_multple_onprem_protection_stores_run_backups_and_restore(context):
    """TestRail ID - C57582322
    Create multiple on_prem protection stores, run backup and perform restore
    """
    select_or_create_protection_store_gateway_vm(context)
    logger.info("Creating multiple local protection stores.")
    for i in range(0, 2):
        create_protection_store(context, type=CopyPoolTypes.local)
    create_protection_template_with_multiple_cloud_regions(
        context,
        cloud_regions=[AwsStorageLocation.AWS_US_EAST_1, AzureLocations.AZURE_eastus],
        onprem_expire_value=7,
        cloud_expire_value=10,
    )
    assign_protection_template_to_vm(context)

    logger.info("Run backup with multiple onprem protection stores")
    run_backup(context, backup_type=BackupTypeScheduleIDs.local, multiple_stores=True)

    logger.info("Run local backup successful.")

    logger.info("Waiting for 5 minutes before restorting VM so that backup tasks gets updated.")
    time.sleep(300)

    logger.info("Restorting VM from local backups")
    restore_virtual_machine(context, RestoreType.new, "local")
    restore_virtual_machine(context, RestoreType.existing, "local", quite_time=120)
    logger.info("Restorting VM from local backups succeeded")


@mark.order(3545)
@mark.dependency()
def test_verify_connectedState_and_stateReason_for_deleted_psg(context):
    """TestRail ID - C57582323
    Verify state and stateReason of protection store for deleted psg
    """
    # Running cloud backup with multiple cloud stores
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud, multiple_stores=True)
    logger.info(f"Waiting for 5 minutest before deleting PSGW VM so that backup tasks gets updated.")
    time.sleep(300)
    # Delete PSG VM from vCenter
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnected
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )
    logger.info("Sleeping for 5 minutes so that protection store details got updated.")
    time.sleep(300)
    verify_state_and_stateReason_of_protection_store(
        context, exp_state="OFFLINE", exp_state_reason="Unable to connect to the storage system."
    )


@mark.order(3550)
@mark.dependency(depends=["test_verify_connectedState_and_stateReason_for_deleted_psg"])
def test_verify_psgw_recovery_with_multiple_cloud_stores_in_same_region(context):
    """TestRail ID - C57582324
    Verify psgw recovery with multiple cloud stores in same region
    """
    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15 min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(10 * 60)
    recover_psgw_name = f"recover_{context.psgw_name}"
    recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=recover_psgw_name,
    )

    # Perform asset backup should work well with existing local/cloud stores and also the protection policy
    validate_protection_store_gateway_vm(context)
    verify_state_and_stateReason_of_protection_store(context)


@mark.order(3555)
@mark.dependency()
def test_delete_psg_and_reattach_protection_store_to_new_psg(context):
    """TestRail ID - C57582325
    Delete PSGW and reattach cloud protection store to new PSG
    """
    # Delete PSG VM from vCenter
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnected
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )
    reattach_cloud_protection_store_to_new_psg(context)


@mark.order(3560)
@mark.dependency()
def test_reattach_cloud_store_to_another_psg(context):
    """TestRail ID - C57582327
    Reattach cloud protection store from one PSG to another
    """
    reattach_cloud_protection_store_to_new_psg(context)


@mark.order(3565)
@mark.dependency()
def test_resize_psg_check_the_store_status(context):
    """TestRail ID - C57582328
    Verify protection store for resized PSGW
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
    logger.info("Sleep for 420 seconds after resize for protection store to reach online")
    time.sleep(420)
    verify_state_and_stateReason_of_protection_store(context)
