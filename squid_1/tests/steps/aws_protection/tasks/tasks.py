import logging
from waiting import wait, TimeoutExpired

from requests import Response

from common.users.user import User
from common.enums.task_status import TaskStatus

from lib.dscc.tasks.api.tasks import TaskManager
from lib.dscc.tasks.payload.task import Task, TaskList


logger = logging.getLogger()


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
