import logging
from typing import Union
from lib.common.users.user import User
from lib.common.common import get, post
import requests
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.indexed_events import (
    IndexedEventList,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.indexed_contacts import (
    IndexedContactList,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.indexed_emails import (
    IndexedEmailList,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.indexed_tasks import (
    IndexedTaskList,
)
from lib.dscc.tasks.api.tasks import TaskManager
from lib.common.config.config_manager import ConfigManager
from requests import Response

logger = logging.getLogger()


class MSIndexManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.ms365_api = config["MS365-API"]
        self.api_group = config["API-GROUP"]
        self.dscc = config["CLUSTER"]
        self.backup_recovery = self.atlantia_api["backup-recovery"]
        self.ms365_protection_groups = self.ms365_api["ms365-protection-groups"]
        self.url = f"{self.dscc['atlantia-url']}/{self.backup_recovery}/{self.dscc['beta-version']}/"
        self.ms365_indexed_events = self.ms365_api["ms365-indexed-events"]
        self.ms365_indexed_tasks = self.ms365_api["ms365-indexed-tasks"]
        self.ms365_indexed_emails = self.ms365_api["ms365-indexed-emails"]
        self.ms365_indexed_contacts = self.ms365_api["ms365-indexed-contacts"]
        self.tasks = TaskManager(user)

    def get_ms365_indexed_contacts(
        self,
        csp_ms365_backup_id,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "displayName",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[IndexedContactList, ErrorResponse]:
        """Get list of MS365 indexed contacts from backup
           GET /backup-recovery/v1beta1/ms365-indexed-contacts
        Args:
            csp_ms365_backup_id (UUID): MS365 Backup ID which is to be used for getting indexed events.

            offset (int, optional): The number of items to omit from the begining of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.
            Defaults to 20.

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending).
            Sorting is supported on the following  properties:
            displayName
            Defaults to "displayName".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            displayName, emailAddress
            Defaults to "".
            expected_status_code (requests.codes, optional): Expected return status code. Defaults to requests.codes.ok.

        Returns:
            Union[IndexedContactList, ErrorResponse]: Either the list of MS365 indexed events or Error response will be returned.
        """
        response: Response = self.raw_get_ms365_indexed_contacts(csp_ms365_backup_id, limit, offset, sort, filter)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 indexed contact list: {response.text}"
        logger.debug(f"response from get_ms365_indexed_contacts: {response.text}")
        if response.status_code == requests.codes.ok:
            return IndexedContactList.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def raw_get_ms365_indexed_contacts(
        self, csp_ms365_backup_id, limit: int = 1000, offset: int = 0, sort: str = "name", filter: str = ""
    ) -> Response:
        """Wrapper of get API call to MS365 indexed contacts.

        Args:
            csp_ms365_backup_id (UUID): MS365 Backup ID which is to be used for getting indexed contacts.

            offset (int, optional): The number of items to omit from the begining of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.
            Defaults to 20.

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending).
            Sorting is supported on the following  properties:
            displayName
            Defaults to "displayName".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            displayName, emailAddress
            Defaults to "".
        Returns:
            Response: API response object.
        """
        path: str = (
            f"{self.ms365_indexed_contacts}?backup={csp_ms365_backup_id}?limit={limit}&offset={offset}&sort={sort}"
        )
        # only add "filter" if it's provided
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        return response

    def get_ms365_indexed_emails(
        self,
        csp_ms365_backup_id,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "receivedAt",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[IndexedEmailList, ErrorResponse]:
        """Get list of MS365 indexed emails from backup
           GET /backup-recovery/v1beta1/ms365-indexed-emails
        Args:
            csp_ms365_backup_id (UUID): MS365 Backup ID which is to be used for getting indexed emails.

            offset (int, optional): The number of items to omit from the begining of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.
            Defaults to 20.

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending).
            Sorting is supported on the following  properties:
            from/emailAddress, receivedAt
            Defaults to "receivedAt".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            mailFolderInfo/id, mailFolderInfo/name, from/name, from/emailAddress, toRecipients/name, toRecipients/emailAddress, ccRecipients/emailAddress, ccRecipients/name, subject, receivedAt
            Defaults to "".
            expected_status_code (requests.codes, optional): Expected return status code. Defaults to requests.codes.ok.

        Returns:
            Union[IndexedEmailList, ErrorResponse]: Either the list of MS365 indexed emails or Error response will be returned.
        """
        response: Response = self.raw_get_ms365_indexed_emails(csp_ms365_backup_id, limit, offset, sort, filter)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 indexed email list: {response.text}"
        logger.debug(f"response from get_ms365_indexed_emails: {response.text}")
        if response.status_code == requests.codes.ok:
            return IndexedEmailList.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def raw_get_ms365_indexed_emails(
        self, csp_ms365_backup_id, limit: int = 1000, offset: int = 0, sort: str = "name", filter: str = ""
    ) -> Response:
        """Wrapper of get API call to MS365 indexed emails.

        Args:
            csp_ms365_backup_id (UUID): MS365 Backup ID which is to be used for getting indexed contacts.

            offset (int, optional): The number of items to omit from the begining of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.
            Defaults to 20.

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending).
            Sorting is supported on the following  properties:
            from/emailAddress, receivedAt
            Defaults to "displayName".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            mailFolderInfo/id, mailFolderInfo/name, from/name, from/emailAddress, toRecipients/name, toRecipients/emailAddress,ccRecipients/emailAddress,ccRecipients/name, subject, receivedAt
            Defaults to "".

        Returns:
            Response: API response object.
        """
        path: str = (
            f"{self.ms365_indexed_emails}?backup={csp_ms365_backup_id}?limit={limit}&offset={offset}&sort={sort}"
        )
        # only add "filter" if it's provided
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        return response

    def get_ms365_indexed_events(
        self,
        csp_ms365_backup_id,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "calendarInfo/name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[IndexedEventList, ErrorResponse]:
        """Get list of MS365 indexed events from backup
           GET /backup-recovery/v1beta1/ms365-indexed-events
        Args:
            csp_ms365_backup_id (UUID): MS365 Backup ID which is to be used for getting indexed events.

            offset (int, optional): The number of items to omit from the begining of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.
            Defaults to 20.

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending).
            Sorting is supported on the following  properties:
            calendarInfo/Name, OrganizerInfo/emailAddress
            Defaults to "calendarInfo/name".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            calendarInfo/Name, calendarInfo/id, organizerInfo/name, organizerInfo/emailAddress, subject
            Defaults to "".
            expected_status_code (requests.codes, optional): Expected return status code. Defaults to requests.codes.ok.

        Returns:
            Union[IndexedEventList, ErrorResponse]: Either the list of MS365 indexed events or Error response will be returned.
        """
        response: Response = self.raw_get_ms365_indexed_events(csp_ms365_backup_id, limit, offset, sort, filter)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 indexed event list: {response.text}"
        logger.debug(f"response from get_ms365_indexed_events: {response.text}")
        if response.status_code == requests.codes.ok:
            return IndexedEventList.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def raw_get_ms365_indexed_events(
        self, csp_ms365_backup_id, limit: int = 1000, offset: int = 0, sort: str = "name", filter: str = ""
    ) -> Response:
        """Wrapper of get API call to MS365 indexed events.

        Args:
            csp_ms365_backup_id (UUID): MS365 Backup ID which is to be used for getting indexed contacts.

            offset (int, optional): The number of items to omit from the begining of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.
            Defaults to 20.

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending).
            Sorting is supported on the following  properties:
            calendarInfo/Name, OrganizerInfo/emailAddress
            Defaults to "calendarInfo/name".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            calendarInfo/Name, calendarInfo/id, organizerInfo/name, organizerInfo/emailAddress, subject
            Defaults to "".
        Returns:
            Response: API response object.
        """
        path: str = (
            f"{self.ms365_indexed_events}?backup={csp_ms365_backup_id}?limit={limit}&offset={offset}&sort={sort}"
        )
        # only add "filter" if it's provided
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        return response

    def get_ms365_indexed_tasks(
        self,
        csp_ms365_backup_id,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "title",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[IndexedTaskList, ErrorResponse]:
        """Get list of MS365 indexed tasks from backup
           GET /backup-recovery/v1beta1/ms365-indexed-tasks
        Args:
            csp_ms365_backup_id (UUID): MS365 Backup ID which is to be used for getting indexed tasks.

            offset (int, optional): The number of items to omit from the begining of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.
            Defaults to 20.

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending).
            Sorting is supported on the following  properties:
            title, createdAt
            Defaults to "title".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            title, createdAt, folderId, folderName, status
            Defaults to "".
            expected_status_code (requests.codes, optional): Expected return status code. Defaults to requests.codes.ok.

        Returns:
            Union[IndexedTaskList, ErrorResponse]: Either the list of MS365 indexed tasks or Error response will be returned.
        """
        response: Response = self.raw_get_ms365_indexed_tasks(csp_ms365_backup_id, limit, offset, sort, filter)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 indexed task list: {response.text}"
        logger.debug(f"response from get_ms365_indexed_tasks: {response.text}")
        if response.status_code == requests.codes.ok:
            return IndexedTaskList.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def raw_get_ms365_indexed_tasks(
        self, csp_ms365_backup_id, limit: int = 1000, offset: int = 0, sort: str = "name", filter: str = ""
    ) -> Response:
        """Wrapper of get API call to MS365 indexed tasks.

        Args:
            csp_ms365_backup_id (UUID): MS365 Backup ID which is to be used for getting indexed contacts.

        Returns:
            Response: API response object.
        """
        path: str = f"{self.ms365_indexed_tasks}?backup={csp_ms365_backup_id}?limit={limit}&offset={offset}&sort={sort}"
        # only add "filter" if it's provided
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        return response
