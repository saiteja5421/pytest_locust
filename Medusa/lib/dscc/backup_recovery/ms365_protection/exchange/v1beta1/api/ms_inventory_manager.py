import logging
from typing import Union
from lib.common.users.user import User
from lib.common.common import get, post
import requests
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.csp_ms_users import (
    MS365CSPUser,
    MS365CSPUserList,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.csp_ms_groups import (
    MS365CSPGroup,
    MS365CSPGroupList,
)
from lib.dscc.tasks.api.tasks import TaskManager
from lib.common.config.config_manager import ConfigManager
from requests import Response

logger = logging.getLogger()


class MSInventoryManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.ms365_api = config["MS365-API"]
        self.api_group = config["API-GROUP"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['atlantia-url']}/{self.api_group['backup-recovery']}/{self.dscc['alpha1-version']}"
        self.virtualization_url = (
            f"{self.dscc['atlantia-url']}/{self.api_group['virtualization']}/{self.dscc['beta-version']}"
        )
        self.csp_accounts = self.atlantia_api["csp-accounts"]
        self.csp_ms365_groups = self.ms365_api["ms365-groups"]
        self.csp_ms365_users = self.ms365_api["ms365-users"]
        self.tasks = TaskManager(user)

    def trigger_ms365_inventory_refresh(self, csp_account_id: str) -> str:
        """Triggers update of the MS 365 inventory with latest information in the cloud account
            POST /hybrid-cloud/v1beta1/csp-accounts/{id}/ms365-refresh

        Args:
            csp_account_id (str): Unique identifier of a cloud account

        Returns:
            str: task uri that can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_accounts}/{csp_account_id}/ms365-refresh"
        response: Response = post(self.virtualization_url, path, headers=self.user.authentication_header)
        return self.tasks.get_task_id_from_header(response)

    def get_ms365_csp_users_list(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[MS365CSPUserList, ErrorResponse]:
        """Get list of MS365 CSP Users
           GET /hybrid-cloud/v1beta1/ms365-users
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
            accountInfo/id, cspInfo/ms365Id, cspInfo/mailBoxInfo/size, cspInfo/mailBoxInfo/count,
            id, name, protectionStatus, state, createdAt, updatedAt
            Defaults to "name".

            filter (str, optional): A string which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering: name, state, protectionStatus, accountInfo/id,
            protectionGroupInfo/id
            Defaults to "".

        Returns:
            MS365CSPUserList: Returns a list of cloud service provider (CSP) MS 365 Users
            ErrorResponse: if eks instance not found return error response
        """

        path: str = f"{self.csp_ms365_users}?offset={offset}&limit={limit}&sort={sort}"
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == expected_status_code, f"Error while retrieving ms365 users list: {response.text}"
        if response.status_code == requests.codes.ok:
            return MS365CSPUserList.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    # GET /hybrid-cloud/v1beta1/ms365-users/{id}
    def get_ms365_csp_user_by_id(
        self,
        ms365_csp_user_id: str,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[MS365CSPUser, ErrorResponse]:
        """Returns details of a specified ms365 user.
           GET /hybrid-cloud/v1beta1/ms365-users/{id}

        Args:
            ms365_csp_user_id (str): Unique identifier of a ms365 csp user

        Returns:
            MS365CSPUser: Details of a ms365 csp user
        """
        path: str = f"{self.csp_ms365_users}/{ms365_csp_user_id}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 user details by id: {response.text}"
        logger.debug(f"response from get_ms365_csp_user_by_id: {response.text}")
        if response.status_code == requests.codes.ok:
            return MS365CSPUser.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    def get_ms365_csp_groups_list(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[MS365CSPGroupList, ErrorResponse]:
        """Get list of MS365 CSP Groups
           GET /hybrid-cloud/v1beta1/ms365-groups
        Args:
            offset (int, optional): The number of items to omit from the beginning of the
            result set. The offset and limit query parameters are used in conjunction
            for pagination, for example "offset=30&limit=10" indicates the fourth page
            of 10 items.
            Defaults to 20.

            limit (int, optional): The maximum number of items to include in the response.
            Defaults to 0.

            sort (str, optional): A resource property by which to sort, followed by an optional
            direction indicator ("asc" or "desc", default: ascending).
            Sorting is supported on the following properties: id, name, accountInfo/id.
            Defaults to "name".

            filter (str, optional): A str which contains one or more expressions by which to filter the results.
            The str item 'contains' expression can be used to filter the results based on case insensitive substring match.
            These fields can be used for filtering: accountInfo/id, name
            Defaults to "".

        Returns:
            MS365CSPGroupList: Returns a list of cloud service provider (CSP) MS 365 Groups
            ErrorResponse: if eks instance not found return error response
        """

        path: str = f"{self.csp_ms365_groups}?offset={offset}&limit={limit}&sort={sort}"
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 groups list: {response.text}"
        logger.debug(f"response from get_ms365_csp_groups_list: {response.text}")
        if response.status_code == requests.codes.ok:
            return MS365CSPGroupList.from_json(response.text)
        else:
            return ErrorResponse(**response.json())

    # GET /hybrid-cloud/v1beta1/ms365-groups/{id}
    def get_ms365_csp_group_by_id(
        self,
        ms365_csp_group_id: str,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[MS365CSPGroup, ErrorResponse]:
        """Returns details of a specified ms365 user.
           GET /hybrid-cloud/v1beta1/ms365-groups/{id}

        Args:
            ms365_csp_group_id (str): Unique identifier of a ms365 csp group

        Returns:
            MS365CSPGroup: Details of a ms365 csp group
        """
        path: str = f"{self.csp_ms365_groups}/{ms365_csp_group_id}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == expected_status_code
        ), f"Error while retrieving ms365 group details by id: {response.content}"
        logger.debug(f"response from get_ms365_csp_group_by_id: {response.text}")
        if response.status_code == requests.codes.ok:
            return MS365CSPGroup.from_json(response.text)
        else:
            return ErrorResponse(**response.json())
