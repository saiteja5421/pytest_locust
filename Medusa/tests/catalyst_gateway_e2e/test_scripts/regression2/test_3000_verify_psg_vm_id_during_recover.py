"""
    TestRail ID - C57582179
    Verify PSG VM ID during the Recover

    TestRail ID - C57501930
    Collect the cipher text from DO pre-recovery and post DO recovery and check both are different or not

    TestRail ID - C57582299
    vCenter Registration with Invalid or wrong Password
"""

import time
import logging
from random import choice
from pytest import fixture, mark
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.azure_locations import AzureLocations
from lib.common.enums.psg import HealthState, HealthStatus, State
from lib.common.error_messages import (
    ERROR_MESSAGE_FOR_TASK_TO_UPDATE_VCENTER_PASSWORD,
    ERROR_MESSAGE_UNABLE_TO_UPDATE_VCENTER_PASSWORD,
)
from tests.steps.vm_protection.backup_steps import run_backup
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
    delete_unassinged_protection_policy,
    unassign_protecion_policy_from_vm,
)
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    select_or_create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    recover_protection_store_gateway_vm,
    delete_protection_store_gateway_vm_from_vcenter,
    wait_for_psg,
    get_psg_vmid,
    validate_psg_vmid_at_given_state,
    enable_remote_support_get_cipher_text,
    check_cipher_text,
)
from tests.steps.vm_protection.vcenter_steps import (
    change_vcenter_credentials,
    validate_error_message_for_insufficient_previlages,
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


@mark.order(3000)
@mark.recover
@mark.dependency()
def test_verify_psg_vm_id_during_recover(context, vm_deploy):
    """
    TestRail ID - C57582179
    Verify PSG VM ID during the Recover
    """
    create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_NORTH_1)
    assign_protection_template_to_vm(context)
    psg_vmId_before_recover = get_psg_vmid(context)
    validate_psg_vmid_at_given_state(context, "before_recover")
    run_backup(context, backup_type=BackupTypeScheduleIDs.local)

    # Delete PSG VM from vCenter to simulate PSG disaster
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnecte
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )

    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(15 * 60)

    # Recover PSG VM
    recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}",
        verify_vmId=True,
    )
    validate_protection_store_gateway_vm(context)
    validate_psg_vmid_at_given_state(context, "after_recover", psg_vmId_before_recover)
    # unassign and delete the protection policy with only local backup
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)


@mark.order(3005)
@mark.recover
@mark.dependency()
def test_verify_cipher_text_during_recover(context):
    """
    TestRail ID - C57501930
    Collect the cipher text from DO pre-recovery and post DO recovery and check both are different or not
    """
    select_or_create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_westeurope)
    assign_protection_template_to_vm(context)
    run_backup(context)

    # enable remote support and get cipher text before recovery
    admin_cipher, support_cipher = enable_remote_support_get_cipher_text(context)
    logger.info(f"Cipher text before recovery")
    logger.info(f"Admin cipher: {admin_cipher}")
    logger.info(f"Support cipher: {support_cipher}")

    # Delete PSG VM from vCenter to simulate PSG disaster
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnecte
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )

    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(15 * 60)

    # Recover PSG VM
    recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}",
        verify_vmId=True,
    )
    validate_protection_store_gateway_vm(context)

    # enable remote support and get cipher text after recovery
    recover_admin_cipher, recover_support_cipher = enable_remote_support_get_cipher_text(context)

    logger.info(f"Cipher text after recovery")
    logger.info(f"Admin cipher: {recover_admin_cipher}")
    logger.info(f"Support cipher: {recover_support_cipher}")

    check_cipher_text(admin_cipher, recover_admin_cipher, type="Admin")
    check_cipher_text(support_cipher, recover_support_cipher, type="Support")


@mark.order(3010)
@mark.dependency()
def test_vCenter_Registration_with_Invalid_or_wrong_Password(context):
    """
    TestRail ID - C57582299
    vCenter Registration with Invalid or wrong Password
    """

    # generate random invalid/wrong password for vcenter from conetxt.vcenter_password
    generated_random_password = "".join([choice(context.vcenter_password) for password in range(13)])
    logger.info(f"generated invalid/wrong password for vcenter: {generated_random_password}")
    task_id = change_vcenter_credentials(
        context,
        context.vcenter_username,
        generated_random_password,
        "failed",
    )
    validate_error_message_for_insufficient_previlages(
        context,
        task_id,
        ERROR_MESSAGE_UNABLE_TO_UPDATE_VCENTER_PASSWORD,
        ERROR_MESSAGE_FOR_TASK_TO_UPDATE_VCENTER_PASSWORD,
    )
