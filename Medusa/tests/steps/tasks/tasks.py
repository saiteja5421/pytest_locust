"""
This module contains functions related to retrieving and waiting for Task objects and status
"""

import logging
from typing import Union
from waiting import wait, TimeoutExpired

from requests import Response

from lib.common.users.user import User
from lib.common.enums.task_status import TaskStatus

from lib.dscc.tasks.api.tasks import TaskManager
from lib.dscc.tasks.payload.task import Task, TaskList

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectNameResourceType


logger = logging.getLogger()


def get_task_status(task_id: str, user: User) -> str:
    """Get the Task Status of the provided "task_id"

    Args:
        task_id (str): The Task ID
        user (User): The Context User object

    Returns:
        str: The Task Status; lowercase value of TaskStatus
    """
    tasks = TaskManager(user)
    return tasks.get_task_state_by_id(task_id)


def get_task_error(task_id: str, user: User) -> str:
    """Get the Task Error of the provided "task_id"

    Args:
        task_id (str): The Task ID
        user (User): The Context User object

    Returns:
        str: The Task Error if the Task has a "failed" Status, "" otherwise.
    """
    error_message: str = ""
    tasks = TaskManager(user)
    response = tasks.get_task(task_id)
    content = response.json()
    if content.get("state") == TaskStatus.failed.value:
        error_message = response.json().get("error", {}).get("error", "")
    return error_message


def get_task_error_code(task_id: str, user: User) -> int:
    """Get the Task Error Code of the provided "task_id"

    Args:
        task_id (str): The Task ID
        user (User): The Context User object

    Returns:
        int: The Task Error Code if the Task has a "failed" Status, 0 otherwise.
    """
    error_code: int = 0
    tasks = TaskManager(user)
    response = tasks.get_task(task_id)
    content = response.json()
    if content.get("state") == TaskStatus.failed.value:
        error_code = int(response.json().get("error", {}).get("errorCode", ""))
    return error_code


def get_task_logs(task_id: str, user: User) -> list[dict]:
    """Get the Task Logs of the provided "task_id"

    Args:
        task_id (str): The Task ID
        user (User): The Context User object

    Returns:
        list[dict]: The list of Log Messages from the Task.
        (e.g. {'message': 'CreateTaskForCVSAActivity: Create Task Activity is successful with TaskID: 43b3eb67-9642-494e-8159-d1720a45da19.', 'timestampAt': '2023-05-30T18:48:38.850622368Z'})
    """
    tasks = TaskManager(user)
    response = tasks.get_task(task_id)
    content = response.json()
    return content["logMessages"]


def get_task_source_resource_uuid(task_id: str, user: User, source_resource_type: str) -> str:
    """Get the Task Source Resource UUID value, given the "source_resource_type"

    Args:
        task_id (str): The Task ID
        user (User): The Context User object
        source_resource_type (str): The Source Resource Type. (e.g. CSPResourceType.PROTECTION_GROUP_RESOURCE_TYPE.value)

    Returns:
        str: UUID of the Task's source_resource.resource_uri value
    """
    task_manager = TaskManager(user)
    return task_manager.get_task_source_resource_uuid(task_id=task_id, source_resource_type=source_resource_type)


def get_child_task_id(task_id, user):
    child_task = ""
    tasks = TaskManager(user)
    filter = f"?filter=parent/id eq '{task_id}'"
    response = tasks.get_task_by_filter(filter)
    response_json = response.json()
    logger.info(f"Task response : {response_json}")
    child_task = response_json.get("items", "")[0].get("id", "")
    # child_task = response_json.get("childTasks")[0].get("resourceUri", "").split("/")[-1]
    assert child_task, "Failed to fetch child task id."
    logger.info(f"Child task id is: {child_task}")
    return child_task


def get_task_id(response: Response) -> str:
    """Parse out the "taskUri" from the Response object and return the "task_id" value

    Args:
        response (Response): A Response object from Tasks API Call

    Returns:
        str: The Task ID from the Response object
    """
    logger.debug(f"Response {response.status_code} {response.json()}")
    task_id: str = response.json()["taskUri"]
    return task_id.split("/")[-1]


def get_task_id_from_header(response: Response):
    """Returns task_id parsed from 'Location' header of the response object as per the new GLCP API compliance"""
    logger.info(f"task {response.headers}: {response.headers}")
    task_id = response.headers.get("Location")
    return task_id.split("/")[-1]


def get_task_source_resource_name(task_id: str, user: User) -> str:
    """Get the Task Source Resource Name of the provided "task_id"

    Args:
        task_id (str): The Task ID
        user (User): The Context User object

    Returns:
        str: Name of the Task's Source Resource
    """
    task_manager = TaskManager(user)
    return task_manager.get_task_source_resource_name(task_id=task_id)


def wait_for_task(
    task_id: str, user: User, timeout: int, interval: float = 0.1, message: str = "", log_result: bool = False
) -> str:
    """Wait for the provided "task_id" to run to completion. (i.e. function returns when task state is not RUNNING or INITIALIZED)

    Args:
        task_id (str): The Task ID
        user (User): The Context User object
        timeout (int): A TimeoutError exception is raised if Task does not complete in the specified number of seconds
        interval (float, optional): Number of seconds to sleep between retries.  Value doubles each retry up
            to a maximum of 10 seconds (or the given interval if larger).  Sample sleep times:  0.1, 0.2, 0.4,
            0.8, 1.6, 3.2, 6.4, 10, 10, 10, ... up until exception timeout or task completion.
        message (str, optional): Message to pass to TimeoutError exception. Defaults to "".
        log_result (bool, optional): If True, the Task results are logged. Defaults to False.

    Returns:
        str: Completion task state (lower-case).  See TaskStatus enum.
    """
    tasks = TaskManager(user)
    task_obj = tasks.get_task_object(task_id)
    logger.info(f"Wait for task Name {task_obj.display_name} - user {user.user.username} - id {task_id}")
    return tasks.wait_for_task(
        task_id=task_id, timeout=timeout, interval=interval, message=message, log_result=log_result
    )


def wait_for_task_error(
    task_id: str, user: User, timeout: int, interval: float = 0.1, message: str = "", log_result: bool = False
) -> str:
    """Wait for the provided "task_id" to run to completion. (i.e. function returns when task state is not RUNNING or INITIALIZED)

    Args:
        task_id (str): The Task ID
        user (User): The Context User object
        timeout (int): A TimeoutError exception is raised if Task does not complete in the specified number of seconds
        interval (float, optional): Number of seconds to sleep between retries.  Value doubles each retry up
            to a maximum of 10 seconds (or the given interval if larger).  Sample sleep times:  0.1, 0.2, 0.4,
            0.8, 1.6, 3.2, 6.4, 10, 10, 10, ... up until exception timeout or task completion.
        message (str, optional): Message to pass to TimeoutError exception. Defaults to "".
        log_result (bool, optional): If True, the Task results are logged. Defaults to False.

    Returns:
        str: Completion task state (lower-case).  See TaskStatus enum.
    """
    tasks = TaskManager(user)
    task_obj = tasks.get_task_object(task_id)
    logger.info(f"Wait for task Name {task_obj.display_name} - user {user.user.username} - id {task_id}")
    return tasks.wait_for_task_error(
        task_id=task_id, timeout=timeout, interval=interval, message=message, log_result=log_result
    )


def wait_for_task_percent_complete(task_id: str, user: User, percent_complete: int, timeout: int):
    """Wait for the given "task_id" to reach the provided "percent_complete".

    Args:
        task_id (str): The Task ID
        user (User): The Context User object
        percent_complete (int): The desired percent complete for the Task ID
        timeout (int): TimeoutError exception is raised if Task does not complete in the specified number of seconds
    """
    tasks = TaskManager(user)
    tasks.wait_for_task_percent_complete(task_id=task_id, percent_complete=percent_complete, timeout=timeout)


def get_root_task_id(
    user: User, resource_id: str, task_name: str, date_start: str, parent_task_name: str = None
) -> str:
    """Looks for up to 1 Hour and returns the Root Task ID of the given "resource_id" and "task_name".

    Args:
        user (User): The Context User object
        resource_id (str): The Source Resource ID
        task_name (str): A portion of the full Task Display Name to match
        date_start (str): A date string to begin looking for Root Task
        parent_task_name (str, optional): If provided and matches, the Parent Task ID is returned instead of Root Task ID. Defaults to None.

    Raises:
        e: A TimeoutExpired exception is raised if the Root Task is not found within 1 Hour

    Returns:
        str: The Root or Parent Task ID
    """
    task_manager = TaskManager(user)
    root_task_id: str = None

    def _get_root_task_id():
        tasks: TaskList = task_manager.get_tasks(date_start, time_offset_minutes=0, include_userId=False)
        for item in tasks.items:
            if task_name not in item.display_name:
                continue
            logger.info(f"{task_name} found in task id: {item.id}")
            logger.info(f"Task: {item}")

            source_resource_uri = (
                item.source_resource.resource_uri
                if item.source_resource and item.source_resource.resource_uri
                else item.source_resource_uri
            )
            if not source_resource_uri:
                logger.info(f"Task {item.display_name} did not produce a 'source_resource_uri' value, continuing")
                continue

            logger.info(f"Source Resource URI from _get_root_task_id(): {source_resource_uri}")

            logger.info(f"Trying to find {resource_id} in {source_resource_uri}")
            if resource_id in source_resource_uri:
                if parent_task_name:
                    if item.parent_task and parent_task_name in item.parent_task.name:
                        return item.id
                    elif item.parent and parent_task_name in item.parent.name:
                        return item.id
                    else:
                        continue
                return item.root_task.id if item.root_task else item.root_operation.id
        return False

    try:
        root_task_id = wait(_get_root_task_id, timeout_seconds=3600, sleep_seconds=60)
    except TimeoutExpired as e:
        tasks: TaskList = task_manager.get_tasks(date_start, time_offset_minutes=5, include_userId=False)
        logger.info(tasks)
        logger.error(
            f"Root task not found {task_name}, resource_id {resource_id}, parent_task_name: {parent_task_name}"
        )
        raise e

    return root_task_id


def wait_for_task_resource(
    user: User,
    resource_id: str,
    task_display_name: str,
    date_start: str,
    wait_completed: bool = False,
    parent_task_name: str = None,
) -> str:
    """Get Root Task ID of the given "resource_id" and "task_display_name", and wait for its Child Tasks to run to completion. Also waits for the Root Task to complete, if requested.

    Args:
        user (User): The Context User object
        resource_id (str): The Source Resource ID
        task_display_name (str): A portion of the full Task Display Name to match
        date_start (str): A date string to begin looking for Root Task
        wait_completed (bool, optional): If True, waits for the Root Task to run to completion. Defaults to False.
        parent_task_name (str, optional): If provided and matches, the Parent Task ID is returned instead of Root Task ID. Defaults to None.

    Returns:
        str: The Root or Parent Task ID
    """
    root_task_id = get_root_task_id(user, resource_id, task_display_name, date_start, parent_task_name)

    wait_for_child_tasks(root_task_id, user)

    if wait_completed:
        status = wait_for_task(root_task_id, user, timeout=3600)
        assert (
            status.upper() == TaskStatus.success.value
        ), f"Root Backup task failed for the task id {root_task_id}, Check the task logs for more information"
        return root_task_id

    return root_task_id


def get_child_tasks_from_task(task: Task, user: User) -> Union[list[Task], list[ObjectNameResourceType]]:
    """The Task object may or may not have a "child_tasks" field.

    Args:
        task (Task): The Task object for which to return child_tasks
        user (User): context.user object

    Returns:
        Union[list[Task], list[ObjectNameResourceType]]: If the provided task has a "child_task" field populated, that data will be returned.
        Otherwise, a filtered list[Task] will be returned that have a "parent/id eq {task.id}"
    """
    # if the Task has 'child_tasks' populated, return them -> list[ObjectNameResourceType]
    if task.child_tasks:
        return task.child_tasks

    # otherwise, we'll get_filtered_tasks() -> list[Task]
    tasks = TaskManager(user)
    child_tasks = tasks.get_filtered_tasks(filter=f"parent/id eq '{task.id}'").items

    return child_tasks


def get_resource_uri_from_child_task(task: Union[Task or ObjectNameResourceType]) -> str:
    """The function get_child_tasks_from_task() returns either a list of Task or ObjectNameResourceType.
    This function returns either the: Task.resource_uri  or  ObjectNameResourceType.resourceUri

    Args:
        task (Union[Task  |  ObjectNameResourceType]): A child_task item

    Returns:
        str: The "resource_uri" of the child_task item
    """
    if isinstance(task, Task):
        return task.resource_uri

    return task.resourceUri


def wait_for_child_tasks(root_task_id: str, user: User, tasks_count: int = 0, raise_error_on_failure: bool = True):
    """Wait for Child Tasks of the provided "root_task_id" to run to a successful completion

    Args:
        root_task_id (str): The Root Task ID
        user (User): The Context User object
        tasks_count (int, optional): If there are "tasks_count" Child Tasks, the function returns without waiting for task completion. Defaults to 0.
        raise_error_on_failure (bool, optional): Raises 'ValueError' when set to 'True'. Defaults to 'True'

    Raises:
        ValueError: A ValueError exception is raised if a Child Task Status is not TaskStatus.success.value
    """
    logger.info(f"Waiting for child task in root task id:{root_task_id}")
    task_ids = []
    root_task = get_task_object(user, root_task_id)

    # get the "child_tasks" for the given "root_task"
    child_tasks = get_child_tasks_from_task(task=root_task, user=user)

    for child_task in child_tasks:
        # NOTE: "child_task" could be a Task or an ObjectNameResourceType.
        # Task.resource_uri  or  ObjectNameResourceType.resourceUri
        resource_uri = get_resource_uri_from_child_task(child_task)
        child_task_id = resource_uri.split("/")[-1]
        task_ids.append(child_task_id)

    if tasks_count == len(task_ids):
        return

    for task_id in task_ids:
        logger.info(f"Waiting for task id:{task_id}")
        status = wait_for_task(task_id, user, timeout=3600)
        if status.upper() != TaskStatus.success.value:
            if raise_error_on_failure:
                failed_task = get_task_object(user, task_id)
                log_messages: str = " ".join([logs.message for logs in failed_task.log_messages])
                raise ValueError(f"Child task status {status}, {log_messages}")

    wait_for_child_tasks(root_task_id, user, len(task_ids))


def get_tasks_by_name_and_resource_uri_with_no_offset(
    user: User, task_name: str, resource_uri: str, time_offset_minutes: int = 10
) -> TaskList:
    """Return a TaskList matching the "task_name" and "resource_uri" provided

    Args:
        user (User): The Context User object
        task_name (str): The Task Name to match
        resource_uri (str): The Resource URI to match
        time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

    Returns:
        TaskList: A TaskList containing any matching Tasks
    """
    task_manager = TaskManager(user)
    return task_manager.get_tasks_by_name_and_resource_uri_with_no_offset(
        task_name=task_name, resource_uri=resource_uri, time_offset_minutes=time_offset_minutes
    )


def get_tasks_by_name_and_resource(
    user: User, task_name: str, resource_uri: str, time_offset_minutes: int = 10
) -> TaskList:
    """Return a TaskList matching the "task_name" and "resource_uri" provided

    Args:
        user (User): The Context User object
        task_name (str): The Task Name to match
        resource_uri (str): The Resource URI to match
        time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

    Returns:
        TaskList: A TaskList containing any matching Tasks
    """
    task_manager = TaskManager(user)
    return task_manager.get_tasks_by_name_and_resource(
        task_name=task_name, resource_uri=resource_uri, time_offset_minutes=time_offset_minutes
    )


def get_tasks_by_name_and_customer_account(
    user: User, task_name: str, customer_id: str, time_offset_minutes: int = 10
) -> list[Task]:
    """Return a list[Task] matching the "task_name" and "customer_id" provided

    Args:
        user (User): The Context User object
        task_name (str): The Task Name to match
        customer_id (str): The Customer ID to match
        time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

    Returns:
        list[Task]: A list[Task] containing any matching Tasks
    """
    task_manager = TaskManager(user)
    return task_manager.get_tasks_by_name_and_customer_account(
        task_name=task_name, customer_id=customer_id, time_offset_minutes=time_offset_minutes
    )


def get_delete_indexed_files_tasks_containing_name(
    user: User, task_name: str, time_offset_minutes: int = 10
) -> list[Task]:
    """Return a list of "DeleteIndexDataWorkflow" Tasks containing 'task_name' in their Display Name.

    Args:
        user (User): The Context User object
        task_name (str): The Task Name to match
        time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

    Returns:
        list[Task]: A list[Task] containing any matching Tasks
    """
    task_manager = TaskManager(user)
    return task_manager.get_delete_indexed_files_tasks_containing_name(
        task_name=task_name, time_offset_minutes=time_offset_minutes
    )


def get_task_object(user: User, task_id: str) -> Task:
    """Get Task object with the provided "task_id"

    Args:
        user (User): The Context User object
        task_id (str): The Task ID

    Returns:
        Task: The Task object
    """
    task_manager = TaskManager(user)
    return task_manager.get_task_object(task_id=task_id)
