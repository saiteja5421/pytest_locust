import logging

import requests
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.protection_group_dynamic_filter_type import ProtectionGroupDynamicFilterType
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.task_status import TaskStatus

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag, GLCPErrorResponse

from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.protection_group_model import (
    DynamicMemberFilterModel,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.csp_protection_group_payload_model import (
    PostDynamicProtectionGroupModel,
)

from lib.common.enums.ec2_restore_operation import Ec2RestoreOperation
import tests.steps.aws_protection.policy_manager_steps as PolicyMgrSteps
import tests.steps.aws_protection.restore_steps as RestoreSteps
import tests.steps.aws_protection.inventory_manager_steps as IMS
from tests.e2e.aws_protection.context import Context
from tests.steps.tasks import tasks
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def refresh_inventory_with_error(
    context: Context, error_msg_expected: str, expected_status_code: requests.codes = requests.codes.conflict
):
    """Refreshs account inventory and asserts appropriate task error is returned

    Args:
        context (Context): test Context
        error_msg_expected (str): Expected error message
    """
    error_message: GLCPErrorResponse = context.inventory_manager.trigger_account_inventory_sync(
        account_id=context.csp_account_id_aws_one, expected_status_code=expected_status_code
    )
    logger.info(f"task errors for refresh inventory(): {error_message}")
    assert (
        error_msg_expected in error_message.message
    ), f"Expected error {error_msg_expected} not found in {error_message}"


def create_protection_group_with_error(context: Context, expected_error: str):
    """Creates protection group and asserts appropriate task error is returned

    Args:
        context (Context): test Context
        expected_error (str): Expected task error
    """
    name = "protection_group_with_error"
    csp_tags = CSPTag(key="test_with_error", value="error")
    payload = PostDynamicProtectionGroupModel(
        [context.csp_account_id_aws_one],
        name,
        [context.aws_one._aws_session_manager.region_name],
        DynamicMemberFilterModel([csp_tags], ProtectionGroupDynamicFilterType.CSP_TAG.value),
        asset_type=AssetType.CSP_MACHINE_INSTANCE.value,
    )
    task_id = context.inventory_manager.create_protection_group(payload)
    create_pg_task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)
    create_pg_task_errors = tasks.get_task_error(task_id, context.user)
    assert create_pg_task_status.upper() == TaskStatus.failed.value
    logger.info(f"Verify task error {expected_error} for create protection group in: {create_pg_task_status}")
    assert (
        expected_error in create_pg_task_errors
    ), f"Expected error not found {expected_error} in {create_pg_task_errors}"


def protect_asset_with_error(context: Context, asset_id: str, protection_policy_id: str, expected_error: str):
    """Protects asset and asserts appropriate task error is returned

    Args:
        context (Context): test Context
        asset_id (str): Asset id
        protection_policy_id (str): Protection policy id
        expected_error (str): Expected task error
    """
    task_id = PolicyMgrSteps.create_protection_job_for_asset(
        context=context,
        asset_id=asset_id,
        asset_type=AssetType.CSP_MACHINE_INSTANCE,
        protection_policy_id=protection_policy_id,
        wait_for_task=False,
    )
    protect_task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)
    protect_task_errors = tasks.get_task_error(task_id, context.user)
    assert protect_task_status.upper() == TaskStatus.failed.value
    logger.info(f"Verify task error {expected_error} for protect asset in: {protect_task_errors}")
    assert expected_error in protect_task_errors, f"Expected error not found {expected_error} in {protect_task_errors}"


def restore_with_error(context: Context, source_ec2_instance_id: str, error_expected: str):
    """Attempts to restore instance and asserts appropriate task error is returned

    Args:
        context (Context): test Context
        source_ec2_instance_id (str): EC2 instance to restore
        error_expected (str): Expected task error
    """
    source_ec2_instance = IMS.get_csp_instance_by_ec2_instance_id(
        context=context, ec2_instance_id=source_ec2_instance_id
    )
    csp_machine_instance_backup = RestoreSteps.get_first_good_machine_instance_backup(
        context, source_ec2_instance.id, CSPBackupType.NATIVE_BACKUP
    )
    subnet_csp_id: str = IMS.get_subnet_csp_id(
        context=context,
        account_id=source_ec2_instance.accountInfo.id,
        subnet_id=source_ec2_instance.cspInfo.networkInfo.subnetInfo.id,
    )

    restore_payload = RestoreSteps.build_restore_machine_instance_payload(
        account_id=source_ec2_instance.accountInfo.id,
        availability_zone=source_ec2_instance.cspInfo.availabilityZone,
        region=source_ec2_instance.cspInfo.cspRegion,
        instance_type=source_ec2_instance.cspInfo.instanceType,
        operation_type=Ec2RestoreOperation.CREATE.value,
        key_pair=source_ec2_instance.cspInfo.keyPairName,
        security_group=source_ec2_instance.cspInfo.networkInfo.securityGroups[0].cspId,
        subnet_id=subnet_csp_id,
        disable_termination=False,
        terminate_original=False,
    )
    restore_payload.target_machine_instance_info.name = "Restore should fail"
    RestoreSteps.restore_machine_instance_and_wait(
        context=context,
        backup_id=csp_machine_instance_backup.id,
        restore_payload=restore_payload,
        wait=False,
        status_code=requests.codes.conflict,
        error_expected=error_expected,
    )
