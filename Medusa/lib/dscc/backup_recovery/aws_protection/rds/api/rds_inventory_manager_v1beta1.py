import requests
import logging
from requests import Response
from typing import Union

from lib.common.common import get, post, get_task_id_from_header
from lib.common.config.config_manager import ConfigManager
from lib.common.users.user import User
from lib.dscc.backup_recovery.aws_protection.rds.domain_models.csp_rds_account_model import CSPRDSAccountModel
from lib.dscc.backup_recovery.aws_protection.rds.domain_models.csp_rds_instance_model import (
    CSPRDSInstanceListModel,
    CSPRDSInstanceModel,
)

from lib.dscc.backup_recovery.aws_protection.rds.models.csp_rds_account_v1beta1 import CSPRDSAccount
from lib.dscc.backup_recovery.aws_protection.rds.models.csp_rds_instance_v1beta1 import (
    CSPRDSInstance,
    CSPRDSInstanceList,
)

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
    GLCPErrorResponse,
)

logger = logging.getLogger()


class RDSInventoryManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        # blocks from INI file
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.api_group = config["API-GROUP"]
        self.virtualization_url = (
            f"{self.dscc['atlantia-url']}/{self.api_group['virtualization']}/{self.dscc['beta-version']}"
        )
        self.csp_rds_instances = self.atlantia_api["csp-rds-instances"]
        self.csp_rds_accounts = self.atlantia_api["csp-rds-accounts"]
        self.csp_accounts = self.atlantia_api["csp-accounts"]

    # GET /virtualization/v1beta1/csp-rds-instances/{id}
    def get_csp_rds_instance_by_id(self, csp_rds_instance_id: str) -> CSPRDSInstanceModel:
        """Returns details of a specified cloud service provider (CSP) RDS machine instance.

        Args:
            csp_rds_instance_id (str): Unique identifier of a CSP RDS machine instance

        Returns:
            CSPRDSInstanceModel: Details of a CSP RDS machine instance
        """
        path: str = f"{self.csp_rds_instances}/{csp_rds_instance_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        csp_rds_instance: CSPRDSInstance = CSPRDSInstance.from_json(response.text)
        return csp_rds_instance.to_domain_model()

    # GET /virtualization/v1beta1/csp-rds-instances
    def get_csp_rds_instances(
        self,
        offset: int = 0,
        limit: int = 1000,
        filter: str = "",
        expected_status_code: int = requests.codes.ok,
    ) -> Union[CSPRDSInstanceListModel, ErrorResponse]:
        """Returns a list of cloud service provider (CSP) RDS machine instances according to the given query parameters
            for paging

        Args:
            offset (int, optional): The number of items to omit from the beginning of the result set. Defaults to 0.
            limit (int, optional): The maximum number of items to include in the response. Defaults to 1000.
            expected_status_code(int): response code from the content
            filter (str, optional): Used to filter the set of resources returned in the response.
            “eq” : Is a property equal to value. Valid for number, boolean and string properties.
            Filters are supported on following attributes:
            - accountId
            - name
            - protectionStatus
        Returns:
            CSPRDSInstanceListModel: List of CSP RDS machine instances if rds instance found
            ErrorResponse: if rds instance not found return error response
        """
        path: str = f"{self.csp_rds_instances}?offset={offset}&limit={limit}&filter={filter}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        assert response.status_code == expected_status_code, response.text
        if response.status_code == requests.codes.ok:
            csp_rds_instance_list: CSPRDSInstanceList = CSPRDSInstanceList.from_json(response.text)
            return csp_rds_instance_list.to_domain_model()
        else:
            return ErrorResponse(**response.json())

    # POST /virtualization/v1beta1/csp-accounts/{id}/rds-refresh
    def _refresh_rds_account_raw(self, csp_account_id: str) -> Response:
        """Updates the RDS inventory with the latest information in a cloud account.

        Args:
            csp_account_id (str): Unique identifier of a cloud account

        Returns:
            response (Response): response of the API call
        """
        path: str = f"{self.csp_accounts}/{csp_account_id}/rds-refresh"
        response: Response = post(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # POST /virtualization/v1beta1/csp-accounts/{id}/rds-refresh
    def refresh_rds_account(self, csp_account_id: str):
        """Updates the RDS inventory with the latest information in a cloud account.

        Args:
            csp_account_id (str): Unique identifier of a cloud account

        Returns:
            task_id (str): Task ID
        """
        response: Response = self._refresh_rds_account_raw(csp_account_id=csp_account_id)
        assert response.status_code == requests.codes.accepted, response.content
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def refresh_rds_account_status_code(self, csp_account_id: str) -> tuple[requests.codes, str]:
        """Attempt an RDS Account refresh, returns the Response.status_code and TaskID if call is accepted.

        Args:
            csp_account_id (str): Unique identifier of a cloud account

        Returns:
            tuple[requests.codes, str]: Returns the Response.status_code and the TaskID if the status_code is accepted.
        """
        response: Response = self._refresh_rds_account_raw(csp_account_id=csp_account_id)

        task_id: str = ""
        if response.status_code == requests.codes.accepted:
            task_id = get_task_id_from_header(response)
        else:
            # to preserve the logging of this data from the original "perform_rds_inventory_refresh_with_retry()" call in RDS IM Steps file
            logger.warn(f"response.content = {response.content}")

        return response.status_code, task_id

    # POST /virtualization/v1beta1/csp-rds-instances/{id}/refresh
    def refresh_rds_instance(self, csp_rds_instance_id: str):
        """Updates the source properties of the specified machine instance to match the settings in the cloud account.

        Args:
            csp_rds_instance_id (str): Unique identifier (UUID) of an RDS instance

        Returns:
            task_id (str): Task ID
        """
        path: str = f"{self.csp_rds_instances}/{csp_rds_instance_id}/refresh"
        response: Response = post(self.virtualization_url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.accepted, response.content
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return ErrorResponse(**response.json())

    def get_csp_rds_account_by_id(
        self, csp_rds_account_id: str, expected_status_code: int = requests.codes.ok
    ) -> Union[CSPRDSAccountModel, GLCPErrorResponse]:
        """Gets a of cloud service provider (CSP) RDS account.

        Args:
            csp_rds_account_id (str): Unique identifier of a cloud account

        Returns:
            CSPRDSAccountModel: Get details of CSP RDS Account
        """
        path: str = f"{self.csp_rds_accounts}/{csp_rds_account_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        assert response.status_code == expected_status_code, response.content
        if response.status_code == requests.codes.ok:
            csp_rds_account: CSPRDSAccount = CSPRDSAccount.from_json(response.text)
            return csp_rds_account.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())
