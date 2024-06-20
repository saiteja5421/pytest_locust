import time
from tests.steps.vm_protection.backup_steps import (
    run_backup_for_storeonce,
    restore_virtual_machine,
)
from tests.steps.vm_protection.storeonces_steps import (
    get_storeonce_id,
    validate_register_storeonces,
    get_storeonce_health_status,
    reattach_cloud_protection_store_to_new_storeonce,
    reset_dsccAdmin_user_pwd,
)
from tests.steps.vm_protection.common_steps import perform_storeonce_cleanup
from tests.steps.vm_protection.storeonce_protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
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


@mark.order(3400)
@mark.dependency()
def test_create_protection_policy_with_azure_run_backup(context, vm_deploy):
    """
    TestRail ID  - C57641208
    Create Azure cloud protection store on SO and preform B&R.
    """
    # Reset DsccAdmin password
    reset_dsccAdmin_user_pwd(context)
    # Register storeonce
    validate_register_storeonces(context)
    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")
    create_protection_template(
        context,
        cloud_region=AzureLocations.AZURE_eastus,
    )
    assign_protection_template_to_vm(context)
    # run the backup for storeonce
    run_backup_for_storeonce(context)


@mark.order(3410)
@mark.dependency(depends=["test_create_protection_policy_with_azure_run_backup"])
def test_reattach_cloud_store_another_storeonce(context):
    """
    TestRail ID  - C57641044
    Create Cloud store with location_id and attach/Re-attach between SO and SO.
    """
    reattach_cloud_protection_store_to_new_storeonce(context, secondary_so=True)


@mark.order(3420)
@mark.dependency(depends=["test_create_protection_policy_with_azure_run_backup"])
def test_restore_vm_from_cloud(context):
    restore_virtual_machine(context, RestoreType.new, "cloud", quite_time=120)
    time.sleep(240)
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)
