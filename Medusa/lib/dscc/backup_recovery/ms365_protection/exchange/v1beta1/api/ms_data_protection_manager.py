import logging
import re
from typing import Union
from lib.common.users.user import User
from lib.common.common import get, post, delete, patch
import requests
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.csp_ms_backups import (
    MS365BackupsList,
    MS365Backup,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.payload.patch_ms_backup import PatchMS365SBackup
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
from lib.dscc.tasks.api.tasks import TaskManager
from lib.common.config.config_manager import ConfigManager
from requests import Response
from lib.dscc.tasks.payload.task import Task

logger = logging.getLogger()


class MSDataProtectionManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.ms365_api = config["MS365-API"]
        self.api_group = config["API-GROUP"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['atlantia-url']}/{self.api_group['backup-recovery']}/{self.dscc['beta-version']}"
        self.csp_ms365_backups = self.ms365_api["ms365-backups"]
        self.tasks = TaskManager(user)

    def list_ms365_backups(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[MS365BackupsList, ErrorResponse]:
        """Get information about MS365 backups.
        GET /backup-recovery/v1beta1/ms365-backups
        Args:
            limit (int, optional): The maximum number of items to include in the response. The offset and limit query parameters are used in conjunction for pagination, for example "offset=30&&limit=10" indicates the fourth page of 10 items.
            Defaults to 20.

            offset (int, optional): The number of items to omit from the beginning of the result set. Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional direction indicator: "asc" (ascending, the default) or "desc" (descending). These fields can be used for filtering: createdAt, expiresAt, state, status, indexState
            Defaults to "name".

            filter (str, optional): An expression by which to filter the results. A 'contains' expression can be used to filter the results based on case insensitive substring match. E.g. filter=contains(name, 'backup-1') will return all MS365 backups with names containing the string 'backup-1' or 'Backup-1'. These fields can be used for filtering: backupType, assetInfo/id, state, status, indexState
            Defaults to "".
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "OK"

        Returns:
            MS365BackupsList: Returns a list of MS365 backups, on success
            ErrorResponse: MS365 Backups error response, on failure
        """

        path: str = f"{self.csp_ms365_backups}?offset={offset}&limit={limit}&sort={sort}"
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 backups list: {response.text}"
        logger.debug(f"MS365 backups list. \n response: {response.text}")
        if response.status_code == requests.codes.ok:
            return MS365BackupsList.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def get_ms365_backup_by_id(
        self,
        csp_ms365_backup_id: str,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[MS365Backup, ErrorResponse]:
        """Get details of a specific MS365 backup.
           GET /backup-recovery/v1beta1/ms365-backups/{backup-id}

        Args:
            csp_ms365_backup_id (str): Unique identifier of a ms365 backup
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "OK"

        Returns:
            MS365Backup: Returns details of MS365 backup, on success
            ErrorResponse: MS365 Backup error response, on failure
        """
        path: str = f"{self.csp_ms365_backups}/{csp_ms365_backup_id}"
        response: Response = get(
            self.url,
            path,
            headers=self.user.authentication_header,
        )
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 backups details: {response.text}"
        logger.debug(f"MS365 backups details. \n response: {response.text}")
        if response.status_code == requests.codes.ok:
            return MS365Backup.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def delete_ms365_backup_by_id(
        self,
        csp_ms365_backup_id: str,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, ErrorResponse]:
        """Remove an MS365 backup.
           DELETE /backup-recovery/v1beta1/ms365-backups/{backup-id}

        Args:
            csp_ms365_backup_id (str): Unique identifier of a ms365 backup
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "ACCEPTED"

        Returns:
            str: task uri that can be used to monitor progress of the operation, on success
            ErrorResponse: Delete backup by id error response, on failure
        """
        path: str = f"{self.csp_ms365_backups}/{csp_ms365_backup_id}"
        response: Response = delete(
            self.url,
            path,
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, f"Error while deleting ms365 backup: {response.text}"
        logger.debug(f"Delete MS365 backup response: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def patch_ms365_backup_by_id(
        self,
        csp_ms365_backup_id: str,
        patch_backup_payload: PatchMS365SBackup,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, ErrorResponse]:
        """Modify the properties of an MS365 backup, The modifiable properties are Name of the Backup, Description of the backup and the retention period. The retention period needs to be specified as an absolute value of UTC.
        DELETE /backup-recovery/v1beta1/ms365-backups/{backup-id}

        Args:
            csp_ms365_backup_id (str): Unique identifier of a ms365 backup
            patch_backup_payload (PatchMS365SBackup): payload for MS365 backup update operation
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "ACCEPTED"

        Returns:
            str: task uri that can be used to monitor progress of the operation, on success
            ErrorResponse: Update backup error response, on failure
        """
        path: str = f"{self.csp_ms365_backups}/{csp_ms365_backup_id}"
        payload = patch_backup_payload.to_json()
        response: Response = patch(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, f"Error while updating ms365 backup: {response.text}"
        logger.debug(f"Update MS365 backup response: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def initiate_ms365_backup_index_by_id(
        self,
        csp_ms365_backup_id: str,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, ErrorResponse]:
        """Initiates an asynchronous operation to extract an index of items from the specified MS365 backup.
        POST /backup-recovery/v1beta1/ms365-backups/{backup-id}/index-items

        Args:
            csp_ms365_backup_id (str): Unique identifier of a ms365 backup
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "ACCEPTED"

        Returns:
            str: task uri that can be used to monitor progress of the operation, on success
            ErrorResponse: initiate ms365 backup index error response, on failure
        """
        path: str = f"{self.csp_ms365_backups}/{csp_ms365_backup_id}/index-items"
        response: Response = post(
            self.url,
            path,
            headers=self.user.authentication_header,
        )
        assert (
            response.status_code == expected_status_code
        ), f"Error while initiating ms365 backup index: {response.text}"
        logger.debug(f"Initiate MS365 backup index response: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def restore_ms365_contacts_from_backup(
        self,
        csp_ms365_backup_id: str,
        restore_contacts_payload: RestoreMS365Contacts,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, ErrorResponse]:
        """Restore contact(s) from the specified MS365 backup. Optionally, a list of contact ID(s) to be restored and a specific destination MS365 user ID to restore to, could be specified. Default is to restore all contact(s) in same MS365 user ID and to a new folder.
        POST /backup-recovery/v1beta1/ms365-backups/{backup-id}/restore-contacts

        Args:
            csp_ms365_backup_id (str): Unique identifier of a ms365 backup
            restore_contacts_payload (RestoreMS365Contacts): payload for restore MS365 contacts from the specified backup
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "ACCEPTED"

        Returns:
            str: task uri that can be used to monitor progress of the operation, on success
            ErrorResponse: Restore contacts error response, on failure
        """
        path: str = f"{self.csp_ms365_backups}/{csp_ms365_backup_id}/restore-contacts"
        payload = restore_contacts_payload.to_json()
        response: Response = post(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, f"Error while restore ms365 contacts: {response.text}"
        logger.debug(f"Restore MS365 contacts response: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def restore_ms365_emails_from_backup(
        self,
        csp_ms365_backup_id: str,
        restore_emails_payload: RestoreMS365Emails,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, ErrorResponse]:
        """Restore email(s) from the specified MS365 backup. Optionally, a list of email ID(s) to be restored and a specific destination MS365 user ID to restore to, could be specified. Default is to restore all email(s) in same MS365 user ID and to a new folder.
        POST /backup-recovery/v1beta1/ms365-backups/{backup-id}/restore-emails

        Args:
            csp_ms365_backup_id (str): Unique identifier of a ms365 backup
            restore_emails_payload (RestoreMS365Emails): payload for restore MS365 emails from the specified backup
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "ACCEPTED"

        Returns:
            str: task uri that can be used to monitor progress of the operation, on success
            ErrorResponse: Restore emails error response, on failure
        """
        path: str = f"{self.csp_ms365_backups}/{csp_ms365_backup_id}/restore-emails"
        payload = restore_emails_payload.to_json()
        response: Response = post(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, f"Error while restore ms365 emails: {response.text}"
        logger.debug(f"Restore MS365 emails response: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def restore_ms365_events_from_backup(
        self,
        csp_ms365_backup_id: str,
        restore_events_payload: RestoreMS365Events,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, ErrorResponse]:
        """Restore event(s) from the specified MS365 backup. Optionally, a list of event ID(s) to be restored and a specific destination MS365 user ID to restore to, could be specified. Default is to restore all event(s) in same MS365 user ID and to a new folder.
        POST /backup-recovery/v1beta1/ms365-backups/{backup-id}/restore-events

        Args:
            csp_ms365_backup_id (str): Unique identifier of a ms365 backup
            restore_events_payload (RestoreMS365Events): payload for restore MS365 emails from the specified backup
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "ACCEPTED"

        Returns:
            str: task uri that can be used to monitor progress of the operation, on success
            ErrorResponse: Restore events error response, on failure
        """
        path: str = f"{self.csp_ms365_backups}/{csp_ms365_backup_id}/restore-events"
        payload = restore_events_payload.to_json()
        response: Response = post(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, f"Error while restore ms365 events: {response.text}"
        logger.debug(f"Restore MS365 events response: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def restore_ms365_tasks_from_backup(
        self,
        csp_ms365_backup_id: str,
        restore_tasks_payload: RestoreMS365Tasks,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, ErrorResponse]:
        """Restore task(s) from the specified MS365 backup. Optionally, a list of task ID(s) to be restored and a specific destination MS365 user ID to restore to, could be specified. Default is to restore all task(s) in same MS365 user ID and to a new folder.
        POST /backup-recovery/v1beta1/ms365-backups/{backup-id}/restore-tasks

        Args:
            csp_ms365_backup_id (str): Unique identifier of a ms365 backup
            restore_events_payload (RestoreMS365Events): payload for restore MS365 emails from the specified backup
            expected_status_code (requests.codes, optional): expected rest response code, defaults to "ACCEPTED"

        Returns:
            str: task uri that can be used to monitor progress of the operation, on success
            ErrorResponse: Restore tasks error response, on failure
        """
        path: str = f"{self.csp_ms365_backups}/{csp_ms365_backup_id}/restore-tasks"
        payload = restore_tasks_payload.to_json()
        response: Response = post(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, f"Error while restore ms365 tasks: {response.text}"
        logger.debug(f"Restore MS365 tasks response: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def get_restore_folder_name_from_task(
        self,
        restore_task_id: str,
    ) -> str:
        """
        From task_id get folder where restore task will copy restored items
        Args:
            restore_task_id (str): restore task's id

        Returns:
            folder_name(str): Name of folder where restored items will be copied.
        """
        # Given a restore_task_id, extract folder_name where email will be restored.
        restore_task: Task = self.tasks.get_task_object(task_id=restore_task_id)
        last_task_message = restore_task.log_messages[-1].message
        pattern = r"Restored_By_HPE_\d+"
        folder_name = re.findall(pattern, last_task_message)
        assert len(folder_name) == 1, "Expected only one match folder name but More than one or no folders name matched"
        logger.info(f"Successfully fetched restored folder name from the tasks {folder_name[0]}")
        return folder_name[0]

    def get_latest_backup_id_for_user(
        self,
        user_id: str,
    ) -> str:
        """
        For given user find and return latest backup_id
        Args:
            user_id (str): user id for whom we need to obtain latest backup_id

        Returns:
            backup_id(str): latest backup_id found for given user_id
        """
        # For given user_id, return latest backup_id.
        pass
