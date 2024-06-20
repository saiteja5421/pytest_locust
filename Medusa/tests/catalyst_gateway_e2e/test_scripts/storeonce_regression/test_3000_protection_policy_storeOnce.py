import time
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.backup_steps import (
    run_backup_for_storeonce,
    restore_virtual_machine,
)
from tests.steps.vm_protection.storeonces_steps import (
    get_storeonce_id,
    validate_register_storeonces,
    get_storeonce_health_status,
    verify_stores_storeonce,
    verify_unregister_storeonce_not_allowed_if_backup_exists,
    reset_dsccAdmin_user_pwd,
)
from tests.steps.vm_protection.common_steps import perform_storeonce_cleanup
from tests.steps.vm_protection.storeonce_protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
    delete_unassinged_protection_policy,
    unassign_protecion_policy_from_all_vms,
    create_protection_template_with_multiple_cloud_regions_for_storeonce,
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
    storeonce_id = get_storeonce_id(test_context)
    if storeonce_id:
        unregister_storeonce = True
    perform_storeonce_cleanup(test_context, unregister_storeonce, storeonce_id)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.order(3000)
@mark.dependency()
def test_create_protection_policy_run_backup(context, vm_deploy):
    """
    TestRail ID - C57582246/C57582247
    Create protection policy for local/cloud backups, take backups and ensure that local/cloud store is created.

    TestRail ID - C57582227
    Register StoreOnce when there's only one Data Orchestrator.

    """
    # Reset DsccAdmin password
    reset_dsccAdmin_user_pwd(context)
    # Register storeonce
    validate_register_storeonces(context)
    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")
    create_protection_template(
        context, cloud_region=AwsStorageLocation.AWS_US_EAST_1, onprem_expire_value=7, cloud_expire_value=10
    )
    assign_protection_template_to_vm(context)
    # run the backup for storeonce
    run_backup_for_storeonce(context)
    # Need wait for backend to update values in dscc
    time.sleep(360)
    """
    verify stores is created in storeonce
    """
    verify_stores_storeonce(context)


@mark.order(3010)
@mark.dependency(depends=["test_create_protection_policy_run_backup"])
def test_restore_vm_from_local(context):
    """
    TestRail ID - C57589867
    Restore VM from local backups
    """
    restore_virtual_machine(context, RestoreType.new, "local", quite_time=120)
    time.sleep(240)
    restore_virtual_machine(context, RestoreType.existing, "local", quite_time=120)


@mark.order(3020)
@mark.dependency(depends=["test_create_protection_policy_run_backup"])
def test_restore_vm_from_cloud(context):
    """
    TestRail ID - C57589868
    Restore VM from cloud backups
    """
    restore_virtual_machine(context, RestoreType.new, "cloud", quite_time=120)
    time.sleep(240)
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)


@mark.order(3030)
@mark.dependency()
def test_create_multiple_cloud_region(context):
    """
    TestRail ID - C57582249
    Create cloud protection policy with multiple cloud regions and check reports show the changes
    """
    delete_all_backups(BackupTypeParam.backups, context)
    unassign_protecion_policy_from_all_vms(context)
    delete_unassinged_protection_policy(context)
    storeonce_id = get_storeonce_id(context)
    if storeonce_id:
        get_storeonce_health_status(context, storeonce_id, "OK")
    else:
        validate_register_storeonces(context)

    create_protection_template_with_multiple_cloud_regions_for_storeonce(
        context,
        cloud_regions=[AwsStorageLocation.AWS_US_EAST_1, AzureLocations.AZURE_eastus2],
        onprem_expire_value=7,
        cloud_expire_value=10,
    )
    time.sleep(20)
    assign_protection_template_to_vm(context)
    run_backup_for_storeonce(context)


@mark.order(3040)
@mark.dependency(depends=["test_create_multiple_cloud_region"])
def test_unregister_storeonce_with_backup(context):
    """
    TestRail ID - C57582241
    Unregister a StoreOnce that has some protected resources.

    """
    verify_unregister_storeonce_not_allowed_if_backup_exists(context)
