import logging
from lib.common.users.user import User
from lib.common.common import get, post, patch, delete
import requests
from typing import Union
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
)
from lib.dscc.tasks.api.tasks import TaskManager
from lib.common.config.config_manager import ConfigManager
from requests import Response
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.csp_ms_protection_groups import (
    MS365CSPProtectionGroup,
    MS365CSPProtectionGroupList,
    MS365CSPProtectionGroupUpdate,
    MS365CSPProtectionGroupCreate,
)

logger = logging.getLogger()


class MSProtectionGroupManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.ms365_api = config["MS365-API"]
        self.api_group = config["API-GROUP"]
        self.dscc = config["CLUSTER"]
        self.backup_recovery = self.atlantia_api["backup-recovery"]
        self.ms365_protection_groups = self.ms365_api["ms365-protection-groups"]
        self.url = f"{self.dscc['atlantia-url']}/{self.backup_recovery}/{self.dscc['beta-version']}"
        self.tasks = TaskManager(user)

    def get_ms365_protection_groups(
        self,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[MS365CSPProtectionGroupList, ErrorResponse]:
        """Get list of MS365 protection groups
           GET /backup-recovery/v1beta1/ms365-protection-groups
        Args:
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
            organizations/id, assetType, createdAt, description, id, membershipType, name, updatedAt
            Defaults to "name".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            membershipType, name, organizations/id
            Defaults to "".
            expected_status_code (requests.codes, optional): Expected return status code. Defaults to requests.codes.ok.

        Returns:
            Union[MS365CSPProtectionGroupList, ErrorResponse]: Either the list of MS365 protection groups or Error response will be returned.
        """
        response: Response = self.raw_get_ms365_protection_groups(limit, offset, sort, filter)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 protection groups list: {response.text}"
        logger.debug(f"response from get_ms365_csp_groups_list: {response.text}")
        if response.status_code == requests.codes.ok:
            return MS365CSPProtectionGroupList.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def raw_get_ms365_protection_groups(
        self, limit: int = 1000, offset: int = 0, sort: str = "name", filter: str = ""
    ) -> Response:
        """Wrapper of get API call to MS365 protection groups.

        Args:
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
            organizations/id, assetType, createdAt, description, id, membershipType, name, updatedAt
            Defaults to "name".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering:
            membershipType, name, organizations/id
            Defaults to "".

        Returns:
            Response: API response object.
        """
        path: str = f"{self.ms365_protection_groups}?limit={limit}&offset={offset}&sort={sort}"
        # only add "filter" if it's provided
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        return response

    def get_ms365_protection_group_by_id(
        self, protection_group_id: str, expected_status_code: requests.codes = requests.codes.ok
    ) -> Union[MS365CSPProtectionGroup, ErrorResponse]:
        """Get details of MS365 protection group by ID.
           GET /backup-recovery/v1beta1/ms365-protection-groups/{protection_group_id}
        Args:
            protection_group_id (str): ID of MS365 protection group to be queried.
            expected_status_code (requests.codes, optional): Expected API response code. Defaults to requests.codes.ok.

        Returns:
            Union[MS365CSPProtectionGroup, ErrorResponse]: Either the MS365 protection group object or error response object.
        """
        response: Response = self.raw_get_ms365_protection_group_by_id(protection_group_id)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 protection group by id: {response.text}"
        logger.debug(f"response from get_ms365_protection_group_by_id: {response.text}")
        if response.status_code == requests.codes.ok:
            return MS365CSPProtectionGroup.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def raw_get_ms365_protection_group_by_id(self, protection_group_id: str) -> Response:
        """Wrapper over get API call to get details of MS365 protection group by ID.

        Args:
            protection_group_id (str): Protection group ID to be queried.

        Returns:
            Response: API response object.
        """
        path: str = f"{self.ms365_protection_groups}/{protection_group_id}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        return response

    def create_ms365_protection_group(
        self,
        post_protection_group: MS365CSPProtectionGroupCreate,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> str:
        """API to create new MS 365 protection group.
           POST /backup-recovery/v1beta1/ms365-protection-groups
        Args:
            post_protection_group (MS365CSPProtectionGroupCreate): Object of type MS365CSPProtectionGroupCreate which will be used to created new MS365 protection group.
            expected_status_code (requests.codes, optional): Expected API response code. Defaults to requests.codes.accepted.

        Returns:
            str: Task ID of create protection group task.
        """
        response = self.raw_create_ms365_protection_group(post_protection_group)
        assert (
            response.status_code == expected_status_code
        ), f"Error while creating MS365 protection group: {response.text}"
        logger.debug(f"Response for create_ms365_protection_group: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def raw_create_ms365_protection_group(self, post_protection_group: MS365CSPProtectionGroupCreate) -> Response:
        """Wrapper over post request to create MS365 protection group.

        Args:
            post_protection_group (MS365CSPProtectionGroupCreate): Object of type MS365CSPProtectionGroupCreate which will be used to create new MS365 protection group.

        Returns:
            Response: API response object
        """
        payload = post_protection_group.to_json()
        response = post(
            self.url,
            self.ms365_protection_groups,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        return response

    def update_ms365_protection_group(
        self,
        protection_group_id: str,
        patch_custom_protection_group: MS365CSPProtectionGroupUpdate,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> str:
        """Patch request to update given MS 365 protection group.
           PATCH /backup-recovery/v1beta1/ms365-protection-groups/{protection_group_id}
        Args:
            protection_group_id (str): ID of MS365 protection group to be updated.
            patch_custom_protection_group (MS365CSPProtectionGroupUpdate): MS365CSPProtectionGroupUpdate object containing updated information for MS365 protection group.
            expected_status_code (requests.codes, optional): Expected API status code. Defaults to requests.codes.accepted.

        Returns:
            str: Task ID of update/edit MS365 protection group task.
        """
        response = self.raw_update_ms365_protection_group(
            protection_group_id=protection_group_id,
            patch_custom_protection_group=patch_custom_protection_group,
        )
        assert (
            response.status_code == expected_status_code
        ), f"Error while updating MS365 protection group: {response.text}"
        logger.debug(f"Response for update_ms365_protection_group: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def raw_update_ms365_protection_group(
        self,
        protection_group_id: str,
        patch_ms365_protection_group: MS365CSPProtectionGroupUpdate,
    ) -> Response:
        """Wrapper function over patch MS365 protection group API.

        Args:
            protection_group_id (str): ID of MS365 protection group to be updated.
            patch_ms365_protection_group (MS365CSPProtectionGroupUpdate): MS365CSPProtectionGroupUpdate object containing updated information of MS365 protection group.

        Returns:
            Response: API response object.
        """
        path = f"{self.ms365_protection_groups}/{protection_group_id}"
        payload = patch_ms365_protection_group.to_json()
        response = patch(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        return response

    def delete_ms365_protection_group(
        self, protection_group_id: str, expected_status_code: requests.codes = requests.codes.accepted
    ) -> str:
        """Delete given MS365 protection group identified by protection group id.
           DELETE /backup-recovery/v1beta1/ms365-protection-groups/{protection_group_id}
        Args:
            protection_group_id (str): ID of MS 365 protection group to be delete.
            expected_status_code (requests.codes, optional): Expected status code. Defaults to requests.codes.accepted.

        Returns:
            str: Task ID of delete MS365 protection group task.
        """
        response = self.raw_delete_ms365_protection_group(protection_group_id=protection_group_id)
        assert (
            response.status_code == expected_status_code
        ), f"Error while deleting MS365 protection group: {response.text}"
        logger.debug(f"Response for delete_ms365_protection_group: {response.text}")
        if response.status_code == requests.codes.accepted:
            return self.tasks.get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def raw_delete_ms365_protection_group(self, protection_group_id: str) -> Response:
        """Wrapper over delete MS365 protection group API.

        Args:
            protection_group_id (str): ID of MS365 protection group to be deleted.

        Returns:
            Response: API response object.
        """
        path = f"{self.ms365_protection_groups}/{protection_group_id}"
        response = delete(self.url, path, headers=self.user.authentication_header)
        return response
