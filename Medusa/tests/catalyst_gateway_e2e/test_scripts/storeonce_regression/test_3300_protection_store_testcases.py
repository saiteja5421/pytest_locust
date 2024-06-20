import time

from requests import codes
from lib.common.enums.azure_locations import AzureLocations
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.copy_pool_types import CopyPoolTypes
from tests.steps.vm_protection.backup_steps import (
    run_backup_for_storeonce,
    restore_virtual_machine,
)
from lib.dscc.backup_recovery.protection_policies.api.protection_templates import (
    ProtectionTemplate,
)
from tests.steps.vm_protection.protection_template_steps import create_protection_store
from tests.steps.vm_protection.storeonces_steps import (
    delete_protection_stores,
    get_storeonce_id,
    reattach_cloud_protection_store_to_new_storeonce,
    validate_register_storeonces,
    get_storeonce_health_status,
    verify_state_and_stateReason_of_protection_store,
    validate_unregister_storeonces,
    verify_stores_storeonce,
    verify_unregister_storeonce_not_allowed_if_backup_exists,
    reset_dsccAdmin_user_pwd,
)
from tests.steps.vm_protection.common_steps import (
    perform_cleanup,
    perform_storeonce_cleanup,
)
from tests.steps.vm_protection.storeonce_protection_template_steps import (
    assign_protection_template_to_vm,
    unassign_protecion_policy_from_vm,
    create_protection_store,
    create_protection_template,
    delete_unassinged_protection_policy,
    unassign_protecion_policy_from_all_vms,
    create_protection_template_with_multiple_cloud_regions_for_storeonce,
    verify_status_and_data_orchestrator_info_on_protection_store,
)
from lib.common.enums.backup_type_param import BackupTypeParam
from tests.steps.vm_protection.backup_steps import delete_all_backups
from pytest import fixture, mark
from lib.common.enums.aws_regions import AwsStorageLocation
from tests.catalyst_gateway_e2e.test_context import Context
import logging
from lib.common.enums.restore_type import RestoreType

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(set_static_policy=False, deploy=True, storeonce=True)
    yield test_context
    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    unregister_storeonce = False
    unregister_secondary_storeonce = False
    storeonce_id = get_storeonce_id(test_context)
    secondary_storeonce_id = get_storeonce_id(test_context, storeonces_name=test_context.second_so_name)

    if storeonce_id:
        unregister_storeonce = True
    if secondary_storeonce_id:
        unregister_secondary_storeonce = True

    perform_storeonce_cleanup(
        test_context,
        unregister_storeonce,
        storeonce_id,
        unregister_secondary_storeonce,
        secondary_storeonce_id,
    )
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.order(3300)
@mark.dependency()
def test_verify_state_and_stateReason_of_protection_store(context):
    """
    TestRail ID  - C57583462
    verify state and statereason of protection store
    """
    # Reset DsccAdmin password
    reset_dsccAdmin_user_pwd(context)
    # Register storeonce
    validate_register_storeonces(context)

    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_US_EAST_1)
    # make api call protection store
    verify_state_and_stateReason_of_protection_store(
        context,
    )
    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3310)
@mark.dependency()
def test_create_multiple_cloud_protection_store_same_region(context, vm_deploy):
    """
    TestRail ID  - C57583463
    create multiple cloud protection store same region
    """
    # # Reset DsccAdmin password
    reset_dsccAdmin_user_pwd(context)
    # Register storeonce
    validate_register_storeonces(context, multiple_local_protection_store=0)
    #
    create_protection_template_with_multiple_cloud_regions_for_storeonce(
        context, cloud_regions=[AwsStorageLocation.AWS_US_EAST_1, AzureLocations.AZURE_centralus]
    )
    assign_protection_template_to_vm(context)
    run_backup_for_storeonce(context, backup_type=BackupTypeScheduleIDs.storeonce)
    time.sleep(120)
    restore_virtual_machine(context, RestoreType.new, "cloud", quite_time=120)
    time.sleep(240)
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)


@mark.order(3320)
@mark.dependency()
def test_create_multiple_local_protection_store_restore_vm(context):
    """
    TestRail ID  - C57583464
    create multiple local protection store and take backup restore the vm.
    """
    logger.info("Unassigning and deleting existing protection policy before creating new one.")
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    logger.info("Creating multiple local protection stores.")
    for i in range(0, 2):
        create_protection_store(context, type=CopyPoolTypes.local)
    logger.info("Creating protection policy with existing cloud store.")
    create_protection_template_with_multiple_cloud_regions_for_storeonce(
        context, create_policy_with_existing_store=True
    )
    assign_protection_template_to_vm(context)

    logger.info("Run backup with multiple onprem protection stores")
    run_backup_for_storeonce(context, backup_type=BackupTypeScheduleIDs.local, multiple_stores=True)

    logger.info("Run local backup successful.")

    logger.info("Restorting VM from local backups")
    restore_virtual_machine(context, RestoreType.new, "local", quite_time=120)
    time.sleep(240)
    restore_virtual_machine(context, RestoreType.existing, "local", quite_time=120)
    logger.info("Restorting VM from local backups succeeded")


@mark.order(3330)
@mark.dependency(depends=["test_create_multiple_cloud_protection_store_same_region"])
def test_reattach_cloud_store_another_storeonce(context):
    """
    TestRail ID  - C57583465
    Reattach cloud store to another storeonce.
    """
    reattach_cloud_protection_store_to_new_storeonce(context)


@mark.order(3340)
@mark.dependency(depends=["test_create_multiple_cloud_protection_store_same_region"])
def test_delete_protection_store_with_backup_without_using_force(context):
    """
    TestRail ID  - C57583466
    Delete protection store having backups without using force
    """
    logger.info("Unassigning and deleting protection policy without deleting the backup.")
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    delete_protection_stores(context, force=False, expected_err=True)


@mark.order(3350)
@mark.dependency(depends=["test_create_multiple_cloud_protection_store_same_region"])
def test_delete_protection_store_with_backup_using_force(context):
    """
    TestRail ID  - C57583467
    Delete protection store with backup using force
    """
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    delete_protection_stores(context, force=True)
    storeonce_id = get_storeonce_id(context)
    secondary_storeonce_id = get_storeonce_id(context, storeonces_name=context.second_so_name)
    perform_storeonce_cleanup(
        context,
        unregister_storeonce=True,
        storeonce_id=storeonce_id,
        unregister_secondary_storeonce=True,
        secondary_storeonce_id=secondary_storeonce_id,
    )


@mark.order(3360)
@mark.dependency()
def test_delete_protection_store_without_backup(context):
    """
    TestRail ID - C57583468
    Delete protection store without backup Without force
    """
    # Reset DsccAdmin password
    reset_dsccAdmin_user_pwd(context)
    # Register storeonce
    validate_register_storeonces(context)
    create_protection_store(context, type=CopyPoolTypes.cloud, cloud_region=AwsStorageLocation.AWS_US_EAST_1)
    verify_state_and_stateReason_of_protection_store(context)
    delete_protection_stores(context, force=False)
    time.sleep(120)
    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3370)
@mark.dependency()
def test_delete_protection_store_without_backup_using_force(context):
    """
    TestRail ID - C57583469
    Delete protection store without backup using force
    """
    # Reset DsccAdmin password
    reset_dsccAdmin_user_pwd(context)
    # Register storeonce
    validate_register_storeonces(context)
    create_protection_store(context, type=CopyPoolTypes.cloud, cloud_region=AzureLocations.AZURE_centralindia)
    verify_state_and_stateReason_of_protection_store(context)
    delete_protection_stores(context, force=True)
