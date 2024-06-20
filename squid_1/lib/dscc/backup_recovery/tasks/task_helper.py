# from asyncio import tasks
from email.utils import formatdate
from time import sleep
from enum import Enum

# from locust import task
import requests
import logging

# from json import dumps, loads
from common import helpers
from tests.aws.config import Paths
from waiting import wait, TimeoutExpired
from common.enums.task_status import TaskStatus
from utils.dates import parse_to_iso8601
from lib.dscc.tasks.payload.task import TaskList, Task
from common.helpers import squid_is_retry_needed
from tenacity import retry, stop_after_attempt, wait_fixed
from common import common

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()

from utils.timeout_manager import TimeoutManager


class TaskDisplayNames(Enum):
    COPY2CLOUD_DISPLAY_NAME = "CVSA Nightly Trigger Cycle for"
    TRIGGER_CLOUD_BACKUP = "Trigger Cloud Backup"
    STAGING_BACKUP_WORKFLOW = "Staging Backup Workflow"


class SubTaskDisplayName(Enum):
    STAGING_BACKUP_WORKFLOW = "Staging Backup Workflow"
    INSTANCE_CLOUD_BACKUP_WORKFLOW = "InstanceCloudBackup Workflow"


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_tasks_by_resource_and_name(task_name, resource_uri, time_offset_in_minutes=10):
    """This function will return tasks filtered by given task name and resource_uri within specified time

    Args:
        task_name (string): task name
        resource_uri (string): resource uri
        time_offset_in_minutes (int, optional): Time interval to filter tasks Defaults to 10.

    Returns:
        _type_: List of tasks objects
    """
    # search for tasks 'time_offset_minutes' back from time 'now'
    date_time = formatdate(timeval=None, localtime=False, usegmt=True)
    datetime_formated = parse_to_iso8601(date_time=date_time, time_offset_minutes=time_offset_in_minutes)

    params = f"offset=0&limit=10&sort=createdAt desc&filter=createdAt gt {datetime_formated} and displayName eq '{task_name}' and sourceResource.resourceUri eq '{resource_uri}'"

    url = f"{helpers.get_locust_host()}/{Paths.TASK_API}"

    response = requests.request("GET", url, headers=headers.authentication_header, params=params)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    return TaskList.from_json(response.text)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_tasks_by_name_and_customer_account(task_name, customer_id, account_id, time_offset_minutes=30):
    """Filters task by task_name, customer_id and account_id for given time period

    Args:
        task_name (string): name of task
        customer_id (UUID): customer id
        account_id (UUID): customer account id
        time_offset_minutes (int, optional): time interval. Defaults to 10.

    Raises:
        TimeoutError: Task timeout

    Returns:
        _type_: List of tasks objects
    """
    # search for tasks 'time_offset_minutes' back from time 'now'
    date_time = formatdate(timeval=None, localtime=False, usegmt=True)
    datetime_formated = parse_to_iso8601(date_time=date_time, time_offset_minutes=time_offset_minutes)
    params = f"offset=0&limit=30&sort=createdAt desc&filter=createdAt gt {datetime_formated} and customerId eq '{customer_id}'"
    url = f"{helpers.get_locust_host()}/{Paths.TASK_API}"
    retry_count = 60
    while retry_count:
        response = requests.request("GET", url, headers=headers.authentication_header, params=params)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        task_list: TaskList = TaskList.from_json(response.text)
        tasks = []

        # should typically only be 1 item
        for task in task_list.items:
            if task.log_messages:
                if task_name in task.display_name:
                    tasks.append(task)
        if len(tasks):
            return tasks
        else:
            retry_count -= 1
            sleep(2)
            logger.debug(
                f"In get_tasks_by_name_and_customer_account {task_name} {customer_id} {account_id}, retrying after 15 seconds"
            )
    message = f"In get_tasks_by_name_and_customer_account, timeout exception has occured"
    print(message)
    logger.error(message)
    raise TimeoutError(message)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_task(task_id):
    """For given task ID returns task API response

    Args:
        task_id (UUID): Task ID

    Returns:
        _type_: Task object as returned by API
    """
    url = f"{helpers.get_locust_host()}/{Paths.TASK_API}/{task_id}"
    response = requests.request("GET", url, headers=headers.authentication_header, params="")
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    return response


def get_task_object(task_id: str):
    """For given task_id returns task object

    Args:
        task_id (UUID): Task ID

    Returns:
        _type_: Task object
    """
    response = get_task(task_id)
    task = Task.from_json(response.text)
    return task


def wait_for_task_to_be_initialized(task_id, timeout: int, log_result=False, message="", interval=0.1):
    """Waits for given task with task_id to be initialized or raises timeout error

    Args:
        task_id (UUID): Task ID to be initialized
        timeout (int): timeout value in seconds
        log_result (bool, optional): _description_. Defaults to False.
        message (str, optional): _description_. Defaults to "".
        interval (float, optional): _description_. Defaults to 0.1.

    Raises:
        TimeoutError: Timeout error
    """
    try:
        wait(
            lambda: get_task_state_by_id(task_id)
            in [
                TaskStatus.initialized.value.lower(),
                TaskStatus.running.value.lower(),
                TaskStatus.success.value.lower(),
            ],
            timeout_seconds=timeout,
            sleep_seconds=(interval, 10),
        )
        response = get_task(task_id)
        response_json = response.json()
        if log_result:
            logger.info(f"wait_for_task {response_json['displayName']} completion, response={response_json}")
        task_state = response_json.get("state")
        assert task_state in [x.value for x in TaskStatus], "No state type in response!"
        return task_state.lower()
    except TimeoutExpired:
        if message != "":
            logger.error(message)
        raise TimeoutError(message)


def wait_for_task(task_id, timeout: int, log_result=False, message="", interval=0.1):
    """Waits for task to be in one of following states -
        succeeded
        failed
        timefout

    Args:
        task_id (UUID): task ID
        timeout (int): Timeout value in seconds
        log_result (bool, optional): _description_. Defaults to False.
        message (str, optional): _description_. Defaults to "".
        interval (float, optional): _description_. Defaults to 0.1.

    Raises:
        TimeoutError: Timeout error

    Returns:
        _type_: Task state and end of function execution
    """
    try:
        wait(
            lambda: get_task_state_by_id(task_id)
            in [TaskStatus.success.value.lower(), TaskStatus.failed.value.lower(), TaskStatus.timedout.value.lower()],
            timeout_seconds=timeout,
            sleep_seconds=(interval, 10),
        )

        response = get_task(task_id)
        response_json = response.json()
        if log_result:
            logger.info(f"wait_for_task {response_json['displayName']} completion, response={response_json}")
        task_state = response_json.get("state")
        assert task_state in [x.value for x in TaskStatus], "No state type in response!"
        return task_state.lower()
    except TimeoutExpired:
        if message != "":
            logger.error(message)
        raise TimeoutError(message)


def get_task_state_by_id(task_id: str):
    """Returns task state for gien task id

    Args:
        task_id (UUID): task ID

    Returns:
        string: state of task
    """
    response = get_task(task_id)
    state = response.json().get("state")
    assert state in [x.value for x in TaskStatus], "No state type in response!"
    return state.lower()


def wait_for_subtask_to_complete(subtask_name, task_id, interval=0.1, timeout=TimeoutManager.create_backup_timeout):
    """Waits for subtask identified by subtask_name of parent task identified by task_id to complete

    Args:
        subtask_name (string): Display Name of subtask
        task_id (UUID): Parent task's ID
        interval (float, optional): _description_. Defaults to 0.1.
        timeout (_type_, optional): _description_. Defaults to TimeoutManager.create_backup_timeout.

    Raises:
        TimeoutError: Timeout error
    """
    try:
        wait(
            lambda: get_subtask_state(subtask_name=subtask_name, task_id=task_id)
            in [
                TaskStatus.success.value.lower(),
                TaskStatus.failed.value.lower(),
                TaskStatus.timedout.value.lower(),
            ],
            timeout_seconds=timeout,
            sleep_seconds=(interval, 10),
        )
    except TimeoutExpired:
        message = f"In wait_for_subtask_to_complete, timeout {timeout} expired"
        logger.error(message)
        print(message)
        raise TimeoutError(message)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def wait_for_subtask_to_start_and_return(subtask_name, task_id, time_offset_minutes=90):
    """Waits for subtask identified by subtask_name of parent task identified by task_id to start
    and return its object

    Args:
        subtask_name (string): Name of subtask
        task_id (UUID): Parent task UUID
        time_offset_minutes (int, optional): _description_. Defaults to 90.

    Raises:
        TimeoutError: Timeout error

    Returns:
        subtask: subtask object
    """
    date_time = formatdate(timeval=None, localtime=False, usegmt=True)
    datetime_formated = parse_to_iso8601(date_time=date_time, time_offset_minutes=time_offset_minutes)
    params = f"?filter=rootTask.id+eq+'{task_id}'&offset=0&limit=100&sort=createdAt desc&filter=createdAt gt {datetime_formated}"
    url = f"{helpers.get_locust_host()}/{Paths.TASK_API}"
    retry_count = 60
    while retry_count:
        response = requests.request("GET", url, headers=headers.authentication_header, params=params)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        task_list: TaskList = TaskList.from_json(response.text)
        tasks = []
        for task in task_list.items:
            if subtask_name in task.display_name:
                tasks.append(task)
        if len(tasks):
            return tasks[0]
        else:
            retry_count -= 1
            sleep(15)
    message = f"In wait_for_subtask_to_start_and_return, timeout exception"
    print(message)
    logger.error(message)
    raise TimeoutError(message)


def get_subtask_state(subtask_name, task_id):
    """Returns state of subtask identified by given subtask_name for given task_id

    Args:
        subtask_name (string): subtask name
        task_id (UUID): task UUID

    Returns:
        string: state of subtask
    """
    sub_task = wait_for_subtask_to_start_and_return(subtask_name, task_id, time_offset_minutes=30)
    return str(sub_task.state).lower()


def get_task_percentage(task_id):
    """Fetches the given task_id and returns the progressPercent of it. E.g. 0"""
    response = get_task(task_id)
    progress_percent = response.json().get("progressPercent")
    logger.info(f"Task ID {task_id} - Progress Percent: {progress_percent}")
    return progress_percent


def wait_for_task_percent_complete(
    task_id: str,
    percent_complete: int = 50,
    timeout: int = 300,
    interval: float = 0.1,
):
    """
        Waits for given task_id to reach the provided percent_complete.

    Args:
        task_id (str): Task ID
        percent_complete (int): The desired percent complete for Task ID
        timeout (int): TimeoutError exception is raised if task does not complete in the specified seconds.
        interval (float, optional): Number of seconds to sleep between retries.  Value doubles each retry up
            to a maximum of 10 seconds (or the given interval if larger).  Sample sleep times:  0.1, 0.2, 0.4,
            0.8, 1.6, 3.2, 6.4, 10, 10, 10, ... up until exception timeout or task completion.
    """
    try:
        wait(
            lambda: get_task_percentage(task_id=task_id) >= percent_complete,
            timeout_seconds=timeout,
            sleep_seconds=(interval, 10),
        )
    except TimeoutExpired:
        raise TimeoutError(f"Task: {task_id} timed out and did not reach {percent_complete} percent complete")

    logger.info(f"Task: {task_id} is {percent_complete} complete")
