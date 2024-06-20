"""
This module contains MS365 Outlook restore workflow functions related to indexing backup, restoring and validating emails, contacts, events and tasks.
"""

import logging
import requests
from waiting import wait, TimeoutExpired

from lib.common.enums.task_status import TaskStatus
from lib.common.enums.backup_type import BackupType
from lib.common.enums.index_status import IndexStatus
from lib.dscc.backup_recovery.ms365_protection.common.enums.backup_task import MS365BackupTask
from tests.steps.tasks import tasks
from tests.e2e.ms365_protection.ms_office_context import MSOfficeContext
from lib.platform.ms365.ms_outlook_manager import MSOutlookManager
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.payload.restore_ms_contacts import (
    RestoreMS365Contacts,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.payload.restore_ms_emails import (
    RestoreMS365Emails,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.payload.restore_ms_tasks import (
    RestoreMS365Tasks,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.payload.restore_ms_events import (
    RestoreMS365Events,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.common import RestoreItem
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.csp_ms_backups import (
    MS365Backup,
    MS365BackupsList,
)
from utils.timeout_manager import TimeoutManager
from tests.steps.ms365_protection.ms_inventory_manager_steps import (
    get_ms365_user_by_email,
)
import tests.steps.aws_protection.backup_steps as BackupSteps

logger = logging.getLogger()


def index_ms365_backup(
    context: MSOfficeContext,
    csp_backup_id: str,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    expected_task_status: TaskStatus = TaskStatus.success,
) -> str:
    """Start/Initiate indexing on given backup and waits for index task to complete

    Args:
        context (MSOfficeContext): MSOfficeContext object
        csp_backup_id (str): CSP Backup ID which needs to be indexed
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.
        expected_task_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.

    Returns:
        task_id (str): Index task_id
    """
    logger.info(f"Indexing the backup {csp_backup_id}")
    task_id = context.data_protection_manager.initiate_ms365_backup_index_by_id(
        csp_ms365_backup_id=csp_backup_id, expected_status_code=response_code
    )
    logger.info(f"Task ID for index backup is {task_id}")

    if wait_for_task:
        logger.info(f"Waiting for indexing of backup {csp_backup_id} to complete")
        restore_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.index_backup_timeout,
        )

        assert restore_task_status.upper() == expected_task_status.value, f"Index task on backup {csp_backup_id} failed"

    return task_id


def restore_emails_from_ms365_backup(
    context: MSOfficeContext,
    csp_backup_id: str,
    destination_user_id: str,
    emails_identifier: list,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    expected_task_status: TaskStatus = TaskStatus.success,
) -> str:
    """Restores provided emails from given backup and waits for restore task to complete

    Args:
        context (MSOfficeContext): MSOfficeContext object
        csp_backup_id (str): CSP Backup ID from which emails need to be restored
        destination_user_id (str): Destination User ID where restore action have to perform
        emails_identifier (list): list of emails identifiers to restore
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.
        expected_task_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.

    Returns:
        task_id (str): Restore task_id
    """
    logger.info(f"Restoring emails from the backup {csp_backup_id}")
    item_id_list = []
    for email_identifier in emails_identifier:
        identifier = RestoreItem(item_id=email_identifier)
        item_id_list.append(identifier)
    restore_emails_info = RestoreMS365Emails(destination_user_id=destination_user_id, emails=item_id_list)
    task_id = context.data_protection_manager.restore_ms365_emails_from_backup(
        csp_ms365_backup_id=csp_backup_id,
        restore_emails_payload=restore_emails_info,
        expected_status_code=response_code,
    )
    logger.info(f"Task ID for restore is {task_id}")

    if wait_for_task:
        logger.info(f"Waiting for restore of emails from backup {csp_backup_id} to complete")
        restore_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.ms365_restore_timeout,
        )

        assert (
            restore_task_status.upper() == expected_task_status.value
        ), f"Restore emails request from backup {csp_backup_id} failed"
        logger.info("MS365 Restore Task is successful")

    return task_id


def restore_contacts_from_ms365_backup(
    context: MSOfficeContext,
    csp_backup_id: str,
    destination_user_id: str,
    contacts_identifiers: list,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    expected_task_status: TaskStatus = TaskStatus.success,
) -> str:
    """Restores provided contacts from given backup and waits for restore task to complete

    Args:
        context (MSOfficeContext): MSOfficeContext object
        csp_backup_id (str): CSP Backup ID from which contacts need to be restored
        destination_user_id (str): Destination User ID where restore action have to perform
        contacts_identifiers (list): list of contact identifiers to restore
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.
        expected_task_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.

    Returns:
        task_id (str): Restore task_id
    """
    logger.info(f"Restoring Contacts from the backup {csp_backup_id}")
    item_id_list = []
    for contact_identifier in contacts_identifiers:
        identifier = RestoreItem(item_id=contact_identifier)
        item_id_list.append(identifier)
    restore_contacts_info = RestoreMS365Contacts(destination_user_id=destination_user_id, contacts=item_id_list)
    task_id = context.data_protection_manager.restore_ms365_contacts_from_backup(
        csp_ms365_backup_id=csp_backup_id,
        restore_contacts_payload=restore_contacts_info,
        expected_status_code=response_code,
    )
    logger.info(f"Task ID for contacts restore is {task_id}")

    if wait_for_task:
        logger.info(f"Waiting for restore of contacts from backup {csp_backup_id} to complete")
        restore_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.ms365_restore_timeout,
        )

        assert (
            restore_task_status.upper() == expected_task_status.value
        ), f"Restore contacts request from backup {csp_backup_id} failed"
        logger.info("MS365 Restore Contacts Task is successful")
    return task_id


def restore_tasks_from_ms365_backup(
    context: MSOfficeContext,
    csp_backup_id: str,
    destination_user_id: str,
    tasks_identifiers: list,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    expected_task_status: TaskStatus = TaskStatus.success,
) -> str:
    """Restores provided tasks from given backup and waits for restore task to complete

    Args:
        context (MSOfficeContext): MSOfficeContext object
        csp_backup_id (str): CSP Backup ID from which tasks need to be restored
        destination_user_id (str): Destination User ID where restore action have to perform
        tasks_identifiers (list): list of tasks identifiers to restore
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.
        expected_task_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.

    Returns:
        task_id (str): Restore task_id
    """
    logger.info(f"Restoring tasks from the backup {csp_backup_id}")
    item_id_list = []
    for task_identifier in tasks_identifiers:
        identifier = RestoreItem(item_id=task_identifier)
        item_id_list.append(identifier)
    restore_tasks_info = RestoreMS365Tasks(destination_user_id=destination_user_id, tasks=item_id_list)
    task_id = context.data_protection_manager.restore_ms365_tasks_from_backup(
        csp_ms365_backup_id=csp_backup_id, restore_tasks_payload=restore_tasks_info, expected_status_code=response_code
    )
    logger.info(f"Task ID for tasks restore is {task_id}")

    if wait_for_task:
        logger.info(f"Waiting for restore of tasks from backup {csp_backup_id} to complete")
        restore_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.ms365_restore_timeout,
        )

        assert (
            restore_task_status.upper() == expected_task_status.value
        ), f"Restore tasks request from backup {csp_backup_id} failed"

    return task_id


def restore_events_from_ms365_backup(
    context: MSOfficeContext,
    csp_backup_id: str,
    destination_user_id: str,
    events_identifiers: list,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    expected_task_status: TaskStatus = TaskStatus.success,
) -> str:
    """Restores provided events from given backup and waits for restore task to complete

    Args:
        context (MSOfficeContext): MSOfficeContext object
        csp_backup_id (str): CSP Backup ID from which events need to be restored
        destination_user_id (str): Destination User ID where restore action have to perform
        events_identifiers (list): list of events identifiers to restore
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.
        expected_task_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.

    Returns:
        task_id (str): Restore task_id
    """
    logger.info(f"Restoring events from the backup {csp_backup_id}")
    item_id_list = []
    for event_identifier in events_identifiers:
        identifier = RestoreItem(item_id=event_identifier)
        item_id_list.append(identifier)
    restore_events_info = RestoreMS365Events(destination_user_id=destination_user_id, events=item_id_list)
    task_id = context.data_protection_manager.restore_ms365_events_from_backup(
        csp_ms365_backup_id=csp_backup_id,
        restore_events_payload=restore_events_info,
        expected_status_code=response_code,
    )
    logger.info(f"Task ID for events restore is {task_id}")

    if wait_for_task:
        logger.info(f"Waiting for restore of events from backup {csp_backup_id} to complete")
        restore_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.ms365_restore_timeout,
        )

        assert (
            restore_task_status.upper() == expected_task_status.value
        ), f"Restore events request from backup {csp_backup_id} failed"

    return task_id


def verify_checksums_for_source_and_restored_emails(
    context: MSOfficeContext,
    csp_source_email_identifier: str,
    csp_restored_email_identifier: str,
    user_id: str,
    ms_outlook_manager: MSOutlookManager = None,
) -> bool:
    """Returns True or False based on validation of restored email identifier w.r.t source email identifier.
    NOTE: Need to get more information on this once we have more visibility

    Args:
        context (MSOfficeContext): MSOfficeContext
        csp_source_email_identifier (str): Source email identifier which was backed-up.
        csp_restored_email_identifier (str): Restored email identifier which was restored from backup.
        user_id: User identifier of user whose mail box is being used.
        ms_outlook_managter: MSOutlookManager object for user whose mailbox is to be used, Defaults to None
    Returns:
        bool: True if source and restored email match
    """
    if not ms_outlook_manager:
        ms_outlook_manager = context.ms_one_outlook_manager
    src_chksum = ms_outlook_manager.get_hash_of_message(user_id=user_id, item_id=csp_source_email_identifier)
    restored_chksum = ms_outlook_manager.get_hash_of_message(user_id=user_id, item_id=csp_restored_email_identifier)
    assert (
        src_chksum == restored_chksum
    ), f"Source email chksum is {src_chksum} and restored email chksum is {restored_chksum}, and it does not match"
    logger.info(
        f"Source email chksum is {src_chksum} and restored email chksum is {restored_chksum}, it matches as expected"
    )


def verify_checksum_for_source_and_restored_items(
    context: MSOfficeContext,
    source_identifiers: list,
    source_folder_id: str,
    restored_identifiers: str,
    restored_folder_id: str,
    user_id: str,
    item_type: str,
    ms_outlook_manager: MSOutlookManager = None,
):
    """This step method will get checksum of the provided items and Verify checksums on both source and restored items.

    Args:
        context (MSOfficeContext): MSOfficeContext
        source_identifiers (list): Source item identifier which was backed-up
        source_folder_id (str): Source folder identifier which was backed-up
        restored_identifiers (str): Restored item identifier which was restored from backup
        restored_folder_id (str): Restored folder identifier which was restored from backup
        user_id (str): User identifier of user whose mail box is being used
        item_type (str): item type to get the checksum ex: contacts, events and tasks.
        ms_outlook_managter: MSOutlookManager object for user whose mailbox is to be used, Defaults to None
    """
    src_chksum = None
    restored_chksum = None
    if not ms_outlook_manager:
        ms_outlook_manager = context.ms_one_outlook_manager
    if item_type == "contacts":
        src_chksum = ms_outlook_manager.get_hash_of_contacts(
            user_id=user_id, item_ids=source_identifiers, folder_id=source_folder_id
        )
        restored_chksum = ms_outlook_manager.get_hash_of_contacts(
            user_id=user_id, item_ids=restored_identifiers, folder_id=restored_folder_id
        )
    elif item_type == "events":
        src_chksum = ms_outlook_manager.get_hash_of_events(
            user_id=user_id, item_ids=source_identifiers, folder_id=source_folder_id
        )
        restored_chksum = ms_outlook_manager.get_hash_of_events(
            user_id=user_id, item_ids=restored_identifiers, folder_id=restored_folder_id
        )
    elif item_type == "tasks":
        src_chksum = ms_outlook_manager.get_hash_of_tasks(
            user_id=user_id, item_ids=source_identifiers, folder_id=source_folder_id
        )
        restored_chksum = ms_outlook_manager.get_hash_of_tasks(
            user_id=user_id, item_ids=restored_identifiers, folder_id=restored_folder_id
        )
    else:
        logger.warning("item_type parameter is not provided. please provide one to validate checksum")
    assert (
        src_chksum == restored_chksum
    ), f"Source item chksum is {src_chksum} and restored item chksum is {restored_chksum}, and it does not match"
    logger.info(
        f"Source item chksum is {src_chksum} and restored item chksum is {restored_chksum}, it matches as expected"
    )


# TODO
def validate_restored_event(
    context: MSOfficeContext,
    csp_source_event_identifier: str,
    csp_restored_event_identifier: str,
) -> bool:
    """Returns True or False based on validation of restored event identifier w.r.t source event identifier.
    NOTE: Need to get more information on this once we have more visibility

    Args:
        context (MSOfficeContext): MSOfficeContext
        csp_source_event_identifier (str): Source event identifier which was backed-up.
        csp_restored_event_identifier (str): Restored event identifier which was restored from backup.

    Returns:
        bool: True if source and restored event match
    """
    pass


# TODO
def validate_restored_contact(
    context: MSOfficeContext,
    csp_source_contact_identifier: str,
    csp_restored_contact_identifier: str,
) -> bool:
    """Returns True or False based on validation of restored contact identifier w.r.t source contact identifier.
    NOTE: Need to get more information on this once we have more visibility

    Args:
        context (MSOfficeContext): MSOfficeContext
        csp_source_contact_identifier (str): Source contact identifier which was backed-up.
        csp_restored_contact_identifier (str): Restored contact identifier which was restored from backup.

    Returns:
        bool: True if source and restored contact match
    """
    pass


# TODO
def validate_restored_task(
    context: MSOfficeContext,
    csp_source_task_identifier: str,
    csp_restored_task_identifier: str,
) -> bool:
    """Returns True or False based on validation of restored task identifier w.r.t source task identifier.
    NOTE: Need to get more information on this once we have more visibility

    Args:
        context (MSOfficeContext): MSOfficeContext
        csp_source_task_identifier (str): Source task identifier which was backed-up.
        csp_restored_task_identifier (str): Restored task identifier which was restored from backup.

    Returns:
        bool: True if source and restored task match
    """
    pass


def perform_ms365_cloud_backup(
    context: MSOfficeContext,
    ms365_asset_resource_uri: str,
    expected_status: TaskStatus = TaskStatus.success,
    wait_for_task_complete: bool = True,
    timeout_value: int = TimeoutManager.create_backup_timeout,
) -> str:
    """Run MS365 backup for ms365_asset and wait for spawned subtask "Triggered MS365 backup"

    Args:
        context (MSOfficeContext): MS365 Context Object
        ms365_asset_resource_uri (str): MS365 asset resource uri
        expected_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.
        wait_for_task_complete (bool, optional): If False, the function will not wait for the "trigger" task to complete. Defaults to True.
        timeout_value (int, optional): If user wants specific time out he can provide. Defaults to TimeoutManager.create_backup_timeout.

    Raises:
        e: TimeoutExpired exception will be raised if method does not find that task within the given time.

    Returns:
        str: Task ID of the "Trigger" Task
    """
    trigger_task_id: str = None
    logger.info(f"Performing MS365 cloud backup action on: {ms365_asset_resource_uri}")
    asset_id = ms365_asset_resource_uri.split("/")[-1]
    BackupSteps.run_backup_on_asset(
        context=context, asset_id=asset_id, backup_types=[BackupType.CLOUD_BACKUP], wait_for_task=True
    )
    logger.info("Initiated scheduled protection job task complete")
    try:
        logger.info(f"Looking for {MS365BackupTask.MS365_BACKUP_TITLE_PREFIX.value}  task")
        wait(
            lambda: tasks.get_tasks_by_name_and_resource(
                user=context.user,
                task_name=MS365BackupTask.MS365_BACKUP_TITLE_PREFIX.value,
                resource_uri=ms365_asset_resource_uri,
            ).total,
            timeout_seconds=10 * 60,
            sleep_seconds=10,
        )
        trigger_task_id = (
            tasks.get_tasks_by_name_and_resource(
                user=context.user,
                task_name=MS365BackupTask.MS365_BACKUP_TITLE_PREFIX.value,
                resource_uri=ms365_asset_resource_uri,
            )
            .items[0]
            .id
        )
        logger.info(f"{MS365BackupTask.MS365_BACKUP_TITLE_PREFIX.value} task is ready: {trigger_task_id}")
    except TimeoutExpired as e:
        logger.error(f"TimeoutExpired waiting for '{MS365BackupTask.MS365_BACKUP_TITLE_PREFIX.value}' task")
        raise e

    if wait_for_task_complete:
        logger.info(f"wait for the trigger task to complete with timeout: {timeout_value}")
        try:
            trigger_task_state: str = tasks.wait_for_task(
                task_id=trigger_task_id, user=context.user, timeout=timeout_value
            )
            assert (
                trigger_task_state.upper() == expected_status.value
            ), f"MS365 Backup Trigger Task State {trigger_task_state.upper()} does NOT equal expected Trigger Task State {expected_status.value}"
            logger.info(f"{MS365BackupTask.MS365_BACKUP_TITLE_PREFIX.value} task state: {trigger_task_state}")

        except TimeoutError:
            trigger_task = tasks.get_task_object(user=context.user, task_id=trigger_task_id)
            logger.error(f"Trigger Task contains {trigger_task.subtree_task_count} subtasks")
            raise Exception(f"MS365 Backup trigger task timed out, task_id: {trigger_task_id}")

    return trigger_task_id


def get_all_ms365_backups(ms_context: MSOfficeContext) -> list:
    """This method can be used to fetch all the ms365 backups and sorted by createdAt
    Args:
        ms_context (MSOfficeContext): MS365 Context Object
    Raises:
        Exception: Raises exception when there is no backups returns from API.
    Returns:
        list: returns list of backups available.
    """
    logger.info("Getting all the backup details...")
    all_backups = None
    try:
        all_backups: MS365BackupsList = ms_context.data_protection_manager.list_ms365_backups(sort="createdAt+desc")
        assert all_backups.count != 0, f"There are no backups available... actual count: {all_backups.count}"
        logger.info("successfully fetched all the available backups")
        return all_backups
    except KeyError:
        raise Exception(f"Failed to get all backups response from API {all_backups}")


def get_ms365_user_latest_backup_details(
    ms_context: MSOfficeContext,
    ms365_user_id: str,
) -> MS365Backup:
    """This method will fetch the latest backup details in available backups list.
    Args:
        ms_context (MSOfficeContext): MS365 context object
        ms365_user (str): MS365 user ID to filter the latest backup
    Returns:
        MS365Backup object: latest backup details of the ms365 user
    """
    logger.info("Fetching latest backup id from available backups list...")
    ms365_user_backup_list: MS365BackupsList = get_all_ms365_backups(ms_context)
    if ms365_user_backup_list.count > 0:
        ms365_user_backup: MS365Backup = next(
            filter(lambda item: item.asset_info.id == str(ms365_user_id), ms365_user_backup_list.items)
        )
        return ms365_user_backup
    else:
        logger.warning("There are no backups available at this moment")


def get_ms365_user_backup_details(ms_context: MSOfficeContext, backup_id: str) -> MS365Backup:
    """This method can be used for getting MS365 backup details for the provided backup ID
    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        backup_id (str): ID of backup which user would like to fetch its details
    Returns:
        MS365Backup type: if provided id available then it give backup details
    """
    logger.info(f"Getting backup details of id: {backup_id}")
    try:
        backup_details: MS365Backup = ms_context.data_protection_manager.get_ms365_backup_by_id(
            csp_ms365_backup_id=backup_id
        )
        assert (
            backup_details.id
        ), f"Failed to fetch backup details by id {backup_id} actual backup details: {backup_details}"
        return backup_details
    except KeyError:
        raise Exception(f"There is KeyError exception occurred while fetching ms365 backup by id {backup_details}")


def verify_backup_index_state(ms_context: MSOfficeContext, backup_id: str, expected_index_state: IndexStatus) -> None:
    """This method checks if the given backup ID is in expected Index state or not

    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        backup_id (str): Backup ID to check its index state
        expected_index_state (IndexStatus): User expected state
    """
    backup_details: MS365Backup = get_ms365_user_backup_details(ms_context, backup_id)
    assert (
        backup_details.index_state == expected_index_state.value
    ), f"Index Status for backup {backup_id} is not as Expected: {expected_index_state} Actual: {backup_details.index_state}"


def get_ms365_user_backup_count(ms_context: MSOfficeContext, ms365_user: str) -> int:
    """This method returns available backup counts for the given ms365 user
    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        ms365_user (str): ms365 user email id
    Returns:
        int: backup counts
    """
    logger.info(f"Getting backup count for the given ms365 user: {ms365_user}")
    ms365_user_details = get_ms365_user_by_email(ms_context, ms365_user)
    if ms365_user_details.backup_info != []:
        backup_count = ms365_user_details.backup_info[0].count
    else:
        logger.info("There are no backups available currently")
        backup_count = 0
    logger.info(f"Backup counts: {backup_count} for ms365 user: {ms365_user}")
    return backup_count


def validate_ms365_backup_count(backup_count_before: int, backup_count_after: int) -> None:
    """This method compares backup count after backup action is greater than backup count before for a MS365 resource.

    Args:
        backup_count_before (int): backup count before performing backup action
        backup_count_after (int): backup count after performing backup action
    """
    logger.info(f"backup count before performing backup action: {backup_count_before}")
    logger.info(f"backup count after performing backup action: {backup_count_after}")
    assert (
        backup_count_after > backup_count_before
    ), "Following the backup action, the expected increase in the backup count did not occur; it failed to increment."

    logger.info("Successfully validated MS365 backup count increased...")


def delete_ms365_backup(
    ms_context: MSOfficeContext,
    backup_id: str,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    expected_task_status: TaskStatus = TaskStatus.success,
):
    """
    This function is used to delete a particular backup.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object
        backup_id (str): ID of backup to be deleted.
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for delete task to complete if set to True. Defaults to True.
        expected_task_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.
    """
    task_id = ms_context.data_protection_manager.delete_ms365_backup_by_id(
        csp_ms365_backup_id=backup_id, expected_status_code=response_code
    )
    logger.info(f"Task ID for deletion of backup with ID:{backup_id} is :{task_id}")

    if wait_for_task:
        logger.info(f"Waiting for delete backup task with ID:{task_id} to complete")
        restore_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=ms_context.user,
            timeout=TimeoutManager.standard_task_timeout,
        )

        assert (
            restore_task_status.upper() == expected_task_status.value
        ), f"Delete backup task for backup ID:{backup_id} failed"


def delete_all_ms365_backups(
    ms_context: MSOfficeContext,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    expected_task_status: TaskStatus = TaskStatus.success,
):
    """
    This function is used to delete all available MS365 backups.

    Args:
        ms_context (MSOfficeContext): MS365 Context Object.
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for delete task to complete if set to True. Defaults to True.
        expected_task_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.
    Returns:
        None
    """
    backup_list: MS365BackupsList = get_all_ms365_backups(ms_context=ms_context)
    backup_ids = [backup.id for backup in backup_list.items]
    logger.info(f"Will call backup delete operation on list of backups:{backup_ids}")
    for backup_id in backup_ids:
        delete_ms365_backup(
            ms_context=ms_context,
            backup_id=backup_id,
            response_code=response_code,
            wait_for_task=wait_for_task,
            expected_task_status=expected_task_status,
        )
