"""
This file contains functions for the backup activities of EKS K8s cluster applications.
"""

import logging
from subprocess import TimeoutExpired
from lib.common.enums.asset_info_types import AssetType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_eks_k8s_app_backup_model import (
    CSPK8sAppBackupInfoModel,
    CSPK8sAppBackupListModel,
)

from lib.dscc.backup_recovery.protection_policies.rest.v1beta1.models.protection_jobs import (
    Protection,
    ProtectionJob,
)
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.backup_type import BackupType
from lib.common.enums.backup_state import BackupState
import tests.steps.aws_protection.backup_steps as BackupSteps
from lib.common.enums.csp_k8s_backup_status import CSPK8sBackupStatus
from lib.common.enums.atlas_error_messages import AtlasErrorMessages
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.backup_steps import (
    perform_copy2cloud_for_delete_tasks,
    delete_backups_check_task,
)
import tests.steps.aws_protection.common_steps as CommonSteps
from tests.steps.aws_protection.eks.csp_eks_inventory_steps import (
    get_csp_k8s_cluster_by_name,
)
from tests.steps.aws_protection.eks.eks_common_steps import (
    assign_protection_policy_to_eks_app,
    cleanup_and_create_protection_policy_for_eks_app,
    get_eks_k8s_cluster_app_by_name,
)
from tests.steps.tasks import tasks
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps
from utils.timeout_manager import TimeoutManager

from lib.common.enums.task_status import TaskStatus

from lib.dscc.backup_recovery.aws_protection.backup_restore.models.csp_eks_k8s_app_backup import (
    CSPK8sAppBackupInfo,
    CSPK8sAppBackupList,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.patch_csp_eks_k8s_backup import (
    PatchCSPK8sAppBackup,
)
from waiting import wait

logger = logging.getLogger()


def get_protection_job(
    context: Context,
    csp_k8s_application_id: str,
) -> ProtectionJob:
    """Get Protection Job for an k8s namespaced application.

    Args:
        context (Context): The test Context.
        csp_k8s_application_id (str): CSP k8s application id.

    Returns:
        ProtectionJob: The ProtectionJob for the k8s application if found, None otherwise.
    """

    protection_job: ProtectionJob = None

    logger.info("Get the protection job")
    protection_jobs = context.policy_manager.get_protection_job_by_asset_id(asset_id=csp_k8s_application_id)

    if protection_jobs.total:
        protection_job = protection_jobs.items[0]

    return protection_job


def get_protections_from_job(
    protection_job: ProtectionJob,
    backup_types: list[BackupType],
) -> list[Protection]:
    """Get the list of Protections from the ProtectionJob.

    Args:
        protection_job (ProtectionJob): Protection job info.
        backup_types (list[BackupType]): A list of BackupType to look for in the ProtectionJob.

    Returns:
        list[Protection]: A list containing any of the requested BackupTypes.
    """
    protections: list[Protection] = []

    for protection in protection_job.protections:
        if BackupType(protection.type) in backup_types:
            protections.append(protection)

    return protections


def run_k8s_app_native_backup(
    context: Context,
    csp_k8s_application_id: str,
    app_name: str,
    csp_account: CSPAccountModel,
    negative_test: bool = False,
    return_backup_task: bool = False,
    backup_sync_timeout=10,
) -> str:
    """Run the Native Backup job, associated with the given k8s application id.

    Args:
        context (Context): The test Context.
        csp_k8s_application_id (str): csp k8s namespaced application id.
        app_name (str): Backing up app name
        csp_account (CSPAccountModel)
        negative_test (bool): flag for negative workflows
        return_backup_task (bool): returns backup task based on the flag, defaults to False.

    Returns:
        str: Backup ID or empty string in case of failure
    """
    logger.info("Get the protection job for k8s application")
    protection_job = get_protection_job(context=context, csp_k8s_application_id=csp_k8s_application_id)
    if not protection_job:
        logger.warn(f"No protection job assigned to an K8s application: {csp_k8s_application_id}")
        return None

    logger.info("Get the protections from the protection job")
    protections = get_protections_from_job(protection_job=protection_job, backup_types=[BackupType.BACKUP])
    if not protections:
        logger.warn(f"No {BackupType.BACKUP} protection schedule in ProtectionJob: {protection_job.id}")
        return None

    backup_count_before = get_k8s_app_backup_count(context, csp_k8s_application_id, BackupType.NATIVE_BACKUP)

    logger.info("Run the backup for a specified protection schedule from the ProtectionJob")
    task_id = context.policy_manager.run_protection_job(
        protection_job_id=protection_job.id,
        protection_schedule_ids=[protections[0].schedules[0].schedule_id],
    )

    if negative_test:
        # Return task id
        return task_id

    task_status = tasks.wait_for_task(
        task_id=task_id,
        user=context.user,
        timeout=TimeoutManager.create_backup_timeout,
    )
    assert (
        task_status.lower() == TaskStatus.success.value.lower()
    ), f"Failed to run backup job for backup type: {BackupType.NATIVE_BACKUP}"

    protection_jobs_running = tasks.get_tasks_by_name_and_customer_account(
        user=context.user,
        task_name=f"Trigger Native Backup for CSPK8sApplication [{app_name}]",
        customer_id=csp_account.customerId,
    )
    if not protection_jobs_running:
        logger.warning(f"No running protection jobs found for {app_name}")
        return None

    last_protection_job_running_id = protection_jobs_running[0].id
    if return_backup_task:
        return last_protection_job_running_id

    # wait for backup to finish
    task_status = tasks.wait_for_task(
        task_id=last_protection_job_running_id,
        user=context.user,
        timeout=TimeoutManager.create_backup_timeout,
    )
    if task_status.lower() != TaskStatus.success.value.lower():
        logger.error(f"Failed to trigger backup job for backup type: {BackupType.NATIVE_BACKUP}")
        return None

    # compare backup count before and after protection job
    try:
        wait(
            lambda: get_k8s_app_backup_count(context, csp_k8s_application_id, BackupType.NATIVE_BACKUP)
            == backup_count_before + 1,
            timeout_seconds=backup_sync_timeout,
            sleep_seconds=(0.1, 4),
        )
    except TimeoutExpired:
        raise TimeoutError(f"Backup count didn't increase after backup task success in {backup_sync_timeout} seconds.")
    backup_count_after = get_k8s_app_backup_count(context, csp_k8s_application_id, BackupType.NATIVE_BACKUP)
    assert (
        backup_count_before + 1
    ) == backup_count_after, f"Native backup count didn't increase by 1 after taking a backup. Before: {backup_count_before}, after: {backup_count_after}."
    logger.info(f"Native backup job ran successfully for backup type: {BackupType.NATIVE_BACKUP}")
    return last_protection_job_running_id


def run_k8s_app_native_backup_with_error(
    context: Context,
    csp_k8s_application_id: str,
    app_name: str,
    csp_account: CSPAccountModel,
    expected_error_message: str,
) -> str:
    """Run the Native Backup job, associated with the given k8s application id with expected error message.

    Args:
        context (Context): The test Context.
        csp_k8s_application_id (str): csp k8s namespaced application id.
        app_name (str): Backing up app name
        csp_account (CSPAccountModel)
        expected_error_message (str): error message for backup failure
    """
    logger.info("Get the protection job for k8s application")
    protection_job = get_protection_job(context=context, csp_k8s_application_id=csp_k8s_application_id)
    if not protection_job:
        logger.warn(f"No protection job assigned to an K8s application: {csp_k8s_application_id}")
        return None

    logger.info("Get the protections from the protection job")
    protections = get_protections_from_job(protection_job=protection_job, backup_types=[BackupType.BACKUP])
    if not protections:
        logger.warn(f"No {BackupType.BACKUP} protection schedule in ProtectionJob: {protection_job.id}")
        return None

    logger.info("Run the backup for a specified protection schedule from the ProtectionJob")
    task_id = context.policy_manager.run_protection_job(
        protection_job_id=protection_job.id,
        protection_schedule_ids=[protections[0].schedules[0].schedule_id],
    )

    task_status = tasks.wait_for_task(
        task_id=task_id,
        user=context.user,
        timeout=TimeoutManager.create_backup_timeout,
    )

    protection_jobs_running = tasks.get_tasks_by_name_and_customer_account(
        user=context.user,
        task_name=f"Trigger Native Backup for CSPK8sApplication [{app_name}]",
        customer_id=csp_account.customerId,
    )
    if not protection_jobs_running:
        logger.warning(f"No running protection jobs found for {app_name}")
        return None

    last_protection_job_running_id = protection_jobs_running[0].id

    task_status = tasks.wait_for_task(
        task_id=last_protection_job_running_id,
        user=context.user,
        timeout=TimeoutManager.create_backup_timeout,
    )

    assert (
        task_status.lower() == TaskStatus.failed.value.lower()
    ), f"Expected task to fail, but had status {task_status.lower()}"

    task_error_message = tasks.get_task_error(task_id=last_protection_job_running_id, user=context.user)
    assert (
        task_error_message == expected_error_message
    ), f"Error message was not as expected. Expected message: {expected_error_message}, but was {task_error_message}"


def cleanup_create_assign_policy_run_backup_eks(
    context: Context,
    protection_policy_name: str,
    app_name: str,
    csp_k8s_app_id: str,
    cloud_only: bool = False,
    backup_only: bool = False,
    immutable: bool = False,
):
    """Cleanup, create and assign protection policy to EKS app and run backup.

    Args:
        context (Context): context object
        protection_policy_name (str): name for created protection policy
        app_name (str): EKS application name
        csp_k8s_app_id (str): EKS k8s application ID
        cloud_only (bool, optional): If True, only a CloudBackup schedule will be created. Defaults to False.
        backup_only (bool, optional): If True, only a Backup schedule will be created. Defaults to False.
    """
    cleanup_and_create_protection_policy_for_eks_app(
        context,
        protection_policy_name,
        csp_k8s_app_id,
        cloud_only=cloud_only,
        backup_only=backup_only,
        immutable=immutable,
    )
    assign_protection_policy_to_eks_app(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        app_name,
        context.protection_policy_id,
    )
    app_id = get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        app_name,
    )
    if not cloud_only:
        perform_and_verify_native_backup(context, context.aws_eks_account_name, app_id, app_name)

    if not backup_only:
        csp_account: CSPAccountModel = CAMSteps.get_csp_account_by_csp_name(
            context, account_name=context.aws_eks_account_name
        )
        csp_cluster_info = get_csp_k8s_cluster_by_name(
            context, context.eks_cluster_name, context.eks_cluster_aws_region
        )
        csp_cluster_id = csp_cluster_info.id
        CommonSteps.run_and_verify_eks_cloud_backup(
            context=context,
            csp_account=csp_account,
            csp_asset_id=app_id,
            asset_type=AssetType.CSP_K8S_APPLICATION,
            region=context.eks_cluster_aws_region,
            wait_for_task_complete=False,
            copy_2_cloud=True,
            csp_cluster_id=csp_cluster_id,
        )


def get_k8s_app_backup_count(
    context: Context, csp_k8s_application_id: str, backup_type: CSPBackupType, return_backup_ids: bool = False
) -> int:
    """Get the backups count for k8s namespaced application

    Args:
        context (Context): The test Context
        csp_k8s_application_id (str): csp k8s namespaced application id
        backup_type: (CSPBackupType): backup type to get the count

    Returns:
        int: backup count of the provided backup type.
    """
    # for temporary commenting this filter line as we have an open issue DCS-10793.
    # filter = f"backupType eq '{backup_type.value}'"
    k8s_app_backup_list: CSPK8sAppBackupListModel = context.eks_data_protection_manager.get_csp_k8s_app_backups(
        csp_k8s_application_id=csp_k8s_application_id
    )
    backups_count = 0
    backups_list = None
    logger.debug(f"List of all backups: {k8s_app_backup_list.items}")
    if k8s_app_backup_list.total > 0:
        backups_list = [each.id for each in k8s_app_backup_list.items if each.backup_type == backup_type.value]
        backups_count = len(backups_list)
    else:
        logger.warning(f"There are no backups available for the given app {csp_k8s_application_id}")
    if return_backup_ids:
        return backups_list
    return backups_count


def get_k8s_app_all_backup_counts(context: Context, csp_k8s_application_id: str) -> dict:
    """Get the backups count for k8s namespaced application it gets all backups types count

    Args:
        context (Context): The test Context
        csp_k8s_application_id (str): csp k8s namespaced application id

    Returns:
        dict: backup count dictionary with keys NATIVE_BACKUP_COUNT and HPE_CLOUD_BACKUP_COUNT
    """
    k8s_app_backup_list: CSPK8sAppBackupListModel = context.eks_data_protection_manager.get_csp_k8s_app_backups(
        csp_k8s_application_id=csp_k8s_application_id
    )
    backups_count_dict = {"NATIVE_BACKUP_COUNT": 0, "HPE_CLOUD_BACKUP_COUNT": 0}
    logger.debug(f"List of all backups: {k8s_app_backup_list.items}")
    if k8s_app_backup_list.total > 0:
        native_backups_list = [
            each.id for each in k8s_app_backup_list.items if each.backup_type == CSPBackupType.NATIVE_BACKUP
        ]
        hpe_cloud_backups_list = [
            each.id for each in k8s_app_backup_list.items if each.backup_type == CSPBackupType.HPE_CLOUD_BACKUP
        ]
        backups_count_dict["NATIVE_BACKUP_COUNT"] = len(native_backups_list)
        backups_count_dict["HPE_CLOUD_BACKUP_COUNT"] = len(hpe_cloud_backups_list)
    else:
        logger.warning(f"There are no backups available for the given app {csp_k8s_application_id}")
    return backups_count_dict


def delete_all_k8s_apps_backups(
    context: Context,
    csp_k8s_application_ids: list[str],
    csp_account: CSPAccountModel,
    region: str,
    skip_immutable_backup: bool = False,
    wait_for_error: bool = False,
):
    """Deletes all the backups attached to the k8s namespaced applications for any backup type.

    Args:
        context (Context): The test Context
        csp_k8s_application_ids (list): List of csp k8s namespaced applications ids
        csp_account (CSPAccountModel): The CSP Account
        region (str): The region for the CSP Account
        skip_immutable_backup (bool, optional): Skip immutable backup, while deletion. Defaults to False.
        wait_for_error (bool, optional): Waits for task failure. Defaults to False
    """
    cloud_tasks: list[str] = []

    # delete_machine_instance_backups() handles "Cloud Backup Deletion", returns list of Cloud Backup Delete task IDs
    for csp_k8s_application_id in csp_k8s_application_ids:
        logger.info(f"Deleting backups for CSP Instance: {csp_k8s_application_id}")
        cloud_tasks.extend(
            delete_k8s_app_backups(
                context=context,
                csp_k8s_application_id=csp_k8s_application_id,
                skip_immutable_backup=skip_immutable_backup,
                wait_for_error=wait_for_error,
            )
        )
        logger.info(f"Number of Cloud delete tasks: {len(cloud_tasks)}")

    # if cloud_tasks are returned, then perform /copy2cloud for the cloud delete tasks
    if len(cloud_tasks):
        logger.info(f"Performing /copy2cloud for {len(cloud_tasks)} Cloud Backup Delete Tasks...")
        perform_copy2cloud_for_delete_tasks(
            context=context,
            csp_account=csp_account,
            region=region,
            cloud_tasks=cloud_tasks,
        )


def delete_k8s_app_backups(
    context: Context,
    csp_k8s_application_id: str,
    skip_immutable_backup: bool = False,
    wait_for_error: bool = False,
) -> list[str]:
    """Deletes Backups for the given EKS app

    Args:
        context (Context): The test Context
        csp_k8s_application_id (str): CSP EKS App ID
        skip_immutable_backup (bool, optional): Skip immutable backup, while deletion. Defaults to False.
        wait_for_error (bool, optional): Waits for task failure. Defaults to False.

    Returns:
        list[str]: List of task ids for backups that were deleted
    """
    backup_list = context.eks_data_protection_manager.get_csp_k8s_app_backups(
        csp_k8s_application_id=csp_k8s_application_id
    )

    cloud_tasks: list[str] = []

    if not backup_list.total:
        logger.warning(f"There are no backups to delete for EKS app id: '{csp_k8s_application_id}'")
        return cloud_tasks

    logger.info(f"There are {backup_list.total} backups")

    for backup in backup_list.items:
        logger.info(f"backupType: {backup.backup_type}")
        logger.info(f"Deleting k8s application Backup ID: {backup.id}")
        # skip Staging
        if backup.backup_type == CSPBackupType.STAGING_BACKUP.value:
            logger.info("skip staging")
            continue

        # To avoid clean up error while running on jenkins skip deleting cloud backup as it is immutable
        backup_detail = context.eks_data_protection_manager.get_csp_k8s_app_backup_details(
            csp_k8s_application_id=csp_k8s_application_id,
            backup_id=backup.id,
        )
        if backup_detail.locked_until and skip_immutable_backup:
            logger.info(f"skip backup {backup.id} deletion as it is immutable cant be deleted")
            continue

        task_id = context.eks_data_protection_manager.delete_csp_k8s_app_backup(
            csp_k8s_application_id=csp_k8s_application_id,
            backup_id=backup.id,
        )

        logger.info(f"Waiting for Delete backup for an EKS app {csp_k8s_application_id} task: {task_id}")
        # for the case where 'None' is returned from 'delete_backups_check_task()', don't add it to 'cloud_tasks'
        cloud_task_id = delete_backups_check_task(
            context=context,
            asset_id=csp_k8s_application_id,
            task_id=task_id,
            backup=backup,
            wait_for_error=wait_for_error,
        )
        if cloud_task_id:
            cloud_tasks.append(cloud_task_id)

    return cloud_tasks


def delete_k8s_app_backup(
    context: Context,
    csp_k8s_application_id: str,
    backup_id: str,
    csp_account: CSPAccountModel,
    region: str,
    copy_2_cloud: bool = False,
) -> bool:
    """Delete the specified backup of the csp k8s namespaced application

    Args:
        context (Context): The test Context
        csp_k8s_application_id (str): CSP k8s namespaced application id.
        backup_id (str): Backup id to be deleted
        csp_account (CSPAccountModel): CSP Account model object
        region (str): Asset region
        copy_2_cloud (bool, optional): Runs copy_2_cloud endpoint if set to True. Defaults to False

    Returns:
        boolean: True of false based on the task result
    """

    logger.info(f"Deleting k8s application Backup ID: {backup_id}")
    task_id = context.eks_data_protection_manager.delete_csp_k8s_app_backup(
        csp_k8s_application_id=csp_k8s_application_id,
        backup_id=backup_id,
    )

    if copy_2_cloud:
        # Triggering copy_2_cloud to initiate k8s backup delete
        logger.info(f"Calling Copy2Cloud for {csp_account.name} in Region {region}")
        BackupSteps.run_copy2cloud_endpoint(context=context, account_name=csp_account.name, region=region)
        logger.info("copy2cloud endpoint called")

        logger.info(
            f"Find and wait for copy2cloud task to complete. customerID: {csp_account.customerId} accountID: {csp_account.id}"
        )
        # look for and wait for the "TaskForNightlyCVSACycle <region>" task to complete
        copy2cloud_task_id = BackupSteps.find_and_wait_for_copy2cloud(
            context=context,
            customer_id=csp_account.customerId,
            account_id=csp_account.id,
            account_name=csp_account.name,
            region=region,
        )
        logger.info(f"copy2cloud task: {copy2cloud_task_id} is complete")

    logger.info(f"Wait for {TimeoutManager.delete_backup_timeout} to delete the k8s application backup id {backup_id}")
    task_status = tasks.wait_for_task(task_id=task_id, user=context.user, timeout=TimeoutManager.delete_backup_timeout)

    if task_status.lower() != TaskStatus.success.value.lower():
        logger.error(
            f"k8s application backup ID: {backup_id} deletion failed. TaskID:{task_id} TaskStatus:{task_status}"
        )
        return False

    logger.info(f"k8s application backup ID: {backup_id} is deleted successfully")
    return True


def get_k8s_app_backup_state_and_status(
    context: Context,
    backup_id: str,
    csp_k8s_application_id: str,
    backup_state: BackupState,
    backup_status: CSPK8sBackupStatus,
) -> dict:
    """Get the k8s namespaced application state and status

    Args:
        context (Context): The test Context
        csp_k8s_application_id (str): csp k8s namespaced application
        backup_id (str): k8s namespaced application backup id
        backup_state (BackupState): k8s app Backup state
        backup_status (CSPK8sBackupStatus): k8s app backup status

    """
    logger.info(f"Verify application backup with id {backup_id} state and status are as expected")
    backup_obj: CSPK8sAppBackupInfoModel = context.eks_data_protection_manager.get_csp_k8s_app_backup_details(
        csp_k8s_application_id=csp_k8s_application_id, backup_id=backup_id
    )
    assert (
        backup_state.value == backup_obj.state
    ), f"application backup with id {backup_id} has incorrect state: {backup_obj.state}"
    logger.info(f"application backup with id {backup_id} is in expected state: {backup_obj.state}")
    assert (
        backup_status.value == backup_obj.status
    ), f"application backup with id {backup_id} has incorrect status: {backup_obj.status}"
    logger.info(f"application backup with id {backup_id} is in expected status: {backup_obj.state}")


def get_csp_k8s_app_backup_id(
    context: Context,
    csp_k8s_application_id: str,
) -> str:
    """Get the k8s namespaced application backup id

    Args:
        context (Context): The test Context
        csp_k8s_application_id (str): csp k8s namespaced application

    Returns:
        str: k8s application backup id
    """
    k8s_app_backup_list: CSPK8sAppBackupListModel = context.eks_data_protection_manager.get_csp_k8s_app_backups(
        csp_k8s_application_id=csp_k8s_application_id,
        sort="createdAt",
    )
    if k8s_app_backup_list:
        k8s_app_backup: CSPK8sAppBackupInfoModel = k8s_app_backup_list.items[0]
        return k8s_app_backup.id
    else:
        logger.warning(f"EKS application {csp_k8s_application_id} does not have any backups")


def validate_csp_k8s_app_backup_count(context: Context, csp_k8s_application_id: str, count: int) -> str:
    """Validates given k8s namespaced application backup count as input

    Args:
        context (Context): The test Context
        csp_k8s_application_id (str): csp k8s namespaced application
        count (int): number of backups expecting for the namespaced application

    Returns:
        NA
    """
    k8s_app_backup_total_count: CSPK8sAppBackupListModel = context.eks_data_protection_manager.get_csp_k8s_app_backups(
        csp_k8s_application_id=csp_k8s_application_id
    )
    assert (
        k8s_app_backup_total_count.total == count
    ), f"Expected backups: {count} but Actual Backups {k8s_app_backup_total_count}"


def validate_csp_k8s_app_has_backup(context: Context, csp_k8s_application_id: str):
    """Validates if app has at least one backup

    Args:
        context (Context): context object
        csp_k8s_application_id (str): csp k8s namespaced application
    """
    k8s_app_backup_total_count: CSPK8sAppBackupListModel = context.eks_data_protection_manager.get_csp_k8s_app_backups(
        csp_k8s_application_id=csp_k8s_application_id
    )
    assert (
        k8s_app_backup_total_count.total > 0
    ), f"Expected more than one backup for this app ID: {csp_k8s_application_id}, but got {k8s_app_backup_total_count.total}"


def delete_all_native_cloud_backups(
    context: Context,
    csp_account: CSPAccountModel,
    region: str,
    csp_k8s_application_id: str,
):
    delete_all_k8s_apps_backups(
        context=context,
        csp_k8s_application_ids=[csp_k8s_application_id],
        csp_account=csp_account,
        region=region,
    )
    backup_total_count_after_delete = context.eks_data_protection_manager.get_csp_k8s_app_backups(
        csp_k8s_application_id=csp_k8s_application_id
    ).total
    assert (
        not backup_total_count_after_delete
    ), f"All backups should be deleted, but we have {backup_total_count_after_delete} remaining."


def verify_eks_suspended_account_modify_expire_time(context: Context, app_id: str, backup_type: CSPBackupType):
    backup_filter = f"backupType eq {backup_type.value}"
    k8s_app_backup_list: CSPK8sAppBackupListModel = context.eks_data_protection_manager.get_csp_k8s_app_backups(
        csp_k8s_application_id=app_id, filter=backup_filter
    )
    assert k8s_app_backup_list.total, f"Expected at least 1 {backup_type.value}, but found 0 instead."
    logger.info(f"Successfully filter the backup type {backup_type.value} to update expiry time")

    # grab the 1st backup
    backup = k8s_app_backup_list.items[0]
    current_expires_at = backup.expires_at
    logger.info(f"Current expires at = {current_expires_at}")

    # modify the last 3 characters
    new_expires_at = current_expires_at[:-3] + "02Z"
    logger.info(f"New expires at = {new_expires_at}")

    backup_patch = PatchCSPK8sAppBackup(expires_at=new_expires_at)

    # we expect the task to error-out for a suspended account
    task_id = context.eks_data_protection_manager.update_csp_k8s_app_backup(
        csp_k8s_application_id=app_id,
        backup_id=backup.id,
        patch_backup_payload=backup_patch,
    )
    logger.info(f"Waiting for taskID: {task_id}")
    tasks.wait_for_task(task_id=task_id, user=context.user, timeout=TimeoutManager.standard_task_timeout)

    # Get the task object
    task = tasks.get_task_object(user=context.user, task_id=task_id)

    assert task.state == TaskStatus.failed.value
    assert task.error.error == AtlasErrorMessages.SUSPENDED_MODIFY_EXPIRE_ERROR_MESSAGE
    logger.info(f"Task 'failed' state with error message: {AtlasErrorMessages.SUSPENDED_MODIFY_EXPIRE_ERROR_MESSAGE}")


def perform_and_verify_native_backup(
    context: Context,
    aws_account_name,
    csp_k8s_application_id,
    app_name,
    val_native_backup_id=True,
):
    """This method perform native backup and verify backup_id is available or not

    Args:
        context (Context): The test Context.
        csp_k8s_application_id (str): csp k8s namespaced application id.
        aws_account_name (str): aws account name where app is available.
        app_name (str): app name to take the backup.
        val_native_backup_id (bool): Check to indicate a positive or negative native backup workflow
    """
    csp_account: CSPAccountModel = CAMSteps.get_csp_account_by_csp_name(context, account_name=aws_account_name)
    assert csp_account is not None, f"Failed to retrieve csp_account: {context.aws_eks_account_name}"
    native_backup_id = None
    native_backup_id = run_k8s_app_native_backup(
        context=context,
        csp_k8s_application_id=csp_k8s_application_id,
        app_name=app_name,
        csp_account=csp_account,
    )
    if val_native_backup_id:
        assert native_backup_id, "Run native backup on k8s namespace failed."
        logger.info(f"Native backup of k8 application {app_name} and id {csp_k8s_application_id} created successfully")
    else:
        assert not native_backup_id, "Run native backup succeeded which is unexpected"
        logger.info(f"Native backup of k8 application {app_name} and id {csp_k8s_application_id} failed as expected.")
    return native_backup_id


def perform_delete_native_backup_and_verify(context: Context, csp_k8s_application_id, backup_id):
    """this method performs delete native backup and verifies

    Args:
        context (Context): Conetxt Object
        csp_k8s_application_id (str): CSP k8 app ID in which the backup needs to be deleted.
        backup_id (str): native backup IT to delete.
    """
    logger.info("Started performing delete native backup task..")
    csp_account: CSPAccountModel = CAMSteps.get_csp_account_by_csp_name(context, context.aws_eks_account_name)
    backup_delete_one = delete_k8s_app_backup(
        context=context,
        csp_k8s_application_id=csp_k8s_application_id,
        backup_id=backup_id,
        csp_account=csp_account,
        region=context.eks_cluster_aws_region,
    )
    assert backup_delete_one, f"Delete native backup ID {backup_id} on k8s app failed."
    logger.info("Successfully verified native backup delted completed...")


def verify_backup_task_and_validate_backup(
    context: Context,
    eks_cluster_name: str,
    eks_cluster_aws_region: str,
    app_name: str,
    backup_task_id: str,
) -> str:
    """Run the Native Backup job, associated with the given k8s application id.
    Args:
        context (Context): The test Context.
        eks_cluster_name (str): EKS cluster name
        eks_cluster_aws_region (str): EKS cluster region
        app_name (str): Backing up app name
        backup_task (str): Backup task id
    Return:
        `backup_id (str) Returns backup ID
    """
    csp_k8s_application_id = get_eks_k8s_cluster_app_by_name(
        context,
        eks_cluster_name,
        eks_cluster_aws_region,
        app_name,
    )
    # wait for backup to finish
    task_status = tasks.wait_for_task(
        task_id=backup_task_id,
        user=context.user,
        timeout=TimeoutManager.create_backup_timeout,
    )
    if task_status.lower() != TaskStatus.success.value.lower():
        logger.error(f"Failed to complete backup job for backup type: {BackupType.NATIVE_BACKUP}")
        return None
    logger.info(f"Native backup job ran successfully for backup type: {BackupType.NATIVE_BACKUP}")
    backup_id = get_csp_k8s_app_backup_id(context, csp_k8s_application_id)
    #  Verify Backup state an status
    get_k8s_app_backup_state_and_status(
        context, backup_id, csp_k8s_application_id, BackupState.OK, CSPK8sBackupStatus.OK
    )
    return backup_id


def validate_backup_task_status(task_name, expected_task_status, context, customer_id, app_name):
    """Validates the task status.
    Args:
        task_name (str): task_name to be validated.
        expected_task_status (str): expected task status.
        context (Context): The test context
        customer_id (str): csp account customer id.
        app_name (str): name of app

    """
    # Get the taskID of the active backup job
    protection_jobs_running = tasks.get_tasks_by_name_and_customer_account(
        user=context.user,
        task_name=task_name,
        customer_id=customer_id,
    )
    assert protection_jobs_running, f"No running protection jobs found for {app_name}"

    last_protection_job_running_id = protection_jobs_running[0].id

    task_status = tasks.wait_for_task(
        task_id=last_protection_job_running_id,
        user=context.user,
        timeout=TimeoutManager.create_backup_timeout,
    )

    assert (
        task_status.lower() == expected_task_status.value.lower()
    ), f"Expected task to fail, but had status {task_status.lower()}"
