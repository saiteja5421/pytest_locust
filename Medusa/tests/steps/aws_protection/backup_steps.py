"""
This Module contains steps Related to Backup Workflow. This includes:
    Creating/Deleting Backups.
    Verifying Backup Related Tasks are Completed.
    Getting and Verifying the Number of Backups for an Asset.
    Checking State/Status of Backups.
"""

from email.utils import formatdate
import logging
import time
from datetime import datetime
from typing import Union
import dateutil.parser
from dateutil.relativedelta import relativedelta
from pytz import timezone
import uuid
from google.protobuf.timestamp_pb2 import Timestamp
from waiting import wait, TimeoutExpired

from lib.common.config.config_manager import ConfigManager
from lib.common.enums.asset_type_uri_prefix import AssetTypeURIPrefix
from lib.common.enums.csp_type import CspType
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.index_status import IndexStatus
from lib.common.enums.kafka_inventory_asset_type import KafkaInventoryAssetType
from lib.common.enums.backup_state import BackupState
from lib.common.enums.backup_consistency import BackupConsistency
from lib.common.enums.backup_type import BackupType
from lib.common.enums.kafka_backup_type import KafkaBackupType
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.schedule_status import ScheduleStatus
from lib.common.enums.task_status import TaskStatus
from lib.common.enums.object_unit_type import ObjectUnitType
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.backup_kafka_event_status import BackupKafkaEventStatus
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import (
    CSPBackupListModel,
    CSPBackupModel,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_payload_model import (
    PatchEC2EBSBackupsModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.models.resource_type import ResourceType
from lib.dscc.backup_recovery.aws_protection.common.models.asset_set import AssetSet
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectUnitValue
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import (
    CSPVolumeListModel,
    CSPVolumeModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import (
    CSPMachineInstanceListModel,
    CSPMachineInstanceModel,
)
from lib.dscc.backup_recovery.azure_protection.common.models.asset_set_azure import AssetSetAzure

from lib.dscc.settings.dual_auth.authorization.models.dual_auth_operation import DualAuthOperation
from lib.platform.aws_boto3.aws_factory import AWS
import tests.steps.aws_protection.cloud_account_manager_steps as CAMS

import tests.steps.aws_protection.inventory_manager_steps as IMS

import lib.platform.kafka.protobuf.dataprotection.backup_updates_pb2 as backup_events_pb2
from lib.platform.kafka.protobuf.dataprotection.backup_updates_pb2 import BackupCreationInfo, BackupDeletionInfo
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.e2e.aws_protection.context import Context
from tests.e2e.azure_protection.azure_context import AzureContext
import tests.steps.aws_protection.common_steps as CommonSteps
import tests.steps.aws_protection.dashboard_steps as DashboardSteps
from tests.steps.aws_protection.settings.dual_auth_steps import (
    authorize_dual_auth_request,
    get_pending_request_by_name_and_resource_uri,
)
from tests.steps.tasks import tasks

from utils.timeout_manager import TimeoutManager


logger = logging.getLogger()
config = ConfigManager.get_config()

TRIGGER_BACKUP_DISPLAY_NAME: str = "Trigger Native Backup"
TRIGGER_CLOUD_BACKUP_DISPLAY_NAME: str = "Trigger Cloud Backup"
COPY2CLOUD_DISPLAY_NAME: str = "CVSA Nightly Trigger Cycle"

# a string of 40 asterisks
ASTERISK_LINE: str = "****************************************"

# Added for Saad's team to report backup deletion start and end time
time_zone = timezone("US/Eastern")


def wait_for_backup_total(
    context: Context, asset_id: str, asset_type: AssetType, backup_type: BackupType, expected_count: int = 0
):
    """Waits for total backup count

    Args:
        context (Context): The test context
        asset_id (str): The CSP Asset ID
        asset_type (AssetType): The CSP Asset Type
        backup_type (BackupType): The Backup Type
        expected_count (int, optional): Expected Number of Backups. Defaults to 0.
    """
    wait(
        lambda: get_asset_backup_count(context, asset_id, asset_type)[backup_type] == expected_count,
        timeout_seconds=15 * 60,
        sleep_seconds=15,
    )


def get_asset_backup_count(
    context: Context, asset_id: str, asset_type: AssetType, refresh_auth: bool = False
) -> dict[CSPBackupType, int]:
    """Returns the number of backups for an asset

    Args:
        context (Context): The test Context
        asset_id (str): The CSP Asset ID
        asset_type (AssetType): The CSP Asset Type
        refresh_auth (bool, optional): Used in the case of long cloud backup tests. Defaults to False.

    Returns:
        dict[CSPBackupType, int]: Number of backups of each type for an asset
    """
    # For production testing, we have cloud backup test that can run for quite some time
    # used by: verify_taken_prod_cloud_backups()
    if refresh_auth:
        context.user.authentication_header = context.user.regenerate_header()

    backups = None
    backup_count_dict = {
        CSPBackupType.NATIVE_BACKUP: 0,
        CSPBackupType.HPE_CLOUD_BACKUP: 0,
        CSPBackupType.STAGING_BACKUP: 0,
    }

    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        backups = get_csp_machine_instance_backups(context, asset_id)
    elif asset_type == AssetType.CSP_VOLUME:
        backups = get_csp_volume_backups(context, asset_id)
    else:
        return backup_count_dict
    logger.info(f"Asset backups: {backups}")

    if backups and backups.total > 0:
        for backup in backups.items:
            if backup.backup_type == CSPBackupType.NATIVE_BACKUP.value and backup.state == BackupState.OK.value:
                backup_count_dict[CSPBackupType.NATIVE_BACKUP] += 1
            if backup.backup_type == CSPBackupType.HPE_CLOUD_BACKUP.value and backup.state == BackupState.OK.value:
                backup_count_dict[CSPBackupType.HPE_CLOUD_BACKUP] += 1
            if backup.backup_type == CSPBackupType.STAGING_BACKUP.value and backup.state == BackupState.OK.value:
                backup_count_dict[CSPBackupType.STAGING_BACKUP] += 1

    return backup_count_dict


def wait_for_asset_backups(
    context: Context,
    asset_id: str,
    asset_type: AssetType,
    backups_types: list[BackupType],
    initial_backup_count_dict: dict[CSPBackupType, int],
    expected_backup_count_dict: dict[CSPBackupType, int],
):
    """Checks that the given asset has the correct number of backups

    Args:
        context (Context): The test Context
        asset_id (str): The CSP Asset ID
        asset_type (AssetType): The CSP Asset Type
        backups_types (list[BackupType]): The Backup Type(s)
        initial_backup_count_dict (dict[CSPBackupType, int]): Initial backup count for each backup type
        expected_backup_count_dict (dict[CSPBackupType, int]): Expected backup count for each backup type

    Raises:
        e: Raised if Native backup count is incorrect
        e: Raised if Cloud backup count is incorrect
    """
    for backup_type in backups_types:
        logger.info(f"Wait for {backup_type.value}, asset id: {asset_id}, type: {asset_type}")

        if backup_type == BackupType.BACKUP:
            logger.info(f"Initial backups: {initial_backup_count_dict[CSPBackupType.NATIVE_BACKUP]}")
            logger.info(f"Additional expected backups: {expected_backup_count_dict[CSPBackupType.NATIVE_BACKUP]}")
            total_expected = (
                initial_backup_count_dict[CSPBackupType.NATIVE_BACKUP]
                + expected_backup_count_dict[CSPBackupType.NATIVE_BACKUP]
            )
            logger.info(f"total expected for: {BackupType.BACKUP.value}: {total_expected}")
            try:
                wait_for_backup_total(context, asset_id, asset_type, CSPBackupType.NATIVE_BACKUP, total_expected)
            except TimeoutExpired as e:
                total_reported = get_asset_backup_count(context, asset_id, asset_type)[CSPBackupType.NATIVE_BACKUP]
                logger.error(f"Native backups count invalid:  expected: {total_expected}, current: {total_reported}")
                raise e
            logger.info("Compare native backups count - success.")

        if backup_type == BackupType.CLOUD_BACKUP:
            logger.info(f"Initial backups: {initial_backup_count_dict[CSPBackupType.HPE_CLOUD_BACKUP]}")
            logger.info(f"Additional expected backups: {expected_backup_count_dict[CSPBackupType.HPE_CLOUD_BACKUP]}")

            expected_transient_count = expected_backup_count_dict[CSPBackupType.STAGING_BACKUP]
            initial_transient_count = initial_backup_count_dict[CSPBackupType.STAGING_BACKUP]
            initial_cloud_count = initial_backup_count_dict[CSPBackupType.HPE_CLOUD_BACKUP]
            # minus 1, because one transient is just for compare purpose
            if initial_transient_count > 0:
                initial_transient_count -= 1
            total_expected_cloud_backups = expected_transient_count + initial_cloud_count + initial_transient_count
            logger.info(f"total expected for: {BackupType.CLOUD_BACKUP.value}: {total_expected_cloud_backups}")
            try:
                wait(
                    lambda: get_asset_backup_count(context, asset_id, asset_type)[CSPBackupType.HPE_CLOUD_BACKUP]
                    == total_expected_cloud_backups,
                    timeout_seconds=60 * 60,
                    sleep_seconds=120,
                )
            except TimeoutExpired as e:
                total_reported = get_asset_backup_count(context, asset_id, asset_type)[CSPBackupType.HPE_CLOUD_BACKUP]
                logger.error(
                    f"Cloud backups count invalid:  expected: {total_expected_cloud_backups}, current: {total_reported}"
                )
                raise e
            logger.info(f"Compare cloud backups count - success. {total_expected_cloud_backups=}")


def wait_for_backups_status_ok(
    context: Context,
    asset_id: str,
    asset_type: AssetType,
    expected_backup_count: dict[str, dict[CSPBackupType, int]] = {},
    initial_backup_count: dict[str, dict[CSPBackupType, int]] = {},
):
    """Wait for backup status to be "OK" and for correct count of backups.

    Args:
        context (Context): The test Context
        asset_id (str): The CSP Asset ID
        asset_type (AssetType): The CSP Asset Type
            expected_backup_count (dict[str, dict[CSPBackupType, int]], optional):
                Dictionary of backups that will be made.
                Collected from protection jobs. If specified count will be verified.
            initial_backup_count: (dict[str, dict[CSPBackupType, int]], optional):
                Default will be 0.
                Dictionary of backups that are present before backup. Collected from backup list.
    """

    def _get_backups_status(
        context: Context,
        asset_id: str,
        asset_type: AssetType,
        initial_backup_count: dict[str, dict[CSPBackupType, int]] = {},
        expected_backup_count: dict[str, dict[CSPBackupType, int]] = {},
    ) -> bool:
        """Checks the state of the backups. Returns False if any of the backups aren't in OK State/Status

        Args:
            context (Context): The test Context
            asset_id (str): The CSP Asset ID
            asset_type (AssetType): The CSP Asset Type
            expected_backup_count (dict[str, dict[CSPBackupType, int]], optional):
                Dictionary of backups that will be made.
                Collected from protection jobs. If specified count will be verified.
            initial_backup_count: (dict[str, dict[CSPBackupType, int]], optional):
                Default will be 0.
                Dictionary of backups that are present before backup. Collected from backup list.

        Returns:
            bool: True if all the backups are in OK State/Status and
                if "expected_backup_count" specified is count correct.
        """
        backups = None
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            backups = get_csp_machine_instance_backups(context, asset_id)
        if asset_type == AssetType.CSP_VOLUME:
            backups = get_csp_volume_backups(context, asset_id)
        if asset_type == AssetType.CSP_K8S_APPLICATION:
            backups = context.eks_data_protection_manager.get_csp_k8s_app_backups(csp_k8s_application_id=asset_id)

        if expected_backup_count and expected_backup_count.get(asset_id):
            logger.info(f"wait for backup count: {initial_backup_count=}, {expected_backup_count=}")

            def _check_backup_count(
                initial_backup_count: dict[str, dict[CSPBackupType, int]],
                expected_backup_count: dict[str, dict[CSPBackupType, int]],
                backup_type: CSPBackupType,
            ):
                initial_backup_type_count = initial_backup_count[asset_id][backup_type] if initial_backup_count else 0
                expected_backups = expected_backup_count[asset_id][backup_type] + initial_backup_type_count
                current_backups = [backup for backup in backups.items if backup.backup_type == backup_type.value]
                logger.info(f"wait for backup count: {expected_backups=}, {current_backups=}")
                assert expected_backups == len(current_backups), f"Backup count for :{backup_type.value} is wrong. "

            try:
                _check_backup_count(initial_backup_count, expected_backup_count, CSPBackupType.NATIVE_BACKUP)
                _check_backup_count(initial_backup_count, expected_backup_count, CSPBackupType.HPE_CLOUD_BACKUP)
                _check_backup_count(initial_backup_count, expected_backup_count, CSPBackupType.STAGING_BACKUP)
            except Exception as e:
                logger.warning(e)
                return False

        logger.info(f"wait_for_backups_status_ok asset_id: {asset_id}, type:{asset_type} - backups:{backups}")
        if backups.total > 0:
            for backup in backups.items:
                if backup.state != BackupState.OK.value or backup.status != BackupState.OK.value:
                    return False

        return True

    wait(
        lambda: _get_backups_status(context, asset_id, asset_type, initial_backup_count, expected_backup_count),
        timeout_seconds=60 * 60,
        sleep_seconds=60,
    )


def wait_for_backup_index_status(
    context: Context, asset_type: AssetType, asset_id: str, backup_id: str, index_status: IndexStatus
):
    """Wait for the Backup ID from AssetType to have the expected IndexStatus

    Args:
        context (Context): The test context
        asset_type (AssetType): AssetType: CSP_VOLUME or CSP_MACHINE_INSTANCE
        asset_id (str): The Asset ID
        backup_id (str): The Backup ID
        index_status (IndexStatus): The desired IndexStatus
    """

    def _get_backup_index_status() -> IndexStatus:
        csp_backup: CSPBackupModel = None
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            csp_backup = get_csp_machine_instance_backup_by_id(context=context, backup_id=backup_id)
        else:  # Volume
            csp_backup = get_csp_volume_backup_by_id(
                context=context,
                volume_id=asset_id,
                backup_id=backup_id,
            )
        return csp_backup.index_status if csp_backup else None

    index_status_lambda = lambda: _get_backup_index_status() == index_status.value

    # default timeout is 10 minutes
    CommonSteps.wait_for_condition(
        lambda: index_status_lambda(),
        error_msg=f"CSP Backup {backup_id} did not reach IndexStatus: {index_status}",
    )


def verify_backup_consistency(
    context: Context, asset_id: str, asset_type: AssetType, consistency: BackupConsistency = BackupConsistency.CRASH
):
    """Checks that an asset has consistent backups

    Args:
        context (Context): The test Context
        asset_id (str): The CSP Asset ID
        asset_type (AssetType): The CSP Asset Type
        consistency (BackupConsistency, optional): Type of consistent state. Defaults to "BackupConsistency.CRASH".
    """
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        backups = get_csp_machine_instance_backups(context, asset_id)
    elif asset_type == AssetType.CSP_VOLUME:
        backups = get_csp_volume_backups(context, asset_id)

    logger.info(f"Check backup consistency for {asset_type}: {asset_id}")
    for backup in backups.items:
        assert (
            backup.consistency == consistency.value
        ), f"Consistency invalid {backup.consistency} for backup {backup.id}"


def run_backup_on_asset(
    context: Context,
    asset_id: str,
    backup_types: list[BackupType],
    async_func=None,
    expected_error: str = None,
    wait_for_task: bool = True,
    policy_id: str = None,
) -> str:
    """Execute "backup_types" for "asset_id".

    Args:
        context : Context
            Test Context
        asset_id : str
            The CSP Asset to execute protection job
        backup_types : list[BackupType]
            Allowed values: BackupType.SNAPSHOT, BackupType.BACKUP, BackupType.CLOUD_BACKUP
        async_func : Any, optional
            Function or partial function executed while waiting for task completion. Defaults to None.
        expected_error : str, optional
            If "wait_for_task" is True, this is the expected status of the Task. Defaults to None.
        wait_for_task : bool, optional
            If False, the function will not wait for the Protection Job task to complete. Defaults to True.
        policy_id : str, optional
            If provided, the Protection Job created by the "policy_id" is used.  Otherwise the 1st Protection Job is
            used.

    Raises:
        Exception: Thrown if there are no Protection Jobs associated with the "asset_id".

    Returns:
        str: The "task_id" of the Protection Job execution
    """
    protection_jobs = context.policy_manager.get_protection_job_by_asset_id(asset_id=asset_id)

    if protection_jobs.total == 0:
        logger.warning(f"Protection policy is not assigned to the asset: {asset_id}")
        raise Exception("No protection job found to trigger the backup")

    # We know we have at least 1 Protection Job
    protection_job = protection_jobs.items[0]

    # If "policy_id" is provided, look for matching "protectionPolicyInfo.id" to "policy_id"
    # if not found, continue to use 1st protection_job assigned above
    if policy_id:
        for job in protection_jobs.items:
            if job.protection_policy_info.id == policy_id:
                protection_job = job
                break

    protections = protection_job.protections

    schedule_ids = []
    for protection in protections:
        if BackupType(protection.type) in backup_types:
            # add all schedules; usual is only 1
            for schedule in protection.schedules:
                schedule_ids.append(schedule.schedule_id)
    logger.info(f"schedule ids found for backup type {backup_types}: {schedule_ids}")
    assert len(schedule_ids), f"No 'scheduleIds' acquired for request: {backup_types}"

    # execute the protection job
    task_id: str = context.policy_manager.run_protection_job(
        protection_job_id=protection_job.id, protection_schedule_ids=schedule_ids
    )

    if async_func:
        time.sleep(5)
        async_func()

    if wait_for_task:
        timeout = TimeoutManager.standard_task_timeout
        status: str = tasks.wait_for_task(task_id, context.user, timeout)

        if expected_error:
            assert status == expected_error
            logger.info(f"Backup task finished with expected error: {expected_error}")
        else:
            assert (
                status.upper() == TaskStatus.success.value
            ), f"Backup initial task failed for the asset {asset_id}, Check the task logs for more information"
            logger.info(f"Backup task completed for the asset {asset_id}")

    # return the protection_job task_id
    return task_id


def run_backup(
    context: Context,
    asset_id: str,
    backup_types: list[BackupType],
    async_func=None,
    expected_error: str = None,
) -> tuple[dict[str, dict[CSPBackupType, int]], (list, list)]:
    """Runs Backup(s) given asset and type(s) of backup

    Args:
        context (Context): The test Context
        asset_id (str): The CSP Asset ID
        backup_types (list[BackupType]): Backup Type(s)
        async_func (Any, optional): function or partial function executed while waiting for task completion. Defaults to None.
        expected_error (str, optional): The expected status of the task. Defaults to None.

    Raises:
        Exception: Thrown if asset has no protection job.

    Returns:
        (dict[str, dict[CSPBackupType, int]], (list, list)): The dict with backup count for each asset, the root task id list, and the protection job task id list.
    """
    protection_jobs = context.policy_manager.get_protection_job_by_asset_id(asset_id=asset_id)

    if protection_jobs.total == 0:
        logger.warning(f"Protection policy is not assigned to the asset: {asset_id}")
        raise Exception("No protection job found to trigger the backup")

    protection_job = protection_jobs.items[0]

    protections = protection_job.protections

    expected_backup_count_dict = {
        CSPBackupType.NATIVE_BACKUP: 0,
        CSPBackupType.HPE_CLOUD_BACKUP: 0,
        CSPBackupType.STAGING_BACKUP: 0,
    }

    schedule_ids = []
    for protection in protections:
        backup_type = BackupType(protection.type)
        if backup_type in backup_types:
            schedule_ids.append(protection.schedules[0].schedule_id)
            if backup_type == BackupType.BACKUP:
                expected_backup_count_dict[CSPBackupType.NATIVE_BACKUP] += 1
            if backup_type == BackupType.CLOUD_BACKUP:
                expected_backup_count_dict[CSPBackupType.STAGING_BACKUP] += 1
    logger.info(f"schedule ids found for backup type {backup_types}: {schedule_ids}")
    if not schedule_ids:
        return expected_backup_count_dict, None
    start_date = formatdate(timeval=None, localtime=False, usegmt=True)
    root_task_id_list: list = []
    schedule_task_id_list: list = []
    backup_asset_count_dict = {}

    for schedule_id in schedule_ids:
        schedule_task_id: str = context.policy_manager.run_protection_job(
            protection_job_id=protection_job.id, protection_schedule_ids=[schedule_id]
        )
        logger.info(f"Protection Job TaskID: {schedule_task_id}")
        root_task_id = None

        if async_func:
            time.sleep(5)
            async_func()

        timeout = TimeoutManager.create_backup_timeout
        status: str = tasks.wait_for_task(schedule_task_id, context.user, timeout)

        if expected_error:
            assert status == expected_error, f"Status {status} does NOT equal expected Error {expected_error}"
            logger.info(f"Backup task finished with expected error {expected_error}")
        else:
            assert (
                status.upper() == TaskStatus.success.value
            ), f"Backup initial task failed for the asset {asset_id}, Check the task logs for more information"
            logger.info(f"Backup task completed for the asset {asset_id}")
            task_name = " Backup "
            root_task_id = tasks.wait_for_task_resource(context.user, asset_id, task_name, start_date)

        if protection_job.asset_info.type == ResourceType.CSP_PROTECTION_GROUP.value:
            logger.info("Protection Group")
            protection_group = context.inventory_manager.get_protection_group_by_id(asset_id)
            filter: str = f"{protection_group.id} in protectionGroupInfo/id"
            filter_csp_instances: CSPMachineInstanceListModel = IMS.get_csp_instances(context=context, filter=filter)
            for instance in filter_csp_instances.items:
                backup_asset_count_dict[instance.id] = expected_backup_count_dict
            filter_csp_volumes: CSPVolumeListModel = IMS.get_csp_volumes(context=context, filter=filter)
            for volume in filter_csp_volumes.items:
                backup_asset_count_dict[volume.id] = expected_backup_count_dict
        else:
            logger.info("Asset")
            backup_asset_count_dict[asset_id] = expected_backup_count_dict
        root_task_id_list.append(root_task_id)
        schedule_task_id_list.append(schedule_task_id)
        # Sleep time is a temporary workaround for the AMI failure when running multiple schedules at once.
        time.sleep(60)

    return backup_asset_count_dict, (root_task_id_list, schedule_task_id_list)


def run_backup_for_protection_job(context: Context, protection_job_id: str):
    """Runs backup given a protection job id

    Args:
        context (Context): The test Context
        protection_job_id (str): ID of the Protection Job that's to be executed
    """
    task_id = context.policy_manager.run_protection_job(protection_job_id=protection_job_id)
    # Note: the status is returned lowercase; TaskStatus enum is uppercase
    protection_job_task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.standard_task_timeout)
    assert (
        protection_job_task_status.upper() == TaskStatus.success.value
    ), f"Protection Job Task State {protection_job_task_status.upper()} does NOT equal expected Success Value {TaskStatus.success.value}"


def get_backup_count_dict(
    context: Context,
    asset_set: Union[AssetSet, AssetSetAzure],
) -> dict[str, dict[CSPBackupType, int]]:
    """Gets number of backups for each asset

    Args:
        context (Context): The test Context
        asset_set (Union[AssetSet, AssetSetAzure]): Standard Assets

    Returns:
        dict[str, dict[CSPBackupType, int]]: Backup count for each asset
    """
    backup_count_dict = {}

    asset_id_list, asset_type_list = asset_set.get_standard_assets()
    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if not asset_id:
            continue
        if asset_type != AssetType.CSP_PROTECTION_GROUP:
            backup_count_dict[asset_id] = get_asset_backup_count(context, asset_id, asset_type)

    return backup_count_dict


def run_prod_cloud_backup_for_standard_assets(
    context: Context,
    asset_set: Union[AssetSet, AssetSetAzure],
) -> tuple[dict[str, dict[CSPBackupType, int]], dict[str, dict[CSPBackupType, int]]]:
    """Run cloud backup for standard assets on production cluster

    Args:
        context (Context): The test Context
        asset_set (Union[AssetSet, AssetSetAzure]): Standard Assets

    Returns:
        (dict[str, dict[CSPBackupType, int]], dict[str, dict[CSPBackupType, int]]):
            Expected Backup Count for each asset after the Backup is taken, Initial Backup Count for each asset before the Backup is taken
    """

    initial_backup_count_dict = get_backup_count_dict(context, asset_set)
    expected_backup_count_dict = {}

    asset_id_list, asset_type_list = asset_set.get_standard_assets()
    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if not asset_id:
            continue
        # calculate expected count of backups
        expected_backups_count_asset_dict, _ = run_backup(context, asset_id, backup_types=[BackupType.CLOUD_BACKUP])
        for asset_backups in expected_backups_count_asset_dict:
            if expected_backup_count_dict.get(asset_backups) is not None:
                for backup_asset_type in expected_backup_count_dict[asset_backups]:
                    expected_backup_count_dict[asset_backups][backup_asset_type] = (
                        expected_backup_count_dict[asset_backups][backup_asset_type]
                        + expected_backups_count_asset_dict[asset_backups][backup_asset_type]
                    )
            else:
                expected_backup_count_dict[asset_backups] = expected_backups_count_asset_dict[asset_backups]

    # wait for backup status and state
    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if asset_id and asset_type != AssetType.CSP_PROTECTION_GROUP:
            wait_for_backups_status_ok(context, asset_id, asset_type)

    return expected_backup_count_dict, initial_backup_count_dict


def run_backup_for_standard_assets_and_validate_count(
    context: Context,
    asset_set: Union[AssetSet, AssetSetAzure],
    account_name: str,
    region: str,
    backup_types: list[BackupType] = [BackupType.BACKUP],
    aws: AWS = None,
) -> tuple[dict[str, dict[CSPBackupType, int]], dict[str, dict[CSPBackupType, int]]]:
    """Run the backups for standard assets and validate the backup count

    Args:
        context (Context): The test Context
        asset_set (Union[AssetSet, AssetSetAzure]): Standard Assets
        account_name (str): CSP Account Name
        region (str): the region for /copy2cloud call
        backup_types (list[BackupType], optional): Types of Backup. Defaults to [BackupType.BACKUP].
        aws (AWS, optional): AWS Account. Defaults to None. If not provided, "context.aws_one" will be used.

    Returns:
        (dict[str, dict[CSPBackupType, int]], dict[str, dict[CSPBackupType, int]]):
            Expected Backup Count for each asset after the Backup is taken, Initial Backup Count for each asset before the Backup is taken
    """
    # if asset_set is AWS AssetSet
    if isinstance(asset_set, AssetSet):
        if not aws:
            aws = context.aws_one
        region = aws.region_name

    initial_backup_count_dict = get_backup_count_dict(context, asset_set)
    expected_backups_count_dict = {}
    asset_id_list, asset_type_list = asset_set.get_standard_assets()

    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if not asset_id:
            continue
        # calculate expected count of backups
        logger.info(f"Run Backups on AssetID: {asset_id}  AssetType: {asset_type}  BackupTypes: {backup_types}")
        expected_backups_count_asset_dict, tasks_ids = run_backup(context, asset_id, backup_types=backup_types)
        logger.info(
            f"Expected Backup Count: {expected_backups_count_asset_dict}  RootTaskID, ProtectionJobTaskID: {tasks_ids}"
        )

        for asset_backups in expected_backups_count_asset_dict:
            if expected_backups_count_dict.get(asset_backups) is not None:
                logger.info(f"Adding onto existing 'expected_backups_count_dict' for: {asset_backups}")
                for backup_asset_type in expected_backups_count_dict[asset_backups]:
                    expected_backups_count_dict[asset_backups][backup_asset_type] = (
                        expected_backups_count_dict[asset_backups][backup_asset_type]
                        + expected_backups_count_asset_dict[asset_backups][backup_asset_type]
                    )
            else:
                logger.info(f"Adding new 'expected_backups_count_dict' for {asset_backups}")
                expected_backups_count_dict[asset_backups] = expected_backups_count_asset_dict[asset_backups]

    # wait for backup status and state
    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if asset_id and asset_type != AssetType.CSP_PROTECTION_GROUP:
            wait_for_backups_status_ok(
                context, asset_id, asset_type, expected_backups_count_dict, initial_backup_count_dict
            )
    if BackupType.CLOUD_BACKUP in backup_types:
        # if asset_set is AWS AssetSet
        if isinstance(asset_set, AssetSet):
            get_ami_and_snapshot_status_list(aws)

        # infrequently, Sanity "test_run_backups" fails due to a Cloud Backup count mismatch:
        #       Cloud backups count invalid:  expected: 3, current: 2
        # 1 time, manual testing witnessed a Cloud backup that did not get picked up my the "copy2cloud" call; DCS-11453
        # We will wait here for a bit to help ensure the "copy2cloud" call considers all Cloud Backups for our testing
        time.sleep(60)
        start_date = formatdate(timeval=None, localtime=False, usegmt=True)
        run_copy2cloud_endpoint(context, account_name, region)
        # wait for backup status and state
        for asset_id, asset_type in zip(asset_id_list, asset_type_list):
            if asset_id and asset_type != AssetType.CSP_PROTECTION_GROUP:
                tasks.wait_for_task_resource(
                    user=context.user,
                    resource_id=asset_id,
                    task_display_name="CloudBackup Workflow",
                    date_start=start_date,
                    wait_completed=True,
                    parent_task_name="CSPBackupParentWorkflow",
                )

    verify_taken_backups(context, asset_set, expected_backups_count_dict, initial_backup_count_dict, backup_types)

    return expected_backups_count_dict, initial_backup_count_dict


def verify_taken_prod_cloud_backups(
    context: Context,
    asset_set: Union[AssetSet, AssetSetAzure],
    expected_backup_count_dict: dict[CSPBackupType, int],
    initial_backup_count_dict: dict[CSPBackupType, int],
    timeout: int = 21600,  # 6h
    interval: int = 600,
):
    """Verify cloud backup was taken

    Args:
        context (Context): The test Context
        asset_set (Union[AssetSet, AssetSetAzure]): Standard Assets
        expected_backup_count_dict (dict[CSPBackupType, int]): Expected number of backups after cloud backup is taken
        initial_backup_count_dict (dict[CSPBackupType, int]): Initial number of backups before cloud backup is taken
        timeout (int, Optional): The timeout to wait for Cloud Backups. Defaults to 21600 (6 hours)
        interval (int, Optional): The time between each query to the Cloud Backup count

    Raises:
        e: Raised if cloud backup count isn't as expected
    """
    asset_id_list, asset_type_list = asset_set.get_standard_assets()

    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if asset_id and asset_type != AssetType.CSP_PROTECTION_GROUP:
            logger.info(f"Initial cloud backups: {initial_backup_count_dict[asset_id][CSPBackupType.HPE_CLOUD_BACKUP]}")
            logger.info(
                f"Additional expected backups: {expected_backup_count_dict[asset_id][CSPBackupType.STAGING_BACKUP]}"
            )

            expected_transient_count = expected_backup_count_dict[asset_id][CSPBackupType.STAGING_BACKUP]
            initial_transient_count = initial_backup_count_dict[asset_id][CSPBackupType.STAGING_BACKUP]
            initial_cloud_count = initial_backup_count_dict[asset_id][CSPBackupType.HPE_CLOUD_BACKUP]
            # minus 1, because one transient is just for compare purpose
            if initial_transient_count > 0:
                initial_transient_count -= 1

            total_expected_cloud_backups = expected_transient_count + initial_cloud_count + initial_transient_count
            logger.info(f"total expected for: {BackupType.CLOUD_BACKUP.value}: {total_expected_cloud_backups}")

            # We need to wait for the scheduled Cloud Backup activity (/copy2cloud) at the midnight hour in the region,
            # we will Sleep for 1 Hour (3600), and Timeout after 12 Hours (43200)
            try:
                wait(
                    lambda: get_asset_backup_count(
                        context=context, asset_id=asset_id, asset_type=asset_type, refresh_auth=True
                    )[CSPBackupType.HPE_CLOUD_BACKUP]
                    == total_expected_cloud_backups,
                    timeout_seconds=timeout,
                    sleep_seconds=interval,
                )
            except TimeoutExpired as e:
                total_reported = get_asset_backup_count(
                    context=context, asset_id=asset_id, asset_type=asset_type, refresh_auth=True
                )[CSPBackupType.HPE_CLOUD_BACKUP]
                logger.error(
                    f"Cloud backups count invalid: expected: {total_expected_cloud_backups}, current: {total_reported}"
                )
                raise e

            logger.info(f"Compare cloud backups count - success. {total_expected_cloud_backups=}")


def verify_taken_backups(
    context: Context,
    asset_set: Union[AssetSet, AssetSetAzure],
    expected_backups_count_dict: dict[str, dict[CSPBackupType, int]],
    initial_backup_count_dict: dict[str, dict[CSPBackupType, int]],
    backup_types: list[BackupType] = [BackupType.BACKUP],
):
    """Verify backup is taken

    Args:
        context (Context): The test Context
        asset_set (Union[AssetSet, AssetSetAzure]): Standard Assets
        expected_backups_count_dict (dict[str, dict[CSPBackupType, int]]): Expected number of backups after backup is taken
        initial_backup_count_dict (dict[str, dict[CSPBackupType, int]]): Initial number of backups before backup is taken
        backup_types (list[BackupType], optional): Type of Backup(s). Defaults to [BackupType.BACKUP].
    """
    asset_id_list, asset_type_list = asset_set.get_standard_assets()
    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if asset_id and asset_type != AssetType.CSP_PROTECTION_GROUP:
            wait_for_asset_backups(
                context,
                asset_id,
                asset_type,
                backup_types,
                initial_backup_count_dict[asset_id],
                expected_backups_count_dict[asset_id],
            )
            verify_backup_consistency(context, asset_id, asset_type)


def run_copy2cloud_endpoint(context: Context, account_name: str, region: str):
    """Workaround to do backup right away. Currently transient backups are performed only once a day

    Args:
        context (Context): The test Context
        account_name (str): CSP Account
        region (str): CSP Region
    """
    csp_account = CAMS.get_csp_account_by_csp_name(context, account_name=account_name)
    context.data_protection_manager.complete_transient_backup(csp_account.customerId, csp_account.id, region)


def get_ami_and_snapshot_status_list(aws: AWS):
    """Gets all EC2 AMIs and EBS Snapshots given AWS Account

    Args:
        aws (AWS): AWS Account
    """
    amis = aws.ec2.get_all_amis()
    logger.debug(f"Amis: {amis}")
    snapshots = aws.ebs.get_all_snapshots()
    logger.debug(f"Snapshots: {snapshots}")


def delete_machine_instance_backups(context: Context, instance_id: str, wait_for_error: bool = False) -> list[str]:
    """Deletes Backups given CSP Machine Instance

    Args:
        context (Context): The test Context
        instance_id (str): CSP Machine Instance ID
        wait_for_error (bool, optional): Waits for task failure. Defaults to False.

    Returns:
        list[str]: List of task ids for backups that were deleted
    """
    backup_list = get_csp_machine_instance_backups(context=context, machine_instance_id=instance_id)

    cloud_tasks: list[str] = []

    if not backup_list.total:
        logger.warning(f"There are no backups to delete for Instance: '{instance_id}'")
        return cloud_tasks

    logger.info(f"There are {backup_list.total} backups")

    for backup in backup_list.items:
        logger.info(f"backupType: {backup.backup_type}")
        # skip Staging
        if backup.backup_type == CSPBackupType.STAGING_BACKUP.value:
            logger.info("skip staging")
            continue

        # Due to DCS-5586, each delete backup is taking 15 minutes.
        # "test_delete_backups" has failed with "JWT is expired"
        # JWT token expires after 2 hours.
        # Sanity Suite has 6 non-staging backups for the EC2 alone.
        logger.info("Regenerating user authentication header")
        context.user.authentication_header = context.user.regenerate_header()

        # start the delete task
        logger.info(ASTERISK_LINE)
        logger.info(
            (
                f"deleting {backup.backup_type} backup: {backup.id} for EC2 {instance_id}. "
                f"Start time = {datetime.now(time_zone)}"
            )
        )
        task_id = delete_csp_machine_instance_backup_by_id(
            context=context, machine_instance_id=instance_id, backup_id=backup.id
        )

        logger.info(f"Waiting for Delete backup for Instance {instance_id} task: {task_id}")
        # for the case where 'None' is returned from 'delete_backups_check_task()', don't add it to 'cloud_tasks'
        cloud_task_id = delete_backups_check_task(
            context=context, asset_id=instance_id, task_id=task_id, backup=backup, wait_for_error=wait_for_error
        )
        if cloud_task_id:
            cloud_tasks.append(cloud_task_id)

        logger.info(
            (
                f"deleted {backup.backup_type} backup: {backup.id} for EC2 {instance_id}. "
                f"End time = {datetime.now(time_zone)}"
            )
        )
        logger.info(ASTERISK_LINE)

    return cloud_tasks


def delete_ec2_instance_backups(
    context: Context,
    ec2_instance_ids: list[str],
    csp_account: CSPAccountModel,
    region: str,
):
    """Delete all CSP Backups associated with the given list of EC2 (AWS) Instance IDs

    Args:
        context (Context): The test Context
        ec2_instance_ids (list[str]): The EC2 (AWS) Instance IDs
        csp_account (CSPAccountModel): The CSP Account
        region (str): The region for the CSP Account
    """
    csp_instance_ids: list[str] = []

    # get CSP Instance IDs for all provided EC2 Instance IDs
    for ec2_instance_id in ec2_instance_ids:
        csp_instance = IMS.get_csp_instance_by_ec2_instance_id(context=context, ec2_instance_id=ec2_instance_id)
        if csp_instance:
            csp_instance_ids.append(csp_instance.id)

    # now call "delete_csp_instance_backups()", which handles Cloud Backup Delete tasks
    delete_csp_instance_backups(context=context, instance_ids=csp_instance_ids, csp_account=csp_account, region=region)


def delete_csp_instance_backups(context: Context, instance_ids: list[str], csp_account: CSPAccountModel, region: str):
    """Delete all CSP Backups associated with the given list of CSP Instance IDs

    Args:
        context (Context): The test Context
        instance_ids (list[str]): The CSP Instance IDs
        csp_account (CSPAccountModel): The CSP Account
        region (str): The region for the CSP Account
    """
    cloud_tasks: list[str] = []

    # delete_machine_instance_backups() handles "Cloud Backup Deletion", returns list of Cloud Backup Delete task IDs
    for instance_id in instance_ids:
        logger.info(f"Deleting backups for CSP Instance: {instance_id}")
        cloud_tasks.extend(delete_machine_instance_backups(context=context, instance_id=instance_id))
        logger.info(f"Number of Cloud delete tasks: {len(cloud_tasks)}")

    # if cloud_tasks are returned, then perform /copy2cloud for the cloud delete tasks
    if len(cloud_tasks):
        logger.info(f"Performing /copy2cloud for {len(cloud_tasks)} Cloud Backup Delete Tasks...")
        perform_copy2cloud_for_delete_tasks(
            context=context, csp_account=csp_account, region=region, cloud_tasks=cloud_tasks
        )


def delete_ebs_volume_backups(context: Context, ebs_volume_ids: list[str], csp_account: CSPAccountModel, region: str):
    """Delete all CSP Backups associated with the given list of EBS (AWS) Volume IDs

    Args:
        context (Context): The test Context
        ebs_volume_ids (list[str]): The EBS (AWS) Volume IDs
        csp_account (CSPAccountModel): The CSP Account
        region (str): The region for the CSP Account
    """
    csp_volume_ids: list[str] = []

    # get CSP Volume IDs for all provided EBS Volume IDs
    for ebs_volume_id in ebs_volume_ids:
        csp_volume = IMS.get_csp_volume_by_ebs_volume_id(context=context, ebs_volume_id=ebs_volume_id)
        if csp_volume:
            csp_volume_ids.append(csp_volume.id)

    # now call "delete_csp_volume_backups()", which handles Cloud Backup Delete tasks
    delete_csp_volume_backups(context=context, volume_ids=csp_volume_ids, csp_account=csp_account, region=region)


def delete_csp_volume_backups(context: Context, volume_ids: list[str], csp_account: CSPAccountModel, region: str):
    """Delete all CSP Backups associated with the given list of CSP Volume IDs

    Args:
        context (Context): The test Context
        volume_ids (list[str]): The CSP Volume IDs
        csp_account (CSPAccountModel): The CSP Account
        region (str): The region for the CSP Account
    """
    cloud_tasks: list[str] = []

    # NOTE: "delete_volume_backups()" handles "Cloud Backup Deletion", returns list of Cloud Backup Delete task IDs
    for volume_id in volume_ids:
        logger.info(f"Deleting backups for CSP Volume: {volume_id}")
        cloud_tasks.extend(delete_volume_backups(context=context, volume_id=volume_id))
        logger.info(f"Number of Cloud delete tasks: {len(cloud_tasks)}")

    # if cloud_tasks are returned, then perform /copy2cloud for the cloud delete tasks
    if len(cloud_tasks):
        logger.info(f"Performing /copy2cloud for {len(cloud_tasks)} Cloud Backup Delete Tasks...")
        logger.info(ASTERISK_LINE)
        logger.info(
            (
                f"Start time for Copy2Cloud for Backup Deletion for Account: {csp_account.name}, {csp_account.id}, "
                f"Region: {region} is {datetime.now(time_zone)}"
            )
        )
        perform_copy2cloud_for_delete_tasks(
            context=context, csp_account=csp_account, region=region, cloud_tasks=cloud_tasks
        )
        logger.info(
            (
                f"End time for Copy2Cloud for Backup Deletion for Account: {csp_account.name}, {csp_account.id}, "
                f"Region: {region} is {datetime.now(time_zone)}"
            )
        )
        logger.info(ASTERISK_LINE)


def delete_volume_backups(context: Context, volume_id: str, wait_for_error: bool = False) -> list[str]:
    """Deletes Backups given CSP Volume

    Args:
        context (Context): The test Context
        volume_id (str): CSP Volume ID
        wait_for_error (bool, optional): Waits for task failure. Defaults to False.

    Returns:
        list[str]: List of task ids for backups that were deleted
    """
    backup_list = get_csp_volume_backups(context=context, volume_id=volume_id)

    cloud_tasks: list[str] = []

    if not backup_list.total:
        logger.warning(f"There are no backups to delete for Volume: '{volume_id}'")
        return cloud_tasks

    logger.info(f"There are {backup_list.total} backups")

    for backup in backup_list.items:
        logger.info(f"backupType: {backup.backup_type}")
        # skip Staging
        if backup.backup_type == CSPBackupType.STAGING_BACKUP.value:
            logger.info("skip staging")
            continue

        # Due to DCS-5586, each delete backup is taking 15 minutes.
        # "test_delete_backups" has failed with "JWT is expired"
        # JWT token expires after 2 hours.
        # Sanity Suite has 6 non-staging backups for the EC2 alone.
        logger.info("Regenerating user authentication header")
        context.user.authentication_header = context.user.regenerate_header()

        # start the delete task
        logger.info(ASTERISK_LINE)
        logger.info(
            (
                f"deleting {backup.backup_type} backup: {backup.id} for EBS {volume_id}. "
                f"Start time = {datetime.now(time_zone)}"
            )
        )
        task_id = delete_csp_volume_backup_by_id(context=context, volume_id=volume_id, backup_id=backup.id)
        logger.info(f"Waiting for Delete backup for Volume {volume_id} task: {task_id}")
        # for the case where 'None' is returned from 'delete_backups_check_task()', don't add it to 'cloud_tasks'
        cloud_task_id = delete_backups_check_task(
            context=context, asset_id=volume_id, task_id=task_id, backup=backup, wait_for_error=wait_for_error
        )
        if cloud_task_id:
            cloud_tasks.append(cloud_task_id)
        logger.info(
            (
                f"deleting {backup.backup_type} backup: {backup.id} for EBS {volume_id}. "
                f"Start time = {datetime.now(time_zone)}"
            )
        )
        logger.info(ASTERISK_LINE)

    return cloud_tasks


def delete_backups_check_task(
    context: Context, asset_id: str, task_id: str, backup: CSPBackupModel, wait_for_error: bool = False
) -> str:
    """Checks that backup is deleted

    Args:
        context (Context): The test Context
        asset_id (str): Asset ID
        task_id (str): Delete Task ID
        backup (CSPBackupModel): CSP Backup to delete
        wait_for_error (bool, optional): Waits for Error. Defaults to False.

    Raises:
        PermissionError: In the case that the task fails

    Returns:
        str: Task ID in the case of a cloud backup
    """
    if wait_for_error:
        logger.info(f"Waiting for delete task error: {task_id}")
        status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.delete_backup_timeout)
        if status.upper() == TaskStatus.failed.value:
            raise PermissionError

    # if deleting a Cloud Backup, return to caller
    if backup.backup_type == CSPBackupType.HPE_CLOUD_BACKUP.value:
        logger.info(f"Adding Cloud Backup to return list: {backup.id}")
        return task_id
    else:
        # otherwise, we can wait for the task to complete
        logger.info(f"Waiting for non-Cloud delete backup task to complete: {task_id}")
        status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.delete_backup_timeout)
        assert (
            status.upper() == TaskStatus.success.value
        ), f"Backup '{backup.id}' deletion failed for '{asset_id}', Check the task logs for more information"
        logger.info(f"Backup deletion task completed for '{asset_id}'")


def delete_backup_for_standard_assets_for_account(
    context: Context,
    asset_set: Union[AssetSet, AssetSetAzure],
    csp_account: CSPAccountModel,
    region: str,
    wait_for_error: bool = False,
    perform_copy2cloud: bool = True,
):
    """Delete Backups for the Standard Assets provided.
    This function handles Cloud Backup Deletion, which now requires a /copy2cloud call to fully complete.

    Args:
        context (Context): Test Context
        asset_set (Union[AssetSet, AssetSetAzure]): Standard Assets
        csp_account (CSPAccountModel): CSP Account
        region (str): CSP Account Region
        wait_for_error (bool): If expecting an error, passing True will wait for the task to fail. Defaults to False
        perform_copy2cloud (bool): Set to True to perform copy2cloud for delete cloud backups tasks. Defaults to True.
    """
    asset_id_list, asset_type_list = asset_set.get_standard_assets()

    all_cloud_tasks: list[str] = []

    for asset_id, asset_type in zip(asset_id_list, asset_type_list):
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            logger.info(f"Deleting CSP Machine: {asset_id} backups...")
            # add any returned Cloud delete tasks to master list
            all_cloud_tasks.extend(
                delete_machine_instance_backups(context=context, instance_id=asset_id, wait_for_error=wait_for_error)
            )

        elif asset_type == AssetType.CSP_VOLUME:
            logger.info(f"Deleting CSP Volume: {asset_id} backups...")
            # add any returned Cloud delete tasks to master list
            all_cloud_tasks.extend(
                delete_volume_backups(context=context, volume_id=asset_id, wait_for_error=wait_for_error)
            )

        # the Cloud and Native backups should go to 0 in DSCC
        wait_for_backup_total(context, asset_id, asset_type, CSPBackupType.NATIVE_BACKUP, 0)
        wait_for_backup_total(context, asset_id, asset_type, CSPBackupType.HPE_CLOUD_BACKUP, 0)

        logger.info(f"backup totals met for asset: {asset_id}")

    if perform_copy2cloud:
        perform_copy2cloud_for_delete_tasks(
            context=context, csp_account=csp_account, region=region, cloud_tasks=all_cloud_tasks
        )


def perform_copy2cloud_for_delete_tasks(
    context: Context, csp_account: CSPAccountModel, region: str, cloud_tasks: list[str]
):
    """Deletes cloud backups ands runs copy2cloud for them

    Args:
        context (Context): The test Context
        csp_account (CSPAccountModel): CSP Account
        region (str): CSP Region
        cloud_tasks (list[str]): Task IDs for cloud backup deletion
    """
    # nothing to do if there are no tasks provided
    if not len(cloud_tasks):
        logger.info("There are no Cloud Delete tasks, returning")
        return

    logger.info(f"Checking cloud backup delete list len(): {len(cloud_tasks)}")

    # Wait for all Cloud Backup Delete tasks to reach 50 percent
    for task_id in cloud_tasks:
        logger.info(f"Waiting for Cloud Backup Delete task: {task_id} to reach 50%")
        tasks.wait_for_task_percent_complete(
            task_id=task_id, user=context.user, percent_complete=50, timeout=TimeoutManager.standard_task_timeout
        )

    # now we can run /copy2cloud
    logger.info(f"Calling Copy2Cloud for {csp_account.name} in Region {region}")
    run_copy2cloud_endpoint(context=context, account_name=csp_account.name, region=region)
    logger.info("copy2cloud endpoint called")

    logger.info(
        (
            "Find and wait for copy2cloud task to complete. "
            f"customerId: {csp_account.customerId} accountID: {csp_account.id}"
        )
    )
    # look for and wait for the "TaskForNightlyCVSACycle <region>" task to complete
    copy2cloud_task_id = find_and_wait_for_copy2cloud(
        context=context,
        customer_id=csp_account.customerId,
        account_id=csp_account.id,
        account_name=csp_account.name,
        region=region,
    )
    logger.info(f"copy2cloud task: {copy2cloud_task_id} is complete")

    logger.info(f"Now wait for {len(cloud_tasks)} 50% Cloud Backup Delete tasks to reach 100%")
    # Wait for all tasks to reach 100 percent
    for task_id in cloud_tasks:
        logger.info(f"Waiting for Cloud Delete task: {task_id} to reach 100%")
        task = tasks.get_task_object(user=context.user, task_id=task_id)
        logger.info(ASTERISK_LINE)
        logger.info(
            (
                f"Start time for Cloud Backup Deletion Task: {task.name} "
                f"for Account: {csp_account.name}, {csp_account.id}, Region: {region}, "
                f"Resource: {task.source_resource}, Message: {task.log_messages} is {datetime.now(time_zone)}"
            )
        )
        tasks.wait_for_task_percent_complete(
            task_id=task_id, user=context.user, percent_complete=100, timeout=TimeoutManager.standard_task_timeout
        )
        logger.info(
            (
                f"End time for Cloud Backup Deletion Task: {task.name} "
                f"for Account: {csp_account.name}, {csp_account.id}, Region: {region}, "
                f"Resource: {task.source_resource}, Message: {task.log_messages} is {datetime.now(time_zone)}"
            )
        )
        logger.info(ASTERISK_LINE)
        logger.info(f"Delete Cloud Backup task {task_id} complete")


class KafkaBackupNotifier:
    """
    This class is to hold Kafka backup notification data and exposes methods to send Kafka backup updates.
    This class can be used in functional test cases where actual backup services are not available.
    """

    def __init__(
        self,
        context: Context,
        customer_id: str,
        backup_type: KafkaBackupType,
        asset_id: str,
        asset_type: KafkaInventoryAssetType,
        protection_job_id: str,
        schedule_id: int,
    ):
        self._context = context
        self._customer_id = customer_id
        self._backup_id = str(uuid.uuid4())
        self._backup_type = backup_type
        self._asset_id = asset_id
        self._asset_type = asset_type
        self._protection_job_id = protection_job_id
        self._schedule_id = schedule_id

    def get_backup_id(self):
        """Returns backup id

        Returns:
            str: Backup id
        """
        return self._backup_id

    def create(self, event_status: BackupKafkaEventStatus, wait_for_job: bool = True):
        """Constructs the payload and sends backup updates to the right Kafka topic.

        Args:
            event_status (BackupKafkaEventStatus): Event Status
            wait_for_job (bool, optional): Waits for Backup Count. Defaults to True.
        """

        send_backup_updates(
            context=self._context,
            customer_id=self._customer_id,
            backup_id=self._backup_id,
            backup_type=self._backup_type,
            asset_id=self._asset_id,
            asset_type=self._asset_type,
            protection_job_id=self._protection_job_id,
            schedule_id=self._schedule_id,
            event_status=event_status,
            wait_for_job=wait_for_job,
        )

    def delete(self, wait_for_job: bool = True):
        """Constructs the payload and sends delete backup notification to right Kafka topic.

        Args:
            wait_for_job (bool, optional): Waits for backup count. Defaults to True.
        """

        send_delete_backup_updates(
            context=self._context,
            customer_id=self._customer_id,
            backup_id=self._backup_id,
            backup_type=self._backup_type,
            asset_id=self._asset_id,
            asset_type=self._asset_type,
            wait_for_job=wait_for_job,
        )


def get_csp_type_for_backup_asset_type(asset_type: KafkaInventoryAssetType) -> AssetType:
    """Returns csp asset type for kafka backup asset type

    Args:
        asset_type (KafkaInventoryAssetType): Kafka Asset Type

    Returns:
        AssetType: CSP Asset Type
    """
    if asset_type == KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE:
        return AssetType.CSP_MACHINE_INSTANCE
    elif asset_type == KafkaInventoryAssetType.ASSET_TYPE_VOLUME:
        return AssetType.CSP_VOLUME


def get_backup_count_from_asset(context: Context, asset_id: str, asset_type: AssetType) -> int:
    """Returns backup count for an asset type

    Args:
        context (Context): The test Context
        asset_id (str): The CSP Asset ID
        asset_type (AssetType): The CSP Asset Type

    Returns:
        int: Number of Backups for given Asset
    """
    backups = None
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        instance = IMS.get_csp_instance_by_id(context, asset_id)
        backups = instance.backupInfo
    if asset_type == AssetType.CSP_VOLUME:
        volume = IMS.get_csp_volume_by_id(context, asset_id)
        backups = volume.backupInfo
    count = 0
    if backups is not None:
        for backup in backups:
            count = count + backup.count
    logger.info(f"get_backup_count_from_asset() == {count}")
    return count


def get_schedule_status(
    context: Context, protection_job_id: str, schedule_id: int, asset_id: str, asset_type: AssetType
) -> ScheduleStatus:
    """Returns schedule status for a given backup id and schedule id

    Args:
        context (Context): The test Context
        protection_job_id (str): Protection Job ID
        schedule_id (int): Schedule ID
        asset_id (str): The CSP Asset ID
        asset_type (AssetType): The CSP Asset Type

    Returns:
        ScheduleStatus: Status of Schedule
    """
    jobs = None
    status: ScheduleStatus = None
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        instance = IMS.get_csp_instance_by_id(context, asset_id)
        jobs = instance.protectionJobInfo
    if asset_type == AssetType.CSP_VOLUME:
        volume = IMS.get_csp_volume_by_id(context, asset_id)
        jobs = volume.protectionJobInfo
    if jobs is not None:
        for job in jobs:
            if protection_job_id not in job.resourceUri:
                continue
            for schedule in job.scheduleInfo:
                if schedule_id == schedule.id:
                    status = schedule.status
    return status


def wait_for_schedule_job_status(
    context: Context,
    schedule_id: str,
    protection_job_id: int,
    asset_id: str,
    asset_type: AssetType,
    expected_status: ScheduleStatus,
):
    """Wait for schedule job to complete

    Args:
        context (Context): The test Context
        schedule_id (str): Schedule ID
        protection_job_id (int): Protection Job ID
        asset_id (str): CSP Asset ID
        asset_type (AssetType): CSP Asset Type
        expected_status (ScheduleStatus): Expected Status for Schedule
    """

    def _wait_for_schedule_job_status():
        """Wait for schedule job to have expected status

        Returns:
            ScheduleStatus: Expected status for Job
        """
        status = get_schedule_status(
            context=context,
            protection_job_id=protection_job_id,
            schedule_id=schedule_id,
            asset_id=asset_id,
            asset_type=asset_type,
        )
        return status == expected_status

    # wait for job completion
    wait(_wait_for_schedule_job_status, timeout_seconds=120, sleep_seconds=0.5)


def wait_for_asset_backup_count(
    context: Context,
    asset_id: str,
    asset_type: AssetType,
    expected_count: int,
    timeout_seconds: int = 120,
    sleep_seconds: float = 0.5,
):
    """Wait for backup count for asset

    Args:
        context (Context): The test Context
        asset_id (str): CSP Asset ID
        asset_type (AssetType): CSP Asset Type
        expected_count (int): Expected backup count
        timeout_seconds (int, optional): Time waiting. Defaults to 120.
        sleep_seconds (float, optional): Time sleeping. Defaults to 0.5.
    """

    def _wait_for_backup_count():
        return get_backup_count_from_asset(context=context, asset_id=asset_id, asset_type=asset_type) == expected_count

    # wait for job completion
    wait(_wait_for_backup_count, timeout_seconds=timeout_seconds, sleep_seconds=sleep_seconds)


def send_backup_updates(
    context: Context,
    customer_id: str,
    backup_id: str,
    backup_type: KafkaBackupType,
    asset_id: str,
    asset_type: KafkaInventoryAssetType,
    protection_job_id: str,
    schedule_id: int,
    event_status: BackupKafkaEventStatus = None,
    wait_for_job: bool = True,
):
    """Send backup updates to Kafka.

    Args:
        context (Context): The test Context
        customer_id (str): Customer ID
        backup_id (str): Backup Id
        backup_type (KafkaBackupType): Type of Backup
        asset_id (str): Asset ID
        asset_type (KafkaInventoryAssetType): Asset Type
        protection_job_id (str): Protection Job ID
        schedule_id (int): Schedule ID
        event_status (BackupKafkaEventStatus, optional): Requested event status. Defaults to None.
        wait_for_job (bool, optional): Waits for backup count. Defaults to True.
    """
    expected_count = 0
    assert (
        asset_type == KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE
        or asset_type == KafkaInventoryAssetType.ASSET_TYPE_VOLUME
    )
    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.CSP_DATAPROTECTION_BACKUP_UPDATES.value, host=config["KAFKA"]["host"]
    )
    actual_asset_type = get_csp_type_for_backup_asset_type(asset_type)

    if wait_for_job:
        backup_count = get_backup_count_from_asset(context=context, asset_id=asset_id, asset_type=actual_asset_type)
        expected_count = backup_count + 1
    requested_event = create_backup_event_kafka_object(
        backup_id=backup_id,
        backup_type=backup_type.value,
        asset_id=asset_id,
        asset_type=asset_type.value,
        event_status=event_status.value,
        protection_job_id=protection_job_id,
        schedule_id=schedule_id,
    )
    CommonSteps.send_kafka_message(
        customer_id=customer_id,
        kafka_manager=kafka_manager,
        requested_event=requested_event,
        event_type=AtlantiaKafkaEvents.BACKUP_CREATION_EVENT_TYPE.value,
    )
    if wait_for_job:
        if BackupKafkaEventStatus.SUCCESS == event_status:
            wait_for_asset_backup_count(
                context=context,
                asset_id=asset_id,
                asset_type=actual_asset_type,
                expected_count=expected_count,
            )
        elif BackupKafkaEventStatus.FAILURE == event_status:
            wait_for_schedule_job_status(
                context=context,
                protection_job_id=protection_job_id,
                schedule_id=schedule_id,
                asset_id=asset_id,
                asset_type=actual_asset_type,
                expected_status=ScheduleStatus.FAILURE,
            )


def send_delete_backup_updates(
    context: Context,
    customer_id: str,
    backup_id: str,
    backup_type: KafkaBackupType,
    asset_id: str,
    asset_type: KafkaInventoryAssetType,
    wait_for_job: bool = True,
):
    """Send delete backup notification to Kafka.

    Args:
        context (Context): The test Context
        customer_id (str): Customer ID
        backup_id (str): Backup ID
        backup_type (KafkaBackupType): Type of Backup
        asset_id (str): Asset ID
        asset_type (KafkaInventoryAssetType): Asset Type
        wait_for_job (bool, optional): Wait for backup count. Defaults to True.
    """
    expected_count = 1
    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.CSP_DATAPROTECTION_BACKUP_UPDATES.value, host=config["KAFKA"]["host"]
    )
    actual_asset_type = get_csp_type_for_backup_asset_type(asset_type)
    if wait_for_job:
        backup_count = get_backup_count_from_asset(context=context, asset_id=asset_id, asset_type=actual_asset_type)
        expected_count = backup_count - 1

    requested_event = delete_backup_event_kafka_object(
        backup_id=backup_id,
        backup_type=backup_type.value,
        asset_id=asset_id,
        asset_type=asset_type.value,
    )
    CommonSteps.send_kafka_message(
        customer_id=customer_id,
        kafka_manager=kafka_manager,
        requested_event=requested_event,
        event_type=AtlantiaKafkaEvents.BACKUP_DELETION_EVENT_TYPE.value,
    )
    if wait_for_job:
        wait_for_asset_backup_count(
            context=context,
            asset_id=asset_id,
            asset_type=actual_asset_type,
            expected_count=expected_count,
        )


# Right now, it is being used for functional testing
def create_backup_event_kafka_object(
    backup_id: str,
    backup_type: str,
    asset_id: str,
    asset_type: str,
    protection_job_id: str,
    schedule_id: int,
    event_status: str = None,
    event_info_time: Timestamp = None,
) -> BackupCreationInfo:
    """Create backup event

    Args:
        backup_id (str): Backup ID
        backup_type (str): Backup Type. Valid values are BACKUP_TYPE_BACKUP | BACKUP_TYPE_CLOUDBACKUP | BACKUP_TYPE_TRANSIENT_BACKUP
        asset_id (str): Asset ID
        asset_type (str): Asset Type. Valid values are: ASSET_TYPE_MACHINE_INSTANCE | ASSET_TYPE_VOLUME
        protection_job_id (str): Protection job ID
        schedule_id (int): Schedule ID
        event_status (str, optional): Requested event status. Valid values are: EVENT_STATUS_SUCCESS | EVENT_STATUS_FAILURE
        event_info_time (Timestamp, optional): Requested event time. Defaults to None.

    Returns:
        BackupCreationInfo: Backup Event
    """
    requested_event_backup_type = backup_events_pb2._BACKUPTYPE.values_by_name[backup_type].number
    requested_event_asset_type = backup_events_pb2._ASSETTYPE.values_by_name[asset_type].number

    requested_event = backup_events_pb2.BackupCreationInfo()
    requested_event.backup_info.id = backup_id
    requested_event.backup_info.type = requested_event_backup_type
    requested_event.asset_info.type = requested_event_asset_type
    requested_event.asset_info.id = asset_id
    requested_event.protection_job_info.id = protection_job_id
    requested_event.protection_job_info.schedule_id = schedule_id

    if event_status:
        requested_event_status = backup_events_pb2._EVENTSTATUS.values_by_name[event_status].number
        requested_event.event_info.status = requested_event_status
        if event_info_time is None:
            event_info_time = Timestamp()
            event_info_time.GetCurrentTime()
        requested_event.event_info.time.CopyFrom(event_info_time)

    return requested_event


def delete_backup_event_kafka_object(
    backup_id: str,
    backup_type: str,
    asset_id: str,
    asset_type: str,
) -> BackupDeletionInfo:
    """Delete backup event

    Args:
        backup_id (str): Backup ID
        backup_type (str): Backup Type. Valid values are BACKUP_TYPE_BACKUP | BACKUP_TYPE_CLOUDBACKUP | BACKUP_TYPE_TRANSIENT_BACKUP
        asset_id (str): Asset ID
        asset_type (str): Asset Type. Valid values are: ASSET_TYPE_MACHINE_INSTANCE | ASSET_TYPE_VOLUME

    Returns:
        BackupDeletionInfo: Backup Deletion Event
    """
    requested_event_backup_type = backup_events_pb2._BACKUPTYPE.values_by_name[backup_type].number
    requested_event_asset_type = backup_events_pb2._ASSETTYPE.values_by_name[asset_type].number

    requested_event = backup_events_pb2.BackupDeletionInfo()
    requested_event.backup_info.id = backup_id
    requested_event.backup_info.type = requested_event_backup_type
    requested_event.asset_info.type = requested_event_asset_type
    requested_event.asset_info.id = asset_id

    return requested_event


def verify_on_aws_native_backup(context: Context, aws: AWS, asset_id: str, asset_type: AssetType, backup_count: int):
    """Confirm number of native backups

    Args:
        context (Context): The test Context
        aws (AWS): AWS account
        asset_id (str): Asset ID
        asset_type (AssetType): Asset Type
        backup_count (int): Number of expected backups
    """
    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        instance = IMS.get_csp_instance_by_id(context, asset_id)
        # Check snapshots
        for info in instance.volumeAttachmentInfo:
            verify_aws_snapshots(aws, info.attachedTo.name, backup_count)

        # Check AMI
        amis = aws.ec2.get_all_amis()
        ami_tags = list(map(lambda ami: ami["Tags"], amis["Images"]))
        for tags in ami_tags:
            for tag in tags:
                if tag["Key"] == "Name" and instance.name in tag["Value"]:
                    return True
        assert False, "AMI not found."

    if asset_type == AssetType.CSP_VOLUME:
        volume = IMS.get_csp_volume_by_id(context, asset_id)
        verify_aws_snapshots(aws, volume.cspId, backup_count)


def verify_aws_snapshots(aws: AWS, vol_name: str, backup_count: int):
    """Confirm number of AWS snapshots

    Args:
        aws (AWS): AWS account
        vol_name (str): Volume name
        backup_count (int): Number of expected snapshots
    """
    snapshots = aws.ebs.get_all_snapshots()
    snapshots_filtered = [snapshot["VolumeId"] for snapshot in snapshots["Snapshots"]]

    backup_count_sum = backup_count[CSPBackupType.STAGING_BACKUP] + backup_count[CSPBackupType.NATIVE_BACKUP]
    assert (
        snapshots_filtered.count(vol_name) == backup_count_sum
    ), f"Vol {vol_name} has aws snapshots: {snapshots_filtered.count(vol_name)}, in B&R has: {backup_count_sum}"


def find_and_wait_for_copy2cloud(
    context: Union[Context, AzureContext],
    customer_id: str,
    account_id: str,
    account_name: str,
    region: str = None,
    expected_status: TaskStatus = TaskStatus.success,
    wait_for_task_complete: bool = True,
) -> str:
    """Finds Copy2Cloud task. Will wait for task to complete if specified.
    This function supports AWS and Azure account types.

    Args:
        context (Context | AzureContext): The test Context AWS or Azure
        customer_id (str): Customer ID
        account_id (str): CSP Account ID
        account_name (str): CSP Account Name
        region (str, optional): CSP region. Defaults to None.
        expected_status (TaskStatus, optional): Expected Task Status. Defaults to TaskStatus.success.
        wait_for_task_complete (bool, optional): Waits for task to complete. Defaults to True.

    Raises:
        e: Raised if it takes too long to get task id
        e: Raised if it takes too long for task to complete

    Returns:
        str: Copy2Cloud task id
    """
    if not region:
        region = context.aws_one_region_name

    # NOTE: AWS task name is "CVSA Nightly Trigger Cycle for customer: 2dbda8709b1d11ecb397b26e5ea5b1a5, region:
    # us-west-2, accountID: 3b585f89-cd4c-46d3-a1c7-210ac0e1eea1, accountName: kg_api-autom"
    aws_copy2cloud_task_name = (
        f"{COPY2CLOUD_DISPLAY_NAME} for customer: {customer_id}, region: {region}, "
        f"accountID: {account_id}, accountName: {account_name}"
    )

    # NOTE: Azure task name is "CVSA Nightly Trigger Cycle (Azure) for customer: d1626060ba8f11ec86fe8e5d5bdc4cce
    # , region: eastus, accountID: 1e027222-1e73-539e-89a8-e034870d0d13, accountName: cds-prashanth"

    azure_copy2cloud_task_name = (
        f"{COPY2CLOUD_DISPLAY_NAME} (Azure) for customer: {customer_id}, region: {region}, "
        f"accountID: {account_id}, accountName: {account_name}"
    )
    csp_type = CAMS.get_csp_account_by_csp_id(context=context, csp_account_id=account_id).cspType.value
    copy2cloud_task_name = aws_copy2cloud_task_name if csp_type == CspType.AWS.value else azure_copy2cloud_task_name

    copy2cloud_task_id: str = None
    logger.info("Looking for copy2cloud task")
    # wait a bit for task to appear
    try:
        wait(
            lambda: len(
                tasks.get_tasks_by_name_and_customer_account(
                    user=context.user, task_name=copy2cloud_task_name, customer_id=customer_id
                )
            ),
            timeout_seconds=5 * 60,
            sleep_seconds=10,
        )
        # get the task id
        copy2cloud_task_id = tasks.get_tasks_by_name_and_customer_account(
            user=context.user, task_name=copy2cloud_task_name, customer_id=customer_id
        )[0].id
        logger.info(f"copy2cloud task ready: {copy2cloud_task_id}")
    except TimeoutExpired as e:
        logger.info(f"TimeoutExpired waiting for 'copy2cloud' task {e}")
        raise e

    if wait_for_task_complete:
        # wait for the task to complete
        try:
            copy2cloud_task_state: str = tasks.wait_for_task(
                task_id=copy2cloud_task_id, user=context.user, timeout=TimeoutManager.create_cloud_backup_timeout
            )
            assert (
                copy2cloud_task_state.upper() == expected_status.value
            ), f"Copy2Cloud Task State {copy2cloud_task_state.upper()} does NOT equal expected Copy2Cloud Task State {expected_status.value}"
            logger.info(f"copy2cloud task state: {copy2cloud_task_state}")

        except TimeoutError as e:
            logger.info(f"copy2cloud task timeout. task_id: {copy2cloud_task_id}")
            raise e

    return copy2cloud_task_id


def run_backup_for_asset_and_wait_for_trigger_task(
    context: Context,
    asset_resource_uri: str,
    expected_status: TaskStatus = TaskStatus.success,
    backup_type: BackupType = BackupType.BACKUP,
    wait_for_task_complete: bool = True,
    wait_for_task_ready_for_copy2cloud: bool = False,
) -> str:
    """Run backup for asset_id and wait for spawned subtask "Trigger Native/Cloud Backup".

    Args:
        context : Context
            Test context
        asset_resource_uri :str
            CSP Machine Instance, CSP Volume or CSP Protection Group resource_uri
        expected_status : TaskStatus, optional
            The expected Task Status. Defaults to TaskStatus.success.
        backup_type : BackupType, optional
            BackupType to execute and wait for completion. Defaults to BackupType.BACKUP.
        wait_for_task_complete : bool, optional
            If False, the function will not wait for the "trigger" task to complete. Defaults to True.

    Returns:
        str: Task ID of the "Trigger" Task
    """
    asset_id = asset_resource_uri.split("/")[-1]
    logger.info(f"Running backup job for asset {asset_id}")
    logger.info(f"asset_id: {asset_id}")

    # default
    task_title = TRIGGER_BACKUP_DISPLAY_NAME
    if backup_type == BackupType.CLOUD_BACKUP:
        task_title = TRIGGER_CLOUD_BACKUP_DISPLAY_NAME
    elif backup_type != BackupType.BACKUP:
        assert False, "Invalid BackupType provided"

    # NOTE: "wait_for_task" due to DCS-3511 (resolved), need to look for spawned "Trigger Native/Cloud Backup" task
    run_backup_on_asset(context=context, asset_id=asset_id, backup_types=[backup_type], wait_for_task=True)  # False
    logger.info("Initiate task complete")

    # run_backup() task == "Initiate protection schedules run for csp volume [cloud asset]" (DCS-3511)
    #   spawns task == "Trigger scheduled protection job" (always succeeds; it spawns next task)
    #   spawns task == "Trigger Native Backup/Trigger Cloud Backup" (this task has subtask "Native Backup workflow")
    #     subtask has the LogMessages containing the "log_entry" provided

    trigger_task_id: str = None
    logger.info("Looking for Trigger task")
    # wait a bit for asset_resource_uri "Trigger" task to appear
    try:
        wait(
            lambda: tasks.get_tasks_by_name_and_resource(
                user=context.user, task_name=task_title, resource_uri=asset_resource_uri
            ).total,
            timeout_seconds=5 * 60,
            sleep_seconds=10,
        )
        # get the task id
        trigger_task_id = (
            tasks.get_tasks_by_name_and_resource(
                user=context.user, task_name=task_title, resource_uri=asset_resource_uri
            )
            .items[0]
            .id
        )
        logger.info(f"Trigger task ready: {trigger_task_id}")
    except TimeoutExpired as e:
        logger.info("TimeoutExpired waiting for 'Trigger' task")
        raise e

    if wait_for_task_ready_for_copy2cloud:
        logger.info("wait for the trigger task to have 50 percentages completed")
        try:
            # sleep time required as EKS task percentage to complete >50% for seconds before it reaches 50%
            time.sleep(180)
            tasks.wait_for_task_percent_complete(
                task_id=trigger_task_id,
                user=context.user,
                percent_complete=50,
                timeout=TimeoutManager.standard_task_timeout,
            )
            logger.info("trigger task progressPercent = 50")
        except TimeoutError:
            logger.info(f"task timeout for 50% percentages. backup_type: {backup_type} task_id: {trigger_task_id}")
            trigger_task = tasks.get_task_object(user=context.user, task_id=trigger_task_id)
            logger.info(f"Trigger Task contains {trigger_task.subtree_task_count} subtasks")

    if wait_for_task_complete:
        logger.info("wait for the trigger task to complete")
        timeout_value = (
            TimeoutManager.create_backup_timeout
            if backup_type == BackupType.BACKUP
            else TimeoutManager.create_cloud_backup_timeout
        )

        try:
            trigger_task_state: str = tasks.wait_for_task(
                task_id=trigger_task_id, user=context.user, timeout=timeout_value
            )
            assert (
                trigger_task_state.upper() == expected_status.value
            ), f"Trigger Task State {trigger_task_state.upper()} does NOT equal expected Trigger Task State {expected_status.value}"
            logger.info(f"trigger task state: {trigger_task_state}")

        except TimeoutError:
            # CLOUD can stay at 50% for several hours (transient to cloud thing?)
            # NOTE: DCS-3811 can have "Native Backups" remain in a running state for up to an hour
            # due to the numerous "Image Delete Child Workflow" subtasks.
            # We'll output the number of subtasks the "trigger_task_id" has for debugging purposes
            logger.info(f"trigger task timeout. backup_type: {backup_type} task_id: {trigger_task_id}")
            trigger_task = tasks.get_task_object(user=context.user, task_id=trigger_task_id)
            logger.info(f"Trigger Task contains {trigger_task.subtree_task_count} subtasks")

    return trigger_task_id


def validate_asset_backup_count(
    context: Context,
    asset_id: str,
    asset_type: AssetType,
    backup_type: CSPBackupType,
    prev_backup_count: dict[CSPBackupType, int],
    num_additional_backups: int = 1,
) -> dict[CSPBackupType, int]:
    """Confirm number of backups is corrent after backups are taken

    Args:
        context (Context): The test Context
        asset_id (str): Asset ID
        asset_type (AssetType): Asset Type
        backup_type (CSPBackupType): Type of Backup
        prev_backup_count (dict[CSPBackupType, int]): Number of backups for each type before recent backup(s) were taken
        num_additional_backups (int, optional): Backups taken since previous backup count. Defaults to 1.

    Returns:
        (dict[CSPBackupType, int]): Current backup count
    """
    current_backup_count = get_asset_backup_count(context=context, asset_id=asset_id, asset_type=asset_type)

    # current 'backup_type' count
    num_current_type_backup = current_backup_count[backup_type]
    # expected backup count
    num_expected = prev_backup_count[backup_type] + num_additional_backups

    assert (
        num_current_type_backup == num_expected
    ), f"Expected to find {num_expected} backups of type {backup_type}, but instead found: {num_current_type_backup}"

    # return updated backup count
    return current_backup_count


def modify_backup_expire_time(
    context: Context, csp_backup_id: str, csp_asset_id: str, csp_asset_type: str, new_expire_time: str
):
    """Modify & validate new backup expire time

    Args:
        context (Context): Context
        csp_backup_id (str): backup ID associated with CSPVolume or CSPInstance
        csp_asset_id (str): ID of CSPVolume or CSPInstance associated with csp_asset_type parameter
        csp_asset_type (str): 'EC2' or 'EBS' associated with csp_asset_id parameter
        new_expire_time (str): need to follow backup.expires_at time format
    """

    # Change Backup Expire time using PATCH API
    backup_patch = PatchEC2EBSBackupsModel(expires_at=new_expire_time)

    if csp_asset_type == "EC2":
        task_id = update_csp_machine_instance_backup(
            context=context,
            machine_instance_id=csp_asset_id,
            backup_id=csp_backup_id,
            patch_backup_payload=backup_patch,
        )
    elif csp_asset_type == "EBS":
        task_id = update_csp_volume_backup(
            context=context,
            volume_id=csp_asset_id,
            backup_id=csp_backup_id,
            patch_backup_payload=backup_patch,
        )

    tasks.wait_for_task(task_id=task_id, user=context.user, timeout=TimeoutManager.standard_task_timeout)

    if csp_asset_type == "EC2":
        new_backup = get_csp_machine_instance_backup_by_id(context=context, backup_id=csp_backup_id)
    elif csp_asset_type == "EBS":
        new_backup = get_csp_volume_backup_by_id(context=context, volume_id=csp_asset_id, backup_id=csp_backup_id)

    assert (
        new_backup.expires_at == new_expire_time
    ), f"New Backup Expire Time {new_backup.expires_at} does NOT equal expected new expire time {new_expire_time}"


def wait_for_cloud_usage_change(context: Context, current_value: float, region: str, full_sync: bool = False):
    """Waits till cloud usage changes

    Args:
        context (Context): The test Context
        current_value (float): Current value for cloud usage
        region (str): AWS region
        full_sync (bool, optional): Should be used especially before deleting backups to ensure that dashboard is in sync with ongoing ops. Defaults to False.

    Raises:
        e: Raised when cloud usage doesn't change
    """

    # NOTE: 31 minute timeout - given the 30 minute update window
    def _wait_for_usage_change():
        new_value = DashboardSteps.get_csp_cloud_usage_in_bytes(context, region=region)
        if current_value != new_value:
            if full_sync:
                _wait_full_sync(new_value)

            return True

    def _wait_full_sync(new_value):
        try:
            logger.info(f"Full sync wait: {new_value}")
            wait(
                lambda: DashboardSteps.get_csp_cloud_usage_in_bytes(context, region=region) != new_value,
                timeout_seconds=60 * 6,
                sleep_seconds=60,
            )
            new_value = DashboardSteps.get_csp_cloud_usage_in_bytes(context, region=region)
            _wait_full_sync(new_value)
        except TimeoutExpired:
            logger.info(f"Full sync wait success: {new_value}")

    try:
        wait(_wait_for_usage_change, timeout_seconds=60 * 62, sleep_seconds=60)
    except TimeoutExpired as e:
        logger.info(f"Timeout waiting for cloud usage to change from current_value: {current_value}")
        raise e


def perform_copy2cloud(context: Context, csp_account: CSPAccountModel, cloud_backup_trigger_task_id: str = None):
    """Runs copy2cloud and triggers cloud backup

    Args:
        context (Context): The test Context
        csp_account (CSPAccountModel): CSP Account
        cloud_backup_trigger_task_id (str, optional): Trigger Task ID. Defaults to None.
    """
    # Run /copy2cloud to start the CloudBackup
    get_ami_and_snapshot_status_list(context.aws_one)
    logger.info(f"Calling Copy2Cloud for {context.aws_one_account_name} in Region {context.aws_one_region_name}")
    run_copy2cloud_endpoint(
        context=context, account_name=context.aws_one_account_name, region=context.aws_one_region_name
    )
    logger.info("copy2cloud endpoint called")

    logger.info(
        f"Find & wait for copy2cloud task to complete.customerId:{csp_account.customerId}accountID:{csp_account.id}"
    )
    # look for and wait for the "TaskForNightlyCVSACycle <region>" task to complete
    copy2cloud_task_id = find_and_wait_for_copy2cloud(
        context=context,
        customer_id=csp_account.customerId,
        account_id=csp_account.id,
        account_name=context.aws_one_account_name,
        region=context.aws_one_region_name,
    )
    logger.info(f"copy2cloud task: {copy2cloud_task_id} is complete")

    if cloud_backup_trigger_task_id is not None:
        logger.info(f"Waiting for CloudBackup Trigger task to complete: {cloud_backup_trigger_task_id}")
        # Now we can wait for the CloudBackup Trigger task to run to completion
        tasks.wait_for_task(
            task_id=cloud_backup_trigger_task_id, user=context.user, timeout=TimeoutManager.create_cloud_backup_timeout
        )
        logger.info(f"CloudBackup Trigger Task complete: {cloud_backup_trigger_task_id}")

        error_msg = tasks.get_task_error(task_id=cloud_backup_trigger_task_id, user=context.user)
        logger.info(f"CloudBackup Task contains error_msg: {error_msg}")
        assert error_msg == "", f"Error message {error_msg} is NOT empty"


def add_retention_to_datetime(start_date: datetime, retention: ObjectUnitValue) -> datetime:
    """Add a Policy retention value to the provided 'datetime' object

    Args:
        start_date (datetime): The datetime to which the retention will be added
        retention (ObjectUnitValue): Policy retention ObjectUnitValue: HOURS, DAYS, WEEKS, MONTHS, YEARS

    Returns:
        datetime: a new datetime object with the retention applied
    """
    logger.info(f"{start_date=}  {retention=}")

    # set to "start_date" by default, find a valid "ObjectUnitType.unit" value.
    new_date = start_date

    if retention.unit == ObjectUnitType.HOURS.value:
        new_date = start_date + relativedelta(hours=retention.value)
    elif retention.unit == ObjectUnitType.DAYS.value:
        new_date = start_date + relativedelta(days=retention.value)
    elif retention.unit == ObjectUnitType.WEEKS.value:
        new_date = start_date + relativedelta(weeks=retention.value)
    elif retention.unit == ObjectUnitType.MONTHS.value:
        new_date = start_date + relativedelta(months=retention.value)
    elif retention.unit == ObjectUnitType.YEARS.value:
        new_date = start_date + relativedelta(years=retention.value)

    logger.info(f"{new_date=}")

    return new_date


def get_last_machine_instance_backup(context: Context, csp_instance_id: str, backup_type: CSPBackupType):
    """Get the last backup taken of the type requested from a CSP Machine Instance

    Args:
        context (Context): The test context
        csp_instance_id (str): CSP Machine Instance ID
        backup_type (CSPBackupType): NATIVE_BACKUP or HPE_CLOUD_BACKUP

    Returns:
        CSPBackup | None: The last CSPBackup if any exist, else None
    """
    csp_backups: CSPBackupListModel = get_csp_machine_instance_backups(
        context=context,
        machine_instance_id=csp_instance_id,
        backup_type=backup_type,
        sort="pointInTime asc",
    )
    return csp_backups.items[-1] if csp_backups.total else None


def get_expires_at_difference_in_seconds(
    expected_expires_at: datetime,
    csp_backup_expires_at: str,
) -> float:
    """Subtract 'expected_expires_at' from 'csp_backup_expires_at' and return difference in seconds

    Args:
        expected_expires_at (datetime): The expected expires at
        csp_backup_expires_at (str): The 'expires_at' value from a CSPBackup

    Returns:
        float: The difference in expires_at times
    """
    backup_expires_at = dateutil.parser.parse(csp_backup_expires_at)
    logger.info(f"backup_expires_at = {backup_expires_at}")

    backup_diff = backup_expires_at - expected_expires_at
    logger.info(f"backup_diff = {backup_diff}")

    return backup_diff.total_seconds()


def validate_machine_instance_backups_expires_at(
    context: Context,
    csp_instance_id: str,
    expected_backup_expires_at: datetime = None,
    expected_cloud_backup_expires_at: datetime = None,
    threshold: int = 3600,
):
    """
    Validate a CSP Machine Instance has CSPBackups with expected 'Expires At' times that are within the tolerance
    'threshold'.

    Args:
        context : Context
            The test context
        csp_instance_id : str
            CSP Machine Instance ID
        expected_backup_expires_at : datetime, optional
            If provided, will validate NATIVE_BACKUP. Defaults to None.
        expected_cloud_backup_expires_at : datetime, optional
            If provided, will validate HPE_CLOUD_BACKUP. Defaults to None.
        threshold : int, optional
            Threshold in seconds, to allow variation in validation window. Defaults to 3600 (1 hour).
    """
    if expected_backup_expires_at:
        # grab the last backup taken
        csp_backup = get_last_machine_instance_backup(
            context=context, csp_instance_id=csp_instance_id, backup_type=CSPBackupType.NATIVE_BACKUP
        )
        backup_diff = get_expires_at_difference_in_seconds(
            expected_expires_at=expected_backup_expires_at, csp_backup_expires_at=csp_backup.expires_at
        )
        assert (
            backup_diff <= threshold and backup_diff >= 0
        ), f"The backup 'expires_at' time is not in expected threshold ({threshold} seconds)"

    if expected_cloud_backup_expires_at:
        # grab the last cloud backup taken
        csp_cloud_backup = get_last_machine_instance_backup(
            context=context, csp_instance_id=csp_instance_id, backup_type=CSPBackupType.HPE_CLOUD_BACKUP
        )
        cloud_backup_diff = get_expires_at_difference_in_seconds(
            expected_expires_at=expected_cloud_backup_expires_at, csp_backup_expires_at=csp_cloud_backup.expires_at
        )
        assert (
            cloud_backup_diff <= threshold and cloud_backup_diff >= 0
        ), f"The cloud_backup 'expires_at' time is not in expected threshold ({threshold} seconds)"


def delete_csp_backups_in_range(
    context: Context,
    csp_asset: Union[CSPMachineInstanceModel, CSPVolumeModel],
    backup_type: CSPBackupType,
    remove_after_date: datetime = None,
    leave_backups: int = 0,
    leave_backups_ids: list = [],
) -> list[str]:
    """
    Delete backups from ec2 or ebs. Specify how many leave or/and after which date they should be deleted.

    Args:
        context:  context class from Medusa framework
        csp_asset: can be ec2 or ebs
        backup_type: CSPBackupType.NATIVE_BACKUP or CSPBackupType.HPE_CLOUD_BACKUP
        remove_after: format iso8601 -> '2023-02-15T10:49:01Z', it is date after <leave_backup> will be applied.
            if None then it's all backups. if '2023-02-15T10:49:01Z' and leave_backup=1 \
            then 1 backup will be left before date <remove_after> and all backups after date. Older backups will be deleted.
        leave_backup: if 0 all backups will de deleted. if 1 or more then this many backups will remain.
        leave_backups_ids: if [] all backups will de deleted. All backups in list will be not deleted.

    Returns:
        list[str]: Returns list of cloud tasks. If none, then it returns nothing.
    """

    cloud_tasks: list[str] = []
    native_backup = True if backup_type == CSPBackupType.NATIVE_BACKUP else False
    asset_type = AssetType(csp_asset.type)

    if asset_type == AssetType.CSP_MACHINE_INSTANCE:
        csp_backups: CSPBackupListModel = get_csp_machine_instance_backups(
            context=context,
            machine_instance_id=csp_asset.id,
            after_date=remove_after_date,
            backup_type=backup_type,
        )
    elif asset_type == AssetType.CSP_VOLUME:
        csp_backups: CSPBackupListModel = get_csp_volume_backups(
            context=context,
            volume_id=csp_asset.id,
            after_date=remove_after_date,
            backup_type=backup_type,
        )
    logger.info(f"Asset {csp_asset} , {backup_type} backups: {csp_backups}")

    if csp_backups.total == 0:
        return

    for i in range(leave_backups, csp_backups.total):
        if csp_backups.items[i].id in leave_backups_ids:
            logger.info(f"Backup {csp_backups.items[i].id} will be not deleted.")
            continue
        logger.info(
            f"Deleting {csp_backups.items[i].backup_type} \
            backup: {csp_backups.items[i].id} for {asset_type} {csp_asset.id}"
        )
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            task_id = delete_csp_machine_instance_backup_by_id(
                context=context,
                machine_instance_id=csp_asset.id,
                backup_id=csp_backups.items[i].id,
            )
        elif asset_type == AssetType.CSP_VOLUME:
            task_id = delete_csp_volume_backup_by_id(
                context=context,
                volume_id=csp_asset.id,
                backup_id=csp_backups.items[i].id,
            )
        assert task_id
        logger.info(f"Waiting for Delete backup for {asset_type}, {csp_backups} task: {task_id}")

        task_id = delete_backups_check_task(
            context=context,
            asset_id=csp_asset.id,
            task_id=task_id,
            backup=csp_backups.items[i],
            wait_for_error=native_backup,
        )
        logger.info(
            f"Deleted {csp_backups.items[i].backup_type} \
            backup: {csp_backups.items[i].id} for {asset_type}, id: {csp_asset.id}"
        )

        # Add cloud tasks to a list to check at the end to save time
        if not native_backup:
            cloud_tasks.append(task_id)
            task_id = None
            logger.info(
                f"Initiated cloud backup delete for {csp_backups.items[i].backup_type} \
                backup: {csp_backups.items[i].id} for {asset_type}, id: {csp_asset.id}"
            )
    return cloud_tasks


def get_csp_machine_instance_backups(
    context: Context,
    machine_instance_id: str,
    backup_type: CSPBackupType = None,
    after_date: datetime = None,
    sort: str = "pointInTime desc",
) -> CSPBackupListModel:
    """
    Get CSP backups of a specific CSP machine instance ID

    Args:
        context:  context class from Medusa framework
        machine_instance_id (str): CSP Machine Instance ID
        backup_type (CSPBackupType): backup type from enum CSPBackupType
        after_date (datetime, optional): filed in filter to find backups after date. Defaults to None.
        sort (str, optional): sort query

    Returns:
        CSPBackupListModel: List of CSP backups
    """
    logger.info(f"Getting backups for CSP Machine Instance: {machine_instance_id}")
    backup_filter = f"backupType eq {backup_type.value}" if backup_type else None
    date_filter = f"startedAt lt '{after_date}'" if after_date else None

    filter_query = " and ".join(filter(None, [backup_filter, date_filter]))

    csp_backups: CSPBackupListModel = context.data_protection_manager.get_csp_machine_instance_backups(
        machine_instance_id=machine_instance_id,
        filter=filter_query,
        sort=sort,
    )
    logger.info(f"Backups: {csp_backups}")
    return csp_backups


def get_csp_volume_backups(
    context: Context,
    volume_id: str,
    backup_type: CSPBackupType = None,
    after_date: datetime = None,
    sort: str = "pointInTime desc",
) -> CSPBackupListModel:
    """
    Get CSP backups of a specific CSP volume ID

    Args:
        context:  context class from Medusa framework
        volume_id (str): CSP Volume ID
        backup_type (CSPBackupType): _description_
        after_date (datetime, optional): filed in filter to find backups after date. Defaults to None.
        sort (str, optional): sort query

    Returns:
        CSPBackupListModel: List of CSP backups
    """
    logger.info(f"Getting backups for CSP Volume: {volume_id}")
    backup_filter = f"backupType eq {backup_type.value}" if backup_type else None
    date_filter = f"startedAt lt '{after_date}'" if after_date else None

    filter_query = " and ".join(filter(None, [backup_filter, date_filter]))

    csp_backups: CSPBackupListModel = context.data_protection_manager.get_csp_volume_backups(
        volume_id=volume_id,
        filter=filter_query,
        sort=sort,
    )
    logger.info(f"Backups: {csp_backups}")
    return csp_backups


def delete_csp_machine_instance_backup_by_id(
    context: Context,
    machine_instance_id: str,
    backup_id: str,
) -> str:
    """
    Delete a CSP backup of a specific CSP machine instance ID

    Args:
        context:  context class from Medusa framework
        machine_instance_id (str): CSP Machine Instance ID
        backup_id (str): Backup ID

    Returns:
        str: Task ID
    """
    logger.info(f"Deleting backup {backup_id} for CSP Machine Instance: {machine_instance_id}")
    task_id = context.data_protection_manager.delete_csp_machine_instance_backup_by_id(
        machine_instance_id=machine_instance_id,
        backup_id=backup_id,
    )
    logger.info(f"Waiting for Delete backup for CSP Machine Instance: {machine_instance_id} task: {task_id}")
    return task_id


def delete_csp_volume_backup_by_id(
    context: Context,
    volume_id: str,
    backup_id: str,
) -> str:
    """
    Delete a CSP backup of a specific CSP volume ID

    Args:
        context:  context class from Medusa framework
        volume_id (str): CSP Volume ID
        backup_id (str): Backup ID

    Returns:
        str: Task ID
    """
    logger.info(f"Deleting backup {backup_id} for CSP Volume: {volume_id}")
    task_id = context.data_protection_manager.delete_csp_volume_backup_by_id(
        volume_id=volume_id,
        backup_id=backup_id,
    )
    logger.info(f"Waiting for Delete backup for CSP Volume: {volume_id} task: {task_id}")
    return task_id


def update_csp_machine_instance_backup(
    context: Context,
    machine_instance_id: str,
    backup_id: str,
    patch_backup_payload: PatchEC2EBSBackupsModel,
) -> str:
    """
    Update a CSP backup of a specific CSP machine instance ID

    Args:
        context:  context class from Medusa framework
        machine_instance_id (str): CSP Machine Instance ID
        backup_id (str): Backup ID
        patch_backup_payload (PatchEC2EBSBackupsModel): Backup patch payload

    Returns:
        str: Task ID
    """
    logger.info(f"Updating backup {backup_id} for CSP Machine Instance: {machine_instance_id}")
    task_id = context.data_protection_manager.update_csp_machine_instance_backup(
        machine_instance_id=machine_instance_id,
        backup_id=backup_id,
        patch_backup_payload=patch_backup_payload,
    )
    logger.info(f"Waiting for Update backup for CSP Machine Instance: {machine_instance_id} task: {task_id}")
    return task_id


def update_csp_volume_backup(
    context: Context,
    volume_id: str,
    backup_id: str,
    patch_backup_payload: PatchEC2EBSBackupsModel,
) -> str:
    """
    Update a CSP backup of a specific CSP Volume ID

    Args:
        context:  context class from Medusa framework
        volume_id (str): CSP Volume ID
        backup_id (str): Backup ID
        patch_backup_payload (PatchEC2EBSBackups): Backup patch payload

    Returns:
        str: Task ID
    """
    logger.info(f"Updating backup {backup_id} for CSP Volume: {volume_id}")
    task_id = context.data_protection_manager.update_csp_volume_backup(
        volume_id=volume_id,
        backup_id=backup_id,
        patch_backup_payload=patch_backup_payload,
    )
    logger.info(f"Waiting for Update backup {backup_id} of CSP Volume: {volume_id} task: {task_id}")
    return task_id


def get_csp_machine_instance_backup_by_id(context: Context, backup_id: str) -> CSPBackupModel:
    """
    Get CSP Machine Instance Backup by ID

    Args:
        context (Context): The test context
        backup_id (str): The ID of the CSP Machine Instance Backup

    Returns:
        CSPBackupModel: The CSP Machine Instance Backup
    """
    logger.info(f"Fetching backup {backup_id} ")
    csp_machine_instance_backup: CSPBackupModel = context.data_protection_manager.get_csp_machine_instance_backup_by_id(
        backup_id
    )
    logger.info(f"Backup for CSP Machine Instance is {csp_machine_instance_backup}")

    return csp_machine_instance_backup


def get_csp_volume_backup_by_id(context: Context, volume_id: str, backup_id: str) -> CSPBackupModel:
    """
    Get CSP Volume Backup by ID

    Args:
        context (Context): The test context
        backup_id (str): The ID of the CSP Volume Backup

    Returns:
        CSPBackupModel: The CSP Volume Backup
    """
    logger.info(f"Fetching backup {backup_id} for volume: {volume_id}")
    csp_volume_backup: CSPBackupModel = context.data_protection_manager.get_csp_volume_backup_by_id(
        volume_id, backup_id
    )
    logger.info(f"Backup for CSP Volume is {csp_volume_backup}")

    return csp_volume_backup


def authorize_backup_deletion_request(
    context: Context,
    backup: CSPBackupModel,
    approve: bool = True,
) -> DualAuthOperation:
    """Approves / Rejects a backup deletion request
    NOTE: DualAuth is not available for RDS yet

    Args:
        context (Context): Context object.
        Make sure to initialize a context object with a user other than who initiated the deletion operation
        backup (CSPBackupModel): Backup object which needs to be deleted
        approve (bool, optional): Approve / Deny the backup deletion operation. Defaults to True.

    Returns:
        DualAuthOperation: Authorized backup deletion request
    """
    # Example: Delete backup: 7e848f4b-bbbc-4274-b580-557095009f75
    pending_request_name: str = f"Delete backup: {backup.id}"
    logger.info(
        f"Getting backup deletion request by name: {pending_request_name} and resource_uri {backup.resource_uri}"
    )

    # NOTE: The 'operationResource.resourceUri' currently has the wrong value:
    # /backup-recovery/v1beta1/backup-recovery/csp-volume-backups/c6a48d86-c62b-411c-9615-432b3a99e5b3
    # an extra '/backup-recovery/'
    resource_uri_suffix = backup.resource_uri.split(f"{AssetTypeURIPrefix.BACKUP_RECOVERY_V1_BETA1.value}/")[-1]
    resource_uri = f"{AssetTypeURIPrefix.BACKUP_RECOVERY_V1_BETA1.value}/{AssetTypeURIPrefix.BACKUP_RECOVERY.value}/{resource_uri_suffix}"
    authorized_request = get_pending_request_by_name_and_resource_uri(
        context=context,
        pending_request_name=pending_request_name,
        resource_uri=resource_uri,
    )

    if not authorized_request:
        # Finding using the correct resourceUri
        authorized_request = get_pending_request_by_name_and_resource_uri(
            context=context,
            pending_request_name=pending_request_name,
            resource_uri=backup.resource_uri,
        )

    action = "Approving" if approve else "Denying"
    logger.info(f"{action} backup deletion request for {backup.id}")
    authorized_request = authorize_dual_auth_request(context=context, id=authorized_request.id, approve=approve)
    return authorized_request
