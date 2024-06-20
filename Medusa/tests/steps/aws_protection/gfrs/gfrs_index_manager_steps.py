import logging
import requests

from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.csp_resource_type import CSPResourceType
from lib.common.enums.task_status import TaskStatus
from lib.common.enums.index_status import IndexStatus

from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.csp_indexed_file_system_info_model import (
    CSPIndexedFileSystemInfoListModel,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.gfrs_models import PostCSPFileSystemInfoModel
import tests.steps.aws_protection.backup_steps as BS

from tests.steps.tasks import tasks
from tests.e2e.aws_protection.context import Context

from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()

DELETE_BACKUP = "Backup"
DELETE_CLOUD_BACKUP = "HPE_Cloud_Backup"
# Delete index data workflow for asset [i-0e64399fc498b7d87]: (i-0e64399fc498b7d87)-HPE_Cloud_Backup-(2023-07-25T16:18:42Z)
# Delete index data workflow for asset [i-0e64399fc498b7d87]: (i-0e64399fc498b7d87)-Backup-(2023-07-25T15:57:33Z)
# The tail-end date/time is dropped for name matching. In testing, that value does not always match "create_at" or "point_in_time" for the CSPBackup
DELETE_INDEX_FILES_TASK_TEMPLATE = "Delete index data workflow for asset [{0}]: ({0})-{1}"
#
# RFE: https://nimblejira.nimblestorage.com/browse/DCS-11724
# Changed the name of the "Delete Index" task. The change is currently only on FILEPOC.
# If we do not find the "old" task name, then we will look for the "new" task name.
#   Delete index data workflow for backup (i-02338556dc4dba32d)-Backup-(2023-09-06T16:49:43Z)
#   Delete index data workflow for backup (i-02338556dc4dba32d)-HPE_Cloud_Backup-(2023-09-06T17:08:49Z)
DELETE_INDEX_FILES_TASK_TEMPLATE_NEW = "Delete index data workflow for backup ({0})-{1}"


def index_guest_files_on_csp_volume_backup(
    context: Context,
    csp_volume_id: str,
    csp_backup_id: str,
    post_file_system_info: PostCSPFileSystemInfoModel = "{}",
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
) -> str:
    """Indexes files on a CSP Volume's backup

    Args:
        context (Context): Context object
        csp_volume_id (str): CSP Volume ID
        csp_backup_id (str): CSP Volume's backup ID
        post_file_system_info (PostCSPFileSystemInfoModel): PostCSPFileSystemInfoModel object
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.

    Returns:
        str: task_id of the operation
    """
    logger.info(f"Indexing files for CSP Volume {csp_volume_id}, backup {csp_backup_id}")
    task_id = context.gfrs_index_manager.index_guest_files_on_csp_volume_backup(
        csp_backup_id=csp_backup_id,
        post_file_system_info=post_file_system_info,
        response_code=response_code,
    )
    logger.info(f"Task ID for indexing is {task_id}")

    if wait_for_task:
        logger.info(f"Waiting for Files indexing for CSP Volume {csp_volume_id}, backup {csp_backup_id} to complete")
        refresh_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.index_backup_timeout,
        )

        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"GFR Indexing for CSP Volume {csp_volume_id}, backup {csp_backup_id} failed"

    return task_id


def index_guest_files_on_csp_instance_backup(
    context: Context,
    csp_instance_id: str,
    csp_backup_id: str,
    post_file_system_info: PostCSPFileSystemInfoModel = "{}",
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    status_code: TaskStatus = TaskStatus.success,
) -> str:
    """Indexes files on a CSP Volume's backup

    Args:
        context (Context): Context object
        csp_instance_id (str): CSP Machine ID
        csp_backup_id (str): CSP Machine's backup ID
        post_file_system_info (PostCSPFileSystemInfoModel): PostCSPFileSystemInfoModel object
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.
        status_code (TaskStatus, optional): The expected task status, used if wait_for_task is True. Defaults to TaskStatus.success

    Returns:
        str: task_id of the operation
    """
    logger.info(f"Indexing files for CSP Machine {csp_instance_id}, backup {csp_backup_id}")
    task_id = context.gfrs_index_manager.index_guest_files_on_csp_machine_instance_backup(
        csp_backup_id=csp_backup_id,
        post_file_system_info=post_file_system_info,
        response_code=response_code,
    )
    logger.info(f"Task ID for indexing is {task_id}")

    if wait_for_task:
        logger.info(f"Waiting for Files indexing for CSP Machine {csp_instance_id}, backup {csp_backup_id} to complete")
        task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.index_backup_timeout,
        )

        assert (
            task_status.upper() == status_code.value
        ), f"GFRS Indexing for CSP Machine instance {csp_instance_id}, backup {csp_backup_id} did not end in the expected status: {status_code.value} : {task_status.upper()}"

    return task_id


def get_indexed_file_system_info_for_backup(
    context: Context, csp_asset_type: CSPResourceType, csp_asset_id: str, csp_backup_id: str
) -> CSPIndexedFileSystemInfoListModel:
    """
    Get indexed filesystem info of csp backup for an CSP asset

    Args:
        context (Context): Context
        csp_asset_type (CSPResourceType): CSP Asset Type
        csp_asset_id (str): CSP Asset ID
        csp_backup_id (str): CSP Backup ID

    Returns:
        CSPIndexedFileSystemInfoListModel: CSPIndexedFileSystemInfoListModel Object
    """

    logger.info(f"Fetching filesystem indexed for CSP BackupID {csp_backup_id}")
    csp_indexed_file_system_info_list = context.gfrs_index_manager.get_indexed_file_system_info_for_backup(
        csp_asset_type=csp_asset_type,
        csp_asset_id=csp_asset_id,
        csp_backup_id=csp_backup_id,
    )
    logger.info(f"Indexed File System Info for CSP Asset {csp_asset_id} is {csp_indexed_file_system_info_list}")

    return csp_indexed_file_system_info_list


def delete_indexed_files_for_backup(
    context: Context, csp_asset_type: CSPResourceType, csp_asset_id: str, csp_backup_id: str
):
    """
    Perform Delete index for the specified CSP backup

    Args:
        context (Context): Context
        csp_asset_type (CSPResourceType): CSP Asset Type
        csp_asset_id (str): CSP Asset ID
        csp_backup_id (str): CSP Backup ID
    """
    logger.info(f"Performing delete index for backup ID {csp_backup_id} ")
    context.gfrs_index_manager.delete_indexed_files_for_backup(
        csp_asset_type=csp_asset_type,
        csp_asset_id=csp_asset_id,
        csp_backup_id=csp_backup_id,
    )
    logger.info(f"Delete index for backup ID {csp_backup_id} is initiated")


def delete_index_files_for_csp_instance_backups_and_wait(context: Context, csp_instance_id: str, aws_asset_id: str):
    """Delete index-files associated with any CSP Backups for the given CSP Instance and wait for the Delete tasks to complete

    Args:
        context (Context): The test Context
        csp_instance_id (str): The CSP Instance ID
        aws_asset_id (str): The AWS EC2 Instance ID
    """
    logger.info(f"Deleting index-files for CSP Instance {csp_instance_id} Backups")

    backup_list = BS.get_csp_machine_instance_backups(context=context, machine_instance_id=csp_instance_id)
    # delete any Indexed-Files for the Backups
    for backup in backup_list.items:
        if backup.backup_type == CSPBackupType.STAGING_BACKUP.value:
            continue
        if backup.index_status != IndexStatus.NOT_INDEXED:
            # Call Internal API to delete the Indexed-Files for this backup
            delete_indexed_files_for_backup(
                context=context,
                csp_asset_type=CSPResourceType.INSTANCE_RESOURCE_TYPE,
                csp_asset_id=csp_instance_id,
                csp_backup_id=backup.id,
            )

    # find and wait for all tasks for this asset id
    find_and_wait_for_delete_index_tasks(context=context, aws_asset_id=aws_asset_id)


def delete_index_files_for_csp_volume_backups_and_wait(context: Context, csp_volume_id: str, aws_asset_id: str):
    """Delete index-files associated with any CSP Backups for the given CSP Volume and wait for the Delete tasks to complete

    Args:
        context (Context): The test Context
        csp_instance_id (str): The CSP Volume ID
        aws_asset_id (str): The AWS EBS Volume ID
    """
    logger.info(f"Deleting index-files for CSP Volume {csp_volume_id} Backups")

    backup_list = BS.get_csp_volume_backups(context=context, volume_id=csp_volume_id)
    # delete any Indexed-Files for the Backups
    for backup in backup_list.items:
        if backup.backup_type == CSPBackupType.STAGING_BACKUP.value:
            continue
        # Call Internal API to delete the Indexed-Files for this backup
        if backup.index_status != IndexStatus.NOT_INDEXED:
            # Call Internal API to delete the Indexed-Files for this backup
            delete_indexed_files_for_backup(
                context=context,
                csp_asset_type=CSPResourceType.VOLUME_RESOURCE_TYPE,
                csp_asset_id=csp_volume_id,
                csp_backup_id=backup.id,
            )

    # find and wait for all tasks for this asset id
    find_and_wait_for_delete_index_tasks(context=context, aws_asset_id=aws_asset_id)


def find_and_wait_for_delete_index_tasks(context: Context, aws_asset_id: str):
    """Find all 'DeleteIndexDataWorkflow' tasks related to the AWS EC2 Instance or EBS Volume ID, and wait for all to complete

    Args:
        context (Context): The test Context
        aws_asset_id (str): The AWS EC2 Instance or EBS Volume ID
    """
    # find and wait for all tasks for this asset id
    native_backup_display_name = DELETE_INDEX_FILES_TASK_TEMPLATE.format(aws_asset_id, DELETE_BACKUP)
    cloud_backup_display_name = DELETE_INDEX_FILES_TASK_TEMPLATE.format(aws_asset_id, DELETE_CLOUD_BACKUP)

    logger.info(f"Looking for Delete Index task name: {native_backup_display_name}")

    task_list = tasks.get_delete_indexed_files_tasks_containing_name(
        user=context.user, task_name=native_backup_display_name
    )
    # If "task_list" is empty, we didn't find the "Delete Index" task.  Update the name search to the "NEW" names
    if not task_list:
        native_backup_display_name = DELETE_INDEX_FILES_TASK_TEMPLATE_NEW.format(aws_asset_id, DELETE_BACKUP)
        cloud_backup_display_name = DELETE_INDEX_FILES_TASK_TEMPLATE_NEW.format(aws_asset_id, DELETE_CLOUD_BACKUP)
        logger.info(f"task_list is empty - switch to new Task Name: {native_backup_display_name}")

        task_list = tasks.get_delete_indexed_files_tasks_containing_name(
            user=context.user, task_name=native_backup_display_name
        )

    task_list.extend(
        tasks.get_delete_indexed_files_tasks_containing_name(user=context.user, task_name=cloud_backup_display_name)
    )

    for task in task_list:
        logger.info(f"Waiting for TaskID: {task.id}")
        tasks.wait_for_task(task_id=task.id, user=context.user, timeout=TimeoutManager.standard_task_timeout)
