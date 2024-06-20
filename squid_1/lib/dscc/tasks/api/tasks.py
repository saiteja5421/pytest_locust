import logging
from requests import Response
from waiting import wait, TimeoutExpired

from email.utils import formatdate

from common.enums.task_status import TaskStatus
from utils.dates import parse_to_iso8601
from common.common import get
from common.users.user import User
from common import helpers
from tests.aws.config import Paths
from lib.dscc.tasks.payload.task import Task, TaskList

# TODO -> Yet to be refactored


logger = logging.getLogger()


class TaskManager:
    def __init__(self, user: User):
        self.user = user
        self.url = helpers.get_locust_host()
        self.path = Paths.TASK_API
        self.user_id = user.user.username

    def get_task(self, task_id):
        return get(self.url, self.path + "/" + task_id, headers=self.user.authentication_header)

    def get_task_object(self, task_id: str) -> Task:
        response = self.get_task(task_id)
        task = Task.from_json(response.text)
        return task

    def get_tasks(self, date_time, time_offset_minutes=0, include_userId=True) -> TaskList:
        """
        Return tasks list from date_time to current time.

        date_time str: Date time as string in format (Tue, 16 Nov 2021 13:35:38 GMT)
        time_offset_minutes int: Time delta to subtract from date_time
        include_userId boolean: If True then includes userId in filter query
        """
        datetime_formated = parse_to_iso8601(date_time, time_offset_minutes)

        filter = f"createdAt gt {datetime_formated}"
        if include_userId:
            filter += f" and userId eq '{self.user_id}'"

        # As of this writing, the ccs-tasks REST API supports a minimum page limit of 2 and a maximum limit
        # of 100.  Here we loop through the tasks, increasing the offset each loop, until all of the tasks
        # are retrieved and added to the all_tasks array.  Note that the sort is set to "createdAt" instead
        # of "createdAt Desc" as was done in previous versions.  If we sort from most to least recent, any
        # new tasks added during the loop will be inserted at the front.  That will cause the older tasks
        # to shift downwards.  Duplicate tasks would then get added to all_tasks.
        max_objects = 10000
        all_tasks: TaskList = TaskList(items=[], page_limit=max_objects, page_offset=0, total=0)
        for offset in range(0, max_objects, 100):
            # https://pages.github.hpe.com/nimble-dcs/storage-api/docs/#get-/api/v1/tasks
            params = {
                "filter": filter,
                "offset": offset,
                "limit": 100,
                "sort": "createdAt",
            }

            payload_str = "&".join("%s=%s" % (k, v) for k, v in params.items())
            tasks = get(self.url, self.path, payload_str, headers=self.user.authentication_header)
            paged_tasks = TaskList.from_json(tasks.text)
            if len(paged_tasks.items) == 0:
                # Break out of loop when there are no tasks remaining
                break
            all_tasks.items.extend(paged_tasks.items)
            all_tasks.total += len(paged_tasks.items)

        # The original version of this get_tasks API returned tasks sorted from most to least recent.
        # As detailed above, the tasks had to be enumerated from least to most recent.  For backwards
        # compatibility, before returning the list of tasks, sort it from most to least recent.
        all_tasks.items.sort(key=lambda x: x.created_at, reverse=True)
        return all_tasks

    def get_task_for_vm(self, vm_name):
        return get(
            self.url,
            self.path + "?filter=sourceResource.name+eq+" + f"'{vm_name}'" + "&sort=createdAt+desc",
            headers=self.user.authentication_header,
        )

    @staticmethod
    def get_task_id_from_header(response: Response):
        """Returns task_id parsed from 'Location' header of the response object as per the new GLCP API compliance"""
        logger.info(f"task {response.headers}: {response.headers}")
        task_id = response.headers.get("Location")
        return task_id.split("/")[-1]

    @staticmethod
    def get_task_id(response: Response):
        """Returns task_id parsed from given response object"""
        task_id = response.json()["taskUri"]
        return task_id.split("/")[-1]

    def get_task_state_by_id(self, task_id: str):
        """Fetches the given task_id and returns the state of it. E.g. running"""
        response = self.get_task(task_id)
        state = response.json().get("state")
        logger.info(f"task {task_id} state: {state}")
        assert state in [x.value for x in TaskStatus], f"Task state '{state}' not in TaskStatus enum!"
        return state.lower()

    def get_task_progress_percent_by_id(self, task_id: str):
        """Fetches the given task_id and returns the progressPercent of it. E.g. 0"""
        response = self.get_task(task_id)
        progress_percent = response.json().get("progressPercent")
        return progress_percent

    def get_task_error(self, task_id: str):
        """
        Fetches the given task_id and returns its error.
        E.g. invalid input(s): account ID 00000000-0000-0000-0000-000000000002 not found
        """
        response = self.get_task(task_id)
        try:
            error = response.json()["error"]["error"]
        except TypeError:
            error = ""
        return error

    def get_task_source_resource_uuid(self, task_id: str, source_resource_type: str):
        """
            This support routine performs the following steps:
            1.) Fetch the given task_id
            2.) Validates the task's source_resource property is present
            3.) Validates the task's source_resource.type is the given source_resource_type
            4.) Validates the task's source_resource.resource_uri prefix aligns with the provided source_resource_type
            5.) Extracts and returns the UUID from the task's source_resource.resource_uri

        Args:
            task_id (str): Task ID
            source_resource_type (str): Unqualified resource type (e.g. AssetType.PROTECTION_GROUP_TYPE.value)

        Returns:
            str: UUID from task's source_resource.resource_uri
        """
        task_object: Task = self.get_task_object(task_id)
        assert task_object.source_resource is not None
        # Tolerate resource type in either old (e.g. "csp-account") or new (e.g. "hybrid-cloud/csp-account") styles.
        assert source_resource_type in task_object.source_resource.type
        index = task_object.source_resource.resource_uri.rfind("/")
        assert index != -1
        prefix, resource_uuid = (
            task_object.source_resource.resource_uri[: index + 1],
            task_object.source_resource.resource_uri[index + 1 :],  # noqa: E203
        )
        # Tolerate resource URI in either old (e.g. "/api/v1/...") or new (e.g. "/hybrid-cloud/v1beta1/...") styles.
        assert source_resource_type in prefix, f'prefix={prefix}, expected to contain "{source_resource_type}"'
        return resource_uuid

    def get_task_source_resource_name(self, task_id: str):
        """Fetch task by id and return its source_resource's name. E.g. Test account"""
        task_object: Task = self.get_task_object(task_id)
        assert task_object.source_resource is not None
        return task_object.source_resource.name

    def wait_for_task(self, task_id, timeout: int, interval=0.1, message="", log_result=False):
        """
            Waits for given task_id to complete (i.e. method returns when task state not in RUNNING
            or INITIALIZED state).

        Args:
            task_id (str): Task ID
            timeout (int): TimeoutError exception is raised if task does not complete in the specified seconds.
            interval (float, optional): Number of seconds to sleep between retries.  Value doubles each retry up
                to a maximum of 10 seconds (or the given interval if larger).  Sample sleep times:  0.1, 0.2, 0.4,
                0.8, 1.6, 3.2, 6.4, 10, 10, 10, ... up until exception timeout or task completion.
            message (str, optional): Message to pass to TimeoutError exception. Defaults to "".
            log_result (bool, optional): Log task completion to logs?

        Returns:
            str: Completion task state (lower-case).  See TaskStatus enum.
        """
        try:
            wait(
                lambda: self.get_task_state_by_id(task_id)
                not in [TaskStatus.running.value.lower(), TaskStatus.initialized.value.lower()],
                timeout_seconds=timeout,
                sleep_seconds=(interval, 10),
            )

            response = self.get_task(task_id)
            response_json = response.json()
            if log_result:
                logger.info(f"wait_for_task {response_json['displayName']} completion, response={response_json}")
            task_state = response_json.get("state")
            assert task_state in [x.value for x in TaskStatus], "No state type in response!"
            return task_state.lower()
        except TimeoutExpired:
            raise TimeoutError(message)

    def wait_for_task_error(self, task_id, timeout: int, interval=0.1, message="", log_result=False):
        """
            Waits for given task_id to complete (i.e. method returns when task state not in RUNNING
            or INITIALIZED state).

        Args:
            task_id (str): Task ID
            timeout (int): TimeoutError exception is raised if task does not complete in the specified seconds.
            interval (float, optional): Number of seconds to sleep between retries.  Value doubles each retry up
                to a maximum of 10 seconds (or the given interval if larger).  Sample sleep times:  0.1, 0.2, 0.4,
                0.8, 1.6, 3.2, 6.4, 10, 10, 10, ... up until exception timeout or task completion.
            message (str, optional): Message to pass to TimeoutError exception. Defaults to "".
            log_result (bool, optional): Log task completion to logs?

        Returns:
            str: Completion task state (lower-case).  See TaskStatus enum.
        """
        try:
            error = wait(
                lambda: self.get_task_error(task_id),
                timeout_seconds=timeout,
                sleep_seconds=(interval, 10),
            )
            return error
        except TimeoutExpired:
            raise TimeoutError(message)

    def get_tasks_by_name_and_resource_uri_with_no_offset(
        self, task_name: str, resource_uri: str, time_offset_minutes: int = 10
    ) -> TaskList:
        """Return a TaskList matching 'task_name' and 'resource_uri' provided.

        Args:
            task_name (str): The task name to match
            resource_uri (str): The resource uri to match
            time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

        Returns:
            TaskList: A TaskList containing any matching Tasks
        """
        # search for tasks 'time_offset_minutes' back from time 'now'
        date_time = formatdate(timeval=None, localtime=False, usegmt=True)
        datetime_formated = parse_to_iso8601(date_time=date_time, time_offset_minutes=time_offset_minutes)

        # NOTE: it seems that the trigger task name format is changed on FILEPOC
        # on SCDEV01: "Trigger Cloud Backup"
        # on FILEPOC: "Trigger Cloud Backup for csp-volume [vol-050603a150e71eae1]"
        # We cannot use the '[' or ']' characters in: "displayName eq '{task_name}'"
        #
        # We'll get all tasks for the 'sourceResource.resourceUri' and then manually look
        # through the 'task.display_name" to match with the 'task_name' provided
        params = f"offset=0&limit=10&sort=createdAt desc&filter=createdAt gt {datetime_formated} and sourceResource.resourceUri eq '{resource_uri}'"
        response = get(self.url, self.path, params, headers=self.user.authentication_header)

        return_list = TaskList(items=[], page_limit=0, page_offset=0, total=0)
        task_list: TaskList = TaskList.from_json(response.text)
        for task in task_list.items:
            logger.info(f"Task Name = {task.name}: {task.display_name}")
            if task_name in task.display_name:
                logger.info(f"Adding item: {task}")
                return_list.items.append(task)
                return_list.total += 1

        return return_list

    def get_tasks_by_name_and_resource(
        self, task_name: str, resource_uri: str, time_offset_minutes: int = 30
    ) -> TaskList:
        """Return a TaskList matching 'task_name' and 'resource_uri' provided.

        Args:
            task_name (str): The task name to match
            resource_uri (str): The resource uri to match
            time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

        Returns:
            TaskList: A TaskList containing any matching Tasks
        """
        # search for tasks 'time_offset_minutes' back from time 'now'
        date_time = formatdate(timeval=None, localtime=False, usegmt=True)
        datetime_formated = parse_to_iso8601(date_time=date_time, time_offset_minutes=time_offset_minutes)

        # NOTE: it seems that the trigger task name format is changed on FILEPOC
        # on SCDEV01: "Trigger Cloud Backup"
        # on FILEPOC: "Trigger Cloud Backup for csp-volume [vol-050603a150e71eae1]"
        # We cannot use the '[' or ']' characters in: "displayName eq '{task_name}'"
        #
        # We'll get all tasks for the 'sourceResource.resourceUri' and then manually look
        # through the 'task.display_name" to match with the 'task_name' provided
        # Need to understand when task will start using the new resource uri.
        # Below is the temporary fix.
        #
        resource_uri = "/".join(resource_uri.split("/")[-2:])
        max_objects = 10000
        return_list = TaskList(items=[], page_limit=0, page_offset=0, total=0)
        for offset in range(0, max_objects, 100):
            params = f"offset={offset}&limit=100&sort=createdAt desc&filter=createdAt gt {datetime_formated}"
            response = get(self.url, self.path, params, headers=self.user.authentication_header)

            # task.name         = CSPBackupParentWorkflow
            # task.display_name = Trigger Cloud Backup for csp-volume [vol-0ee9a3901a22d8edb]
            task_list: TaskList = TaskList.from_json(response.text)
            if not task_list.items:
                # Break out of loop when there are no tasks remaining
                break
            for task in task_list.items:
                logger.info(f"Task Name = {task.name}: {task.display_name}")
                if not task.source_resource:
                    logger.info("No task.source_resource.resource_uri field")
                    continue
                if task_name in task.display_name and resource_uri in task.source_resource.resource_uri:
                    logger.info(f"Adding item: {task}")
                    return_list.items.append(task)
                    return_list.total += 1

        return return_list

    def get_tasks_by_name_and_customer_account(
        self, task_name: str, customer_id: str, time_offset_minutes: int = 10
    ) -> list[Task]:
        """Return a list[Task] matching 'task_name' and 'customer_id'.

        Args:
            task_name (str): The task name to match
            customer_id (str): CustomerID (CSPAccount.customerId)
            time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

        Returns:
            list[Task]: a list[Task] containing any matching Tasks
        """
        # search for tasks 'time_offset_minutes' back from time 'now'
        date_time = formatdate(timeval=None, localtime=False, usegmt=True)
        datetime_formated = parse_to_iso8601(date_time=date_time, time_offset_minutes=time_offset_minutes)

        filter = f"createdAt gt {datetime_formated} and customerId eq '{customer_id}'"

        logger.info(f"Looking for task_name: {task_name}")
        logger.info(f"Using filter: {filter}")

        return_list = TaskList(items=[], page_limit=0, page_offset=0, total=0)
        # max_objects = 10000
        # for offset in range(0, max_objects, 100):
        params = {
            "filter": filter,
            "limit": 100,
            "offset": 0,
            "sort": "createdAt desc",
        }
        payload_str = "&".join("%s=%s" % (k, v) for k, v in params.items())
        logger.info(f"url {self.url} payload {payload_str}")
        response = get(self.url, self.path + "?" + payload_str, headers=self.user.authentication_header)
        task_list: TaskList = TaskList.from_json(response.text)
        if not task_list.items:
            logger.info(f"There are no matched items")
            return
        logger.info(f"There are {task_list.total} items")

        for task in task_list.items:
            if task_name in task.display_name:
                logger.info(f"Adding item: {task}")
                return_list.items.append(task)
                return_list.total += 1

        return return_list.items

    def get_delete_indexed_files_tasks_containing_name(
        self, task_name: str, time_offset_minutes: int = 10
    ) -> list[Task]:
        """Return a list of "DeleteIndexDataWorkflow" Tasks containing 'task_name' in their Display Name.

        Args:
            task_name (str): The task name to match
            time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

        Returns:
            list[Task]: a list[Task] containing any matching Tasks
        """
        # search for tasks 'time_offset_minutes' back from time 'now'
        date_time = formatdate(timeval=None, localtime=False, usegmt=True)
        datetime_formated = parse_to_iso8601(date_time=date_time, time_offset_minutes=time_offset_minutes)

        filter = f"createdAt gt {datetime_formated} and name eq 'DeleteIndexDataWorkflow'"

        logger.info(f"Looking for task_name:timeouts {task_name}")
        logger.info(f"Using filter: {filter}")

        params = {
            "filter": filter,
            "limit": 20,
            "offset": 0,
            "sort": "createdAt desc",
        }
        payload_str = "&".join("%s=%s" % (k, v) for k, v in params.items())
        response = get(self.url, self.path, payload_str, headers=self.user.authentication_header)

        task_list: TaskList = TaskList.from_json(response.text)
        logger.info(f"There are {task_list.total} items")
        tasks = []

        # should typically only be 1 item
        for task in task_list.items:
            if task_name in task.display_name:
                logger.info(f"adding task: {task.id}")
                tasks.append(task)

        return tasks

    def wait_for_task_percent_complete(
        self,
        task_id: str,
        percent_complete: int,
        timeout: int,
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
                lambda: self.get_task_progress_percent_by_id(task_id=task_id) >= percent_complete,
                timeout_seconds=timeout,
                sleep_seconds=(interval, 10),
            )
        except TimeoutExpired:
            raise TimeoutError(f"Task: {task_id} timed out and did not reach {percent_complete} percent complete")

        logger.info(f"Task: {task_id} is {percent_complete} complete")
