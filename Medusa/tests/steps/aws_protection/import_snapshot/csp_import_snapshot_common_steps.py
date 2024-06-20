"""
This module contains functions related to importing and validating AMI and Snapshots from AWS
"""

import logging
import re
import requests

from lib.common.enums.task_status import TaskStatus
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import CSPBackupModel

from lib.dscc.backup_recovery.aws_protection.common.models.import_aws_assets import ImportAWSAssetsByRegion

from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_payload_model import (
    PostImportSnapshotModel,
)

from lib.dscc.tasks.payload.task import LogMessage

from tests.e2e.aws_protection.context import Context
import tests.steps.aws_protection.backup_steps as BS

from tests.steps.tasks import tasks

from utils.timeout_manager import TimeoutManager

IMPORT_SNAPSHOT_WORKFLOW: str = "CSPImportSnapshotsParentWorkflow"
IMPORT_AMI_WORKFLOW: str = "CSPImportImagesParentWorkflow"

FOUND: str = "Found"
SNAPSHOTS_TO_IMPORT: str = "Cloud Service Provider snapshot(s) to import"
IMAGES_TO_IMPORT: str = "Cloud Service Provider AMI(s) to import"

IMPORTED_SNAPSHOT: str = "Imported snapshot"
IMPORTED_AMI: str = "Imported AMI"

logger = logging.getLogger()


def import_snapshots_and_amis(
    context: Context,
    csp_account_id: str,
    post_import_snapshot: PostImportSnapshotModel,
    expected_status_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
) -> str:
    """Imports AWS snapshots and AMIs into provided DSCC account

    Args:
        context (Context): Context object
        csp_account_id (str): AWS account ID registered in DSCC
        post_import_snapshot (PostImportSnapshotModel): PostImportSnapshotModel object
        expected_status_code (int, optional): Expected Task Status Code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Waits for task to complete if set to 'True'. Defaults to True.

    Returns:
        str: The Task ID of the import operation
    """
    task_id = context.data_protection_manager.import_account_snapshots_and_amis(
        csp_account_id=csp_account_id,
        post_import_snapshot=post_import_snapshot,
        expected_status_code=expected_status_code,
    )
    logger.info(f"Import Backup task id = {task_id}")
    if wait_for_task:
        logger.info(
            f"Waiting for import backup for account {csp_account_id} with parameters {post_import_snapshot} to complete"
        )
        import_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.standard_task_timeout,
        )
        assert (
            import_task_status.upper() == TaskStatus.success.value
        ), f"Account {csp_account_id} import backup failure, task_status={import_task_status}"

    return task_id


def validate_csp_volume_imported_snapshots_properties(
    context: Context,
    csp_volume_id: str,
    csp_backup_id: str,
    expected_created_at_time: str,
    expected_expires_at_time: str,
    expected_point_in_time: str,
):
    """Validate the expected "time" properties of the imported volume Snapshot

    Args:
        context (Context): The test Context
        csp_volume_id (str): CSP Volume ID
        csp_backup_id (str): CSP Backup ID
        expected_created_at_time (str): The expected "created at" time
        expected_expires_at_time (str): The expected "expires at" time
        expected_point_in_time (str): The expected "point in" time
    """
    logger.info(f"Fetching backup {csp_backup_id} for CSP Volume {csp_volume_id}")
    csp_backup: CSPBackupModel = BS.get_csp_volume_backup_by_id(
        context=context,
        volume_id=csp_volume_id,
        backup_id=csp_backup_id,
    )
    logger.info(f"Backup for CSP Volume {csp_volume_id} is {csp_backup}")

    assert (
        expected_created_at_time == csp_backup.created_at
    ), f"Expected created_at time is {expected_created_at_time} and actual is {csp_backup.created_at}"
    assert (
        expected_expires_at_time == csp_backup.expires_at
    ), f"Expected expires_at time is {expected_expires_at_time} and actual is {csp_backup.expires_at}"
    assert (
        expected_point_in_time == csp_backup.point_in_time
    ), f"Expected point_in_time is {expected_point_in_time} and actual is {csp_backup.point_in_time}"


def validate_csp_instance_imported_ami_properties(
    context: Context,
    csp_machine_instance_id: str,
    csp_backup_id: str,
    expected_created_at_time: str,
    expected_expires_at_time: str,
    expected_point_in_time: str,
):
    """Validate the expected "time" properties of the imported machine instance AMI

    Args:
        context (Context): The test Context
        csp_machine_instance_id (str): CSP Machine Instance ID
        csp_backup_id (str): CSP Backup ID
        expected_created_at_time (str): The expected "created at" time
        expected_expires_at_time (str): The expected "expires at" time
        expected_point_in_time (str): The expected "point in" time
    """
    logger.info(f"Fetching backup {csp_backup_id} for CSP Machine Instance {csp_machine_instance_id}")
    csp_backup: CSPBackupModel = BS.get_csp_machine_instance_backup_by_id(context=context, backup_id=csp_backup_id)
    logger.info(f"Backup for CSP Machine Instance {csp_machine_instance_id} is {csp_backup}")

    assert (
        expected_created_at_time == csp_backup.created_at
    ), f"Expected created_at time is {expected_created_at_time} and actual is {csp_backup.created_at}"
    assert (
        expected_expires_at_time == csp_backup.expires_at
    ), f"Expected expires_at time is {expected_expires_at_time} and actual is {csp_backup.expires_at}"
    assert (
        expected_point_in_time == csp_backup.point_in_time
    ), f"Expected point_in_time is {expected_point_in_time} and actual is {csp_backup.point_in_time}"


# NOTE: Keeping validate_snapshot_count_in_task_logs() and validate_ami_count_in_task_logs() wrapper methods separate for
#       simplicity. Once we have visibility into AMI import, we can modify these methods


def validate_snapshot_count_in_task_logs(
    context: Context,
    parent_task_id: str,
    expected_snapshots: list[ImportAWSAssetsByRegion],
):
    """Validate the number of expected Snapshots imported per Region

    Args:
        context (Context): The test Context
        parent_task_id (str): Task ID of the import operation
        expected_snapshots (list[ImportAWSAssetsByRegion]): A list of AWS Regions and the expected count and names of the AWS asset
    """
    _validate_asset_count_in_task_logs(
        context=context,
        parent_task_id=parent_task_id,
        expected_assets=expected_snapshots,
        child_task_name=IMPORT_SNAPSHOT_WORKFLOW,
        imported_assets_log_entry=IMPORTED_SNAPSHOT,
    )


def validate_ami_count_in_task_logs(
    context: Context,
    parent_task_id: str,
    expected_amis: list[ImportAWSAssetsByRegion],
):
    """Validate the number of expected AMIs imported per Region

    Args:
        context (Context): The test Context
        parent_task_id (str): Task ID of the import operation
        expected_amis (list[ImportAWSAssetsByRegion]): A list of AWS Regions and the expected count and names of the AWS asset
    """
    _validate_asset_count_in_task_logs(
        context=context,
        parent_task_id=parent_task_id,
        expected_assets=expected_amis,
        child_task_name=IMPORT_AMI_WORKFLOW,
        imported_assets_log_entry=IMPORTED_AMI,
    )


def _validate_asset_count_in_task_logs(
    context: Context,
    parent_task_id: str,
    expected_assets: list[ImportAWSAssetsByRegion],
    child_task_name: str,
    imported_assets_log_entry: str,
):
    """Retrieves child tasks from given parent_task_id and validates imported asset count by region in the log messages

    Args:
        context (Context): Context object
        parent_task_id (str): Parent Task ID for CSPImportBackupsWorkflow
        expected_assets (list[ImportAWSAssetsByRegion]): A list of AWS Regions and the expected count and names of the AWS asset
        child_task_name (str): CSPImportSnapshotsParentWorkflow(Snapshots) | CSPImportImagesParentWorkflow(AMIs)
        imported_assets_log_entry (str): Either of the constants IMPORTED_SNAPSHOT or IMPORTED_AMI, to use in searching for asset names
    """
    parent_task = tasks.get_task_object(user=context.user, task_id=parent_task_id)
    logger.info(f"Parent Task: {parent_task}")

    # Hierarchy:
    # Parent Task -> CSPImportBackupsWorkflow (Import Backups)
    #     Child Task -> CSPImportSnapshotsParentWorkflow (Import Volume Snapshots Parent Workflow)
    #         Child Tasks [list] -> CSPImportSnapshotsChildWorkflow [For each region] (Import Volume Snapshots for Region: us-west-2)
    #             LogMessages

    # get the "child_tasks" for the given "parent_task"
    parent_child_tasks = tasks.get_child_tasks_from_task(task=parent_task, user=context.user)

    for child_import_task in parent_child_tasks:
        # look for the child_task with "child_task_name"
        # NOTE: "child_import_task" could be a Task or an ObjectNameResourceType. Both have a "name" field
        if child_import_task.name == child_task_name:
            # we found the child task (AMI or Snapshot)
            # NOTE: "child_import_task" could be a Task or an ObjectNameResourceType.
            # Task.resource_uri  or  ObjectNameResourceType.resourceUri
            resource_uri = tasks.get_resource_uri_from_child_task(child_import_task)

            import_task = tasks.get_task_object(
                user=context.user,
                task_id=resource_uri.split("/")[-1],
            )
            logger.info(f"Import Task: {import_task}")
            logger.info("Getting Import Task child tasks for each region to validate imported asset count")

            # get the "child_tasks" for the given "import_task"
            import_child_tasks = tasks.get_child_tasks_from_task(task=import_task, user=context.user)

            for import_region_child_task in import_child_tasks:
                # NOTE: "import_region_child_task" could be a Task or an ObjectNameResourceType.
                # Task.resource_uri  or  ObjectNameResourceType.resourceUri
                import_resource_uri = tasks.get_resource_uri_from_child_task(import_region_child_task)

                region_child_task = tasks.get_task_object(
                    user=context.user,
                    task_id=import_resource_uri.split("/")[-1],
                )
                logger.info(f"Region Child Task: {region_child_task}")

                # "displayName": "Import Volume Snapshots for Region: eu-west-1"
                region_name = region_child_task.display_name.strip().split(":")[-1].strip()
                logger.info(f"Child Task for region: {region_name}")

                # if "region_name" is found in provided "expected_assets" list, continue.
                # otherwise move onto next region
                region_assets = None
                for item in expected_assets:
                    if item.region.value == region_name:
                        region_assets = item
                        break

                if not region_assets:
                    continue

                logger.info(f"Validating expected assets for this region: {region_name}")
                # get number from log messages, such as: "Found 1 Cloud Service Provider snapshot(s) to import"
                # validate count
                _validate_import_count(
                    expected_count=region_assets.num_expected, log_messages=region_child_task.log_messages
                )

                # get all AMI/Snapshot names imported
                asset_names = _get_imported_asset_names(
                    log_entry=imported_assets_log_entry, log_messages=region_child_task.log_messages
                )
                logger.info(f"Found asset names: {asset_names}")

                # compare results with data
                for name in region_assets.asset_names:
                    assert name in asset_names, f"Did not find expected asset name: {name}"


def _get_imported_asset_names(log_entry: str, log_messages: list[LogMessage]) -> list[str]:
    asset_names = []
    for log_message in log_messages:
        # "message": "Imported snapshot snap-0943b5a20ac0ccb5f successfully" or "Imported AMI ami-06a3aa36723837962 successfully"
        if log_entry in log_message.message:
            asset_names.append(log_message.message.split()[2])
    return asset_names


def _validate_import_count(expected_count: int, log_messages: list[LogMessage]):
    message = None
    for log_message in log_messages:
        # "message": "Found 2 Cloud Service Provider snapshot(s) to import"
        if FOUND in log_message.message and (SNAPSHOTS_TO_IMPORT or IMAGES_TO_IMPORT in log_message.message):
            message = log_message.message
            break
    assert message, "Did not find any assets imported in the logs"
    logger.info(f"Found message: {message}")

    pattern_match = re.findall(r"\d+", message)
    count = list(map(int, pattern_match))[0]
    logger.info(f"Number of imported assets is: {count}")

    # a) let's assert that there are at least "expected_count" in the logs.
    assert count >= expected_count, f"Count in logs={count}, expected at least count={expected_count}"
    logger.info(f"Count in logs {count} satisfies expected count {expected_count}")
