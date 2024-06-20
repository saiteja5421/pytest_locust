"""
This file contains functions for the backup and recovery activities on RDS instance.

Below are the following Region categories of this file:
-   Run RDS Backups
-   Delete RDS Backups
-   RDS Backup Info: State, Status, Count, Expiration, Protections

"""

import logging
from time import sleep
import requests
from typing import Union

from waiting import wait, TimeoutExpired
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_model import (
    CSPRDSInstanceBackupListModel,
    CSPRDSInstanceBackupModel,
)
from utils.timeout_manager import TimeoutManager

from lib.common.enums.asset_type_uri_prefix import AssetTypeURIPrefix
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.backup_type import BackupType
from lib.common.enums.backup_state import BackupState
from lib.common.enums.status import Status
from lib.common.enums.task_status import TaskStatus
from lib.dscc.backup_recovery.protection_policies.rest.v1beta1.models.protection_jobs import (
    Protection,
    ProtectionJob,
    ProtectionJobList,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    GLCPErrorResponse,
)
from tests.e2e.aws_protection.context import Context
from tests.steps.tasks import tasks
import tests.steps.aws_protection.rds.csp_rds_inventory_manager_steps as CSPRDSInvMgrSteps


logger = logging.getLogger()

TRIGGER_BACKUP_DISPLAY_NAME: str = "Initiated RDS Instance backup[{}]"

# region RDS Backups


def get_rds_instance_backups(
    context: Context,
    csp_rds_id: str,
    limit: int = 20,
    offset: int = 0,
    filter: str = "",
) -> CSPRDSInstanceBackupListModel:
    """Returns all the backups for the provided csp_rds_id

    Args:
        context (Context): The test Context
        csp_rds_id (str): DB ID
        limit (int, optional): The maximum number of items to include in the response. Defaults to 20.
        offset (int, optional): The number of items to omit from the beginning of the result set. Defaults to 0.
        filter (str, optional): An expression by which to filter the results. Defaults to "".
        These fields can be used for filtering:
            accountInfo/id
            assetInfo/id
            backupType
            state
            status

    Returns:
        CSPRDSInstanceBackupListModel: List of CSPRDSInstanceBackupModel
    """
    rds_instance_backups: CSPRDSInstanceBackupListModel = (
        context.rds_data_protection_manager.get_csp_rds_instance_backups(
            csp_rds_id=csp_rds_id, limit=limit, offset=offset, filter=filter
        )
    )
    return rds_instance_backups


def get_rds_instance_backup_by_id(context: Context, backup_id: str) -> CSPRDSInstanceBackupModel:
    """Returns details of a specified cloud service provider (CSP) RDS machine instance backup

    Args:
        context (Context): The test Context
        backup_id (str): Unique identifier of a CSP RDS machine instance backup

    Returns:
        CSPRDSInstanceBackupModel: Details of a CSP RDS machine instance backup
    """
    rds_instance_backup: CSPRDSInstanceBackupModel = (
        context.rds_data_protection_manager.get_csp_rds_instance_backup_by_id(backup_id=backup_id)
    )
    return rds_instance_backup


def patch_rds_instance_backup_by_id(context: Context, backup_id: str, new_expires_at: str) -> CSPRDSInstanceBackupModel:
    """Update CSP RDS machine instance backup

    Args:
        context (Context): The test Context
        backup_id (str): Unique identifier of a CSP RDS machine instance backup
        new_expires_at (str): New retention period datetime in str.
        The retention period needs to be specified as an absolute value of UTC.

    Returns:
        CSPRDSInstanceBackupModel: Updated backup
    """
    rds_instance_backup: CSPRDSInstanceBackupModel = (
        context.rds_data_protection_manager.patch_csp_rds_instance_backup_by_id(
            backup_id=backup_id, new_expires_at=new_expires_at
        )
    )
    return rds_instance_backup


# endregion

# region Run RDS Backups


def run_rds_backup(
    context: Context, csp_rds_instance_id: str, backup_type: BackupType, wait_for_backup: bool = True
) -> str:
    """Function runs the Native Backup or Cloud Snapshot protection job associated with the given rds instance id.
    return immediately after running the schedule or wait for task based on the set flag.

    Args:
        context (Context): The test Context.
        csp_rds_instance_id (str): csp rds instance id.
        backup_type (BackupType): The type of backup protection to run.
        wait_for_backup (bool, optional): If True, this function will wait for the Cloud Snapshot Task to complete. Defaults to True.

    Returns:
        str: The Cloud Snapshot Task ID if the Task was started, None otherwise
    """
    task_id = None
    trigger_task_id: str = None

    # Get protection job for RDS Instance
    protection_job_list: ProtectionJobList = context.policy_manager.get_protection_job_by_asset_id(
        asset_id=csp_rds_instance_id
    )
    if protection_job_list.total == 0:
        logger.warning(f"No Protection Policy assigned to RDS Instance: {csp_rds_instance_id}")
        return task_id
    protection_job: ProtectionJob = protection_job_list.items[0]

    # -> if no "backup_type" protection, nothing to do
    protections = get_protections_from_job(protection_job=protection_job, backup_types=[backup_type])
    if not protections:
        logger.warning(f"No {backup_type.value} protection in ProtectionJob: {protection_job.id}")
        return task_id

    # run the backup_type Protection Schedule from the ProtectionJob
    task_id = context.policy_manager.run_protection_job(
        protection_job_id=protection_job.id, protection_schedule_ids=[protections[0].schedules[0].schedule_id]
    )

    logger.info("Looking for Trigger task")
    # wait a bit for asset_resource_uri "Trigger" task to appear
    try:
        wait(
            lambda: tasks.get_tasks_by_name_and_resource(
                user=context.user,
                task_name=TRIGGER_BACKUP_DISPLAY_NAME.format(csp_rds_instance_id),
                resource_uri=f"{AssetTypeURIPrefix.RDS_INSTANCES_RESOURCE_URI_PREFIX.value}{csp_rds_instance_id}",
            ).total,
            timeout_seconds=5 * 60,
            sleep_seconds=10,
        )
        # get the task id
        trigger_task_id = (
            tasks.get_tasks_by_name_and_resource(
                user=context.user,
                task_name=TRIGGER_BACKUP_DISPLAY_NAME.format(csp_rds_instance_id),
                resource_uri=f"{AssetTypeURIPrefix.RDS_INSTANCES_RESOURCE_URI_PREFIX.value}{csp_rds_instance_id}",
            )
            .items[0]
            .id
        )
        logger.info(f"Trigger task ready: {trigger_task_id}")
    except TimeoutExpired as e:
        logger.info("TimeoutExpired waiting for 'Trigger' task")
        raise e
    # wait for backup to finish, if requested
    if wait_for_backup:
        logger.info(f"Waiting for backup task {trigger_task_id} to complete")
        tasks.wait_for_task(task_id=trigger_task_id, user=context.user, timeout=TimeoutManager.create_backup_timeout)

    return trigger_task_id if trigger_task_id else task_id


def run_hpe_cloud_snapshot_for_rds_instance(
    context: Context, csp_rds_instance_id: str, wait_for_backup: bool = True
) -> str:
    """Function runs the cloud snapshot protection job associated with the given rds instance id.
    return immediately after running the schedule or wait for task based on the set flag.

    Args:
        context (Context): The test Context.
        csp_rds_instance_id (str): csp rds instance id.
        wait_for_backup (bool, optional): If True, this function will wait for the Cloud Snapshot Task to complete. Defaults to True.

    Returns:
        str: The Cloud Snapshot Task ID if the Task was started, None otherwise
    """
    # https://pages.github.hpe.com/cloud/storage-api/#post-/protection-jobs
    # Protection.type: Allowed:  SNAPSHOT, BACKUP, CLOUD_BACKUP, REPLICATED_SNAPSHOT, CLOUD_SNAPSHOT
    # ... 'CLOUD_SNAPSHOT' type is supported only for AWS RDS instances.
    # Not supported for the first release.
    return run_rds_backup(
        context=context,
        csp_rds_instance_id=csp_rds_instance_id,
        backup_type=BackupType.CLOUD_SNAPSHOT,
        wait_for_backup=wait_for_backup,
    )


def run_aws_native_backup_for_rds_instance(
    context: Context, csp_rds_instance_id: str, wait_for_backup: bool = True
) -> str:
    """Function runs the AWS native backup protection job associated with the given rds instance id.
    return immediately after running the schedule or wait for task based on the set flag.

    Args:
        context (Context): The test Context.
        csp_rds_instance_id (str): csp rds instance id.
        wait_for_backup (bool, optional): If True, this function will wait for the Native Backup Task to complete. Defaults to True.

    Returns:
        str: The Native Backup Task ID if the Task was started, None otherwise
    """
    return run_rds_backup(
        context=context,
        csp_rds_instance_id=csp_rds_instance_id,
        backup_type=BackupType.BACKUP,
        wait_for_backup=wait_for_backup,
    )


def run_all_backups_for_rds_instance(
    context: Context, csp_rds_instance_id: str, wait_for_backup: bool = True
) -> list[str]:
    """Function runs all the available backup jobs for the given RDS instance.

    Args:
        context (Context): The test Context.
        csp_rds_instance_id (str): csp rds instance id.
        wait_for_backup (bool, optional): If True, this function will wait for the Native Backup and Cloud Snapshot Tasks to complete. Defaults to True.

    Returns:
        list[str]: A list of backup Task IDs
    """
    task_ids = []

    # Run Native Backup
    task_id = run_aws_native_backup_for_rds_instance(
        context=context, csp_rds_instance_id=csp_rds_instance_id, wait_for_backup=wait_for_backup
    )
    if task_id:
        task_ids.append(task_id)

    # Run Cloud Snapshot
    task_id = run_hpe_cloud_snapshot_for_rds_instance(
        context=context, csp_rds_instance_id=csp_rds_instance_id, wait_for_backup=wait_for_backup
    )
    if task_id:
        task_ids.append(task_id)

    return task_ids


# endregion

# region Delete RDS Backups


def delete_backups_from_rds_instances(
    context: Context, csp_rds_instance_ids: list[str], backup_type: CSPBackupType = None
) -> list[str]:
    """Function deletes all the backups attached to the RDS instance for the specified backup type.
       If backup_type is specified as None. All the backups for that rds instance will be deleted.

    Args:
        context (Context): The test Context
        csp_rds_instance_ids (list): list of csp rds instance id's.
        backup_type (CSPBackupType, optional): The Backup Type to delete for the RDS Instance. Defaults to None.

    Returns:
        task_ids(list[str]): Will return list of task ids
    """

    # Based on the type of backups to be deleted.
    # Using filter, it will get the backups to be deleted. Call method delete_rds_instance_backup to delete the backups
    # It will return list of task ids

    filter: str = ""
    task_ids: list[str] = []
    if backup_type:
        filter = f"backupType eq '{backup_type.value}'"

    for csp_rds_instance_id in csp_rds_instance_ids:
        rds_backup_list: CSPRDSInstanceBackupListModel = (
            context.rds_data_protection_manager.get_csp_rds_instance_backups(
                csp_rds_id=csp_rds_instance_id, filter=filter
            )
        )

        for rds_backup in rds_backup_list.items:
            task_id: str = delete_rds_instance_backup(context=context, backup_id=rds_backup.id)
            task_ids.append(task_id)

    return task_ids


def delete_rds_instance_backup(context: Context, backup_id: str) -> str:
    """This function will delete the specified backup of the rds instance and return task id

    Args:
        context (Context): The test Context
        backup_id (str): backup id

    Returns:
        task_id(str): Will return the task id
    """

    rds_backup: CSPRDSInstanceBackupModel = context.rds_data_protection_manager.get_csp_rds_instance_backup_by_id(
        backup_id=backup_id
    )
    logger.info("Check backup is available for deletion")
    timer: int = 0
    while (rds_backup.state.value == BackupState.IN_USE_FOR_RESTORE.value) and (
        timer < TimeoutManager.restore_rds_backup_timeout
    ):
        timer += 10
        sleep(10)
        continue
    logger.info(f"Deleting RDS Backup {rds_backup.name}:{rds_backup.id}")
    task_id = context.rds_data_protection_manager.delete_csp_rds_instance_backup_by_id(backup_id=backup_id)

    logger.info(f"Wait for {TimeoutManager.standard_task_timeout} to delete the rds backup id {rds_backup.id}")

    task_status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=TimeoutManager.standard_task_timeout)

    if task_status.lower() != TaskStatus.success.value.lower():
        logger.error(
            f"RDS Backup {rds_backup.name}:{rds_backup.id} deletion failed. TaskID:{task_id} TaskStatus:{task_status}"
        )
    else:
        logger.info(f"RDS Backup {rds_backup.name}:{rds_backup.id} is deleted successfully")

    return task_id


def delete_rds_instance_backup_expected_code(
    context: Context, backup_id: str, expected_code: int = requests.codes.accepted
) -> Union[str, GLCPErrorResponse]:
    """Deletes a specific CSP RDS instance backup ID

    Args:
        context (Context): The test Context
        backup_id (str): CSP RDS backup ID
        expected_code (int, optional): Status code to compare with expected status code. Defaults to requests.codes.accepted.

    Returns:
        Union[str, GLCPErrorResponse]: Returns delete Task ID if successful else returns GLCPErrorResponse
    """
    return_data = context.rds_data_protection_manager.delete_csp_rds_instance_backup_by_id(
        backup_id=backup_id, expected_code=expected_code
    )
    return return_data


# endregion

# region RDS Backup Info: State, Status, Count, Expiration, Protections


def get_rds_instance_backup_count(context: Context, csp_rds_instance_id: str) -> dict:
    """Function returns the no. of backups for the rds instance

    Args:
        context (Context): The test Context
        csp_rds_instance_id (str): csp rds instance id

    Returns:
        dict: Object with the backup count details:
        eg:
            {
            NATIVE_BACKUP: int,
            CLOUD_BACKUP: int,
            total: int
            }
    """

    backup_objs: CSPRDSInstanceBackupListModel = context.rds_data_protection_manager.get_csp_rds_instance_backups(
        csp_rds_id=csp_rds_instance_id
    )
    logger.info(f"List of backups: {backup_objs.items}")

    native_backup_count: int = 0
    cloud_backup_count: int = 0
    for backup_obj in backup_objs.items:
        if backup_obj.backup_type.value == CSPBackupType.NATIVE_BACKUP.value:
            native_backup_count += 1
        elif backup_obj.backup_type.value == CSPBackupType.HPE_CLOUD_BACKUP.value:
            cloud_backup_count += 1

    backup_counts = {
        CSPBackupType.NATIVE_BACKUP.value: native_backup_count,
        CSPBackupType.HPE_CLOUD_BACKUP.value: cloud_backup_count,
        "total": backup_objs.total,
    }
    logger.info(f"Backup Counts of RDS Instance {csp_rds_instance_id}:{backup_counts}")

    return backup_counts


def validate_rds_instance_backup_state_and_count(
    context: Context,
    csp_rds_instance_id: str,
    expected_native_backup_count: int,
    expected_cloud_snapshot_count: int = 0,
    state: BackupState = BackupState.OK,
) -> bool:
    """Validate the backup count of rds instance
    NOTE: If the expected_native_backup_count or expected_cloud_snapshot_count is 0
          then backup_state check will be skipped

    Args:
        context (Context): The test Context
        csp_rds_instance_id (str): csp rds instance id
        expected_native_backup_count (int): expected native backup count in decimal value
        expected_cloud_snapshot_count (int): expected cloud snapshot count in decimal value
        state (BackupState, optional): state of the backup to check. Defaults to BackupState.OK.

    Returns:
        bool: True indicates success and False results in validation failure.
    """

    backup_objs = context.rds_data_protection_manager.get_csp_rds_instance_backups(csp_rds_id=csp_rds_instance_id)
    logger.info(f"List of backups: {backup_objs.items}")

    backup_state_result = True
    for backup_obj in backup_objs.items:
        status = check_rds_instance_backup_state(context=context, backup_id=backup_obj.id, backup_state=state)
        if status is not True:
            backup_state_result = status

    backup_count = get_rds_instance_backup_count(context=context, csp_rds_instance_id=csp_rds_instance_id)
    logger.info(f"Backup count: {backup_count}")

    instance_backup_info_count = get_backup_count_from_rds_instance_backup_info(
        context=context, csp_rds_instance_id=csp_rds_instance_id
    )
    logger.info(f"Instance backup info count: {instance_backup_info_count}")

    expected_total_backup_count = expected_native_backup_count + expected_cloud_snapshot_count
    expected_backup_count: dict = {
        CSPBackupType.NATIVE_BACKUP.value: expected_native_backup_count,
        CSPBackupType.HPE_CLOUD_BACKUP.value: expected_cloud_snapshot_count,
        "total": expected_total_backup_count,
    }
    logger.info(f"Expected Backup Count details = {expected_backup_count}")

    backup_count_result = False
    if expected_backup_count == backup_count == instance_backup_info_count:
        backup_count_result = True
    else:
        logger.error("There is a mismatch between the backup counts")

    logger.info(f"Backup count: {backup_count}")
    logger.info(f"Instance backup info count: {instance_backup_info_count}")
    logger.info(f"Expected Backup Count details = {expected_backup_count}")
    return backup_count_result & backup_state_result


def get_backup_count_from_rds_instance_backup_info(context: Context, csp_rds_instance_id: str) -> dict:
    """Get Backup count details from rds Instance details "backup_info"

    Args:
        context (Context): The test Context
        csp_rds_instance_id (str): csp rds instance id

    Returns:
        dict: Object with the backup count details:
        eg:
            {
            NATIVE_BACKUP: int,
            CLOUD_BACKUP: int,
            total: int
            }
    """

    instance_details = CSPRDSInvMgrSteps.get_csp_rds_instance_by_id(
        context=context,
        csp_rds_instance_id=csp_rds_instance_id,
    )
    logger.info(f"instance backup counts: {instance_details.backup_info}")
    instance_backup_info_count: dict = {CSPBackupType.HPE_CLOUD_BACKUP.value: 0, CSPBackupType.NATIVE_BACKUP.value: 0}

    for backup_info in instance_details.backup_info:
        if backup_info.type == CSPBackupType.NATIVE_BACKUP.value:
            instance_backup_info_count[CSPBackupType.NATIVE_BACKUP.value] = backup_info.count
        elif backup_info.type == CSPBackupType.HPE_CLOUD_BACKUP.value:
            instance_backup_info_count[CSPBackupType.HPE_CLOUD_BACKUP.value] = backup_info.count

    total_instance_backup_count = (
        instance_backup_info_count[CSPBackupType.NATIVE_BACKUP.value]
        + instance_backup_info_count[CSPBackupType.HPE_CLOUD_BACKUP.value]
    )
    instance_backup_info_count["total"] = total_instance_backup_count
    logger.info(f"Instance Backup Info Count: {instance_backup_info_count}")

    return instance_backup_info_count


def check_rds_instance_backup_state(context: Context, backup_id: str, backup_state: BackupState) -> bool:
    """Validate the state of RDS Backup

    Args:
        context (Context): The test Context
        backup_id (str): rds instance backup id
        state (BackupState): BackupState

    Returns:
        bool: Return true if the validation is successful. Else return false
    """
    result: bool = False
    backup_obj: CSPRDSInstanceBackupModel = context.rds_data_protection_manager.get_csp_rds_instance_backup_by_id(
        backup_id=backup_id
    )
    logger.info(f"backup: {backup_obj}")
    if backup_obj.state == backup_state:
        result = True
        logger.info(f"RDS Backup {backup_obj.name}:{backup_obj.id} state is validated successful")
    else:
        logger.error(
            f"RDS Backup {backup_obj.name}:{backup_obj.id} state {backup_obj.state.value} doesn't match the expected state {backup_state.value}"
        )

    return result


def wait_for_backup_status_active(context: Context, rds_asset_id: str):
    """Wait for RDS Backup Status to be Active

    Args:
        context (Context): Context object
        rds_asset_id (str): CSP RDS ID
    """

    def _get_backups_status(context: Context, rds_asset_id):
        backups = context.rds_data_protection_manager.get_csp_rds_instance_backups(csp_rds_id=rds_asset_id)

        logger.info(f"wait_for_backup_status_active rds_asset_id: {rds_asset_id} - backups:{backups}")
        if backups.total:
            for backup in backups.items:
                if backup.state != BackupState.OK or backup.status != Status.ACTIVE:
                    return False

        return True

    wait(
        lambda: _get_backups_status(context=context, rds_asset_id=rds_asset_id),
        timeout_seconds=60 * 60,
        sleep_seconds=60,
    )


def get_protections_from_job(protection_job: ProtectionJob, backup_types: list[BackupType]) -> list[Protection]:
    """Get the requested Protections from the ProtectionJob.

    Args:
        protection_job (ProtectionJob): A ProtectionJob.
        backup_types (list[BackupType]): A list of BackupType to look for in the ProtectionJob.

    Returns:
        list[Protection]: A list containing any of the requested BackupTypes.
    """
    protections: list[Protection] = []

    for protection in protection_job.protections:
        if BackupType(protection.type) in backup_types:
            protections.append(protection)

    return protections


# endregion
