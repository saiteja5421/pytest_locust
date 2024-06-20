import requests
from requests import codes
from json import dumps
from common import helpers
import logging
from tests.aws.config import Paths
from waiting import wait, TimeoutExpired
from lib.dscc.backup_recovery.tasks import task_helper
from lib.dscc.backup_recovery.tasks.task_helper import SubTaskDisplayName, TaskDisplayNames
from common.helpers import squid_is_retry_needed
from tenacity import retry, stop_after_attempt, wait_fixed
from common import common

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()

from utils.timeout_manager import TimeoutManager


def get_copy2cloud_task_name(account_id, customer_id, region, account_name):
    """Will for copy2cloud task name using input parameters

    Args:
        account_id (UUID): Account UUID
        customer_id (UUID): Customer UUID
        region (string): name of region where assets are created
        account_name (string): Name of user account

    Returns:
        string: Name of copy2cloud task
    """
    task_name = f"{TaskDisplayNames.COPY2CLOUD_DISPLAY_NAME.value} customer: {customer_id}, region: {region}, accountID: {account_id}, accountName: {account_name}"
    return task_name


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def start_cvsa(customer_id, account_id, region):
    """Will call copy2cloud test api to trigger copy to cloud action

    Args:
        customer_id (string): Customer ID
        account_id (string): Customer account ID
        region (string): AWS region where the copy2cloud has to be triggered for given account.
    """
    logger.debug(f"calling copy2cloud endpoint: customer_id: {customer_id}, account_id: {account_id}, region: {region}")
    payload = {"customerID": customer_id, "accountID": account_id, "cspRegion": region}
    url = f"{helpers.get_locust_host()}{Paths.COPY2CLOUD_API}"

    response = requests.request("POST", url, headers=headers.authentication_header, data=dumps(payload))
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    assert response.status_code == codes.ok, f"{response.status_code} == {codes.ok}, Response {response}"


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def wait_for_cloudbackup_completion(account_id, customer_id, region, account_name):
    """Wait for CVSA task for copying the backups to cloud to finish

    Args:
        account_id (UUID): customer account id
        customer_id (UUID): customer id
        region (string): region where assets are present
        account_name (string): customer account name

    Raises:
        e: TimeoutExpired
        e: TimeoutError
    """
    copy2cloud_task_name = get_copy2cloud_task_name(account_id, customer_id, region, account_name)
    copy2cloud_task_id: str = None
    try:
        copy2cloud_task_id = task_helper.get_tasks_by_name_and_customer_account(
            task_name=copy2cloud_task_name, customer_id=customer_id, account_id=account_id
        )[0].id
        logger.debug(f"copy2cloud task ready: {copy2cloud_task_id}")
    except TimeoutExpired as e:
        logger.error("TimeoutExpired waiting for 'copy2cloud' task")
        print("TimeoutExpired waiting for 'copy2cloud' task")
        raise e

    # wait for the task to complete
    try:
        copy2cloud_task_state: str = task_helper.wait_for_task(task_id=copy2cloud_task_id, timeout=900)
        logger.debug(f"copy2cloud task state: {copy2cloud_task_state} for copy2cloud_task_id {copy2cloud_task_id}")

    except TimeoutError as e:
        logger.error(f"copy2cloud task timeout. task_id: {copy2cloud_task_id}")
        print(f"copy2cloud task timeout. task_id: {copy2cloud_task_id}")
        raise e


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def wait_for_staging_backup_task(asset_id):
    """Wait for staging backup task for given asset to complete

    Args:
        asset_id (UUID/string): asset ID for which staging backup is to be completed

    Raises:
        e: TimeoutExpired

    Returns:
        string: triggered task for the staging backup
    """
    task_title = TaskDisplayNames.TRIGGER_CLOUD_BACKUP.value
    resource_uri = f"/api/v1/csp-machine-instances/{asset_id}"
    # wait a bit for asset_resource_uri "Trigger" task to appear
    trigger_task_id = None
    try:
        wait(
            lambda: task_helper.get_tasks_by_resource_and_name(task_name=task_title, resource_uri=resource_uri).total,
            timeout_seconds=20 * 60,
            sleep_seconds=10,
        )
        # get the task id
        trigger_task_id = (
            task_helper.get_tasks_by_resource_and_name(task_name=task_title, resource_uri=resource_uri).items[0].id
        )
    except TimeoutExpired as e:
        logger.error(f"TimeoutExpired waiting for {task_title} task")
        raise e

    # wait for the trigger task to complete
    try:
        task_helper.wait_for_task_to_be_initialized(
            task_id=trigger_task_id, timeout=TimeoutManager.create_backup_timeout
        )
        # Need to check for subtask with title "Staging Backup Workflow" to complete
        subtask_name = SubTaskDisplayName.STAGING_BACKUP_WORKFLOW.value
        task_helper.wait_for_subtask_to_complete(subtask_name=subtask_name, task_id=trigger_task_id, timeout=10 * 60)

    except TimeoutError as e:
        # cloud_type can stay at 50% for several hours (transient to cloud thing?)
        # NOTE: DCS-3811 can have "Native Backups" remain in a running state for up to an hour
        # due to the numerous "Image Delete Child Workflow" subtasks.
        # We'll output the number of subtasks the "trigger_task_id" has for debugging purposes
        logger.error(f"TimeoutError waiting for subtask {subtask_name} to complete.")
        raise e
    print(f"In wait_for_staging_backup_task returning trigger_task_id -> {trigger_task_id}")
    return trigger_task_id
