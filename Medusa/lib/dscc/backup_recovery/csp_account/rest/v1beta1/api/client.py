from uuid import UUID
import requests
from requests import Response
from lib.common.common import delete, get, patch, post

from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.payload.csp_account_create import (
    CSPAccountCreate,
)
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.payload.csp_account_update import (
    CSPAccountUpdate,
)
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.csp_account import (
    CSPAccount,
    CSPAccountList,
    CSPOnboardingTemplate,
)
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.csp_type import CspType
from lib.common.enums.task_status import TaskStatus
from lib.dscc.tasks.api.tasks import TaskManager
from lib.common.users.user import User


class CloudAccountManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.base_url = f"{self.dscc['atlantia-url']}"
        self.api_group = config["API-GROUP"]
        self.hybrid_cloud_url = (
            f"{self.dscc['atlantia-url']}/{self.api_group['hybrid-cloud']}/{self.dscc['beta-version']}"
        )
        self.hybrid_cloud_url_alpha1_version = (
            f"{self.dscc['atlantia-url']}/{self.api_group['hybrid-cloud']}/{self.dscc['alpha1-version']}"
        )
        self.backup_recovery_url = (
            f"{self.dscc['atlantia-url']}/{self.api_group['backup-recovery']}/{self.dscc['beta-version']}"
        )
        self.csp_accounts = self.atlantia_api["csp-accounts"]
        self.tasks = TaskManager(user)

    def get_csp_accounts(
        self,
        offset: int = 0,
        limit: int = 1000,
        sort: str = "name asc",
        filter: str = "",
    ) -> CSPAccountList:
        """Retrieves a list of all available CSP accounts

        Args:
            offset (int, optional): number of items from the beginning of the result set to the first item included in the response. Defaults to 0.
            limit (int, optional): limit is the maximum number of items to include in the response. Defaults to 1000.
            sort (str, optional):  A resource property by which to sort, followed by an optional direction indicator ("asc" or "desc"). Defaults to "name asc".
            filter (str, optional): used to filter the list of CSP accounts returned in the response. Defaults to "".

        Returns:
            CSPAccountList: List of available CSP accounts
        """
        response: Response = self.raw_get_csp_accounts(offset=offset, limit=limit, sort=sort, filter=filter)
        assert (
            response.status_code == requests.codes.ok
        ), f"GET /csp_accounts failed with status_code: {response.status_code}  response.text: {response.text}"
        return CSPAccountList.from_json(response.text)

    # renamed from 'get_csp_accounts_return_response'
    def raw_get_csp_accounts(
        self,
        offset: int = 0,
        limit: int = 1000,
        sort: str = "name asc",
        filter: str = "",
    ) -> Response:
        """Returns raw response of GET call for CSP Account

        Args:
            offset (int, optional): number of items from the beginning of the result set to the first item included in the response. Defaults to 0.
            limit (int, optional): limit is the maximum number of items to include in the response. Defaults to 1000.
            sort (str, optional):  A resource property by which to sort, followed by an optional direction indicator ("asc" or "desc"). Defaults to "name asc".
            filter (str, optional): used to filter the list of CSP accounts returned in the response. Defaults to "".

        Returns:
            Response: Raw response of GET call for CSP Account
        """
        path: str = f"{self.csp_accounts}?offset={offset}&limit={limit}&sort={sort}"
        # only add "filter" if it's provided
        if len(filter):
            path += f"&filter={filter}"
        response: Response = get(self.hybrid_cloud_url, path, headers=self.user.authentication_header)
        return response

    # GET /csp-accounts/{id}
    def get_csp_account_by_id(self, account_id: UUID) -> CSPAccount:
        """Returns a CSP account object by its ID

        Args:
            account_id (UUID): ID of a CSP account

        Returns:
            CSPAccount: CSP Account found by its ID
        """
        path: str = f"{self.csp_accounts}/{account_id}"
        response: Response = get(self.hybrid_cloud_url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == requests.codes.ok
        ), f"GET /csp_accounts/{account_id} Failed with status_code: {response.status_code}  response.text: {response.text}"
        return CSPAccount.from_json(response.text)

    # GET /csp-accounts?filter=name eq '<name>'
    def get_csp_account_by_name(self, name: str) -> CSPAccount:
        """Returns a CSP Account found by its name

        Args:
            name (str): Name of the account

        Returns:
            CSPAccount: CSP Account found by its name
        """
        path: str = f"{self.csp_accounts}?filter=name eq '{name}'"
        response: Response = get(self.hybrid_cloud_url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == requests.codes.ok
        ), f"GET /csp_accounts Failed with status_code: {response.status_code}  response.text: {response.text}"
        csp_account_list: CSPAccountList = CSPAccountList.from_json(response.text)
        return csp_account_list.items[-1] if csp_account_list.total > 0 else None

    # GET /csp-accounts/{id}/onboardingtemplate
    def get_csp_account_onboarding_template(self, account_id: UUID) -> CSPOnboardingTemplate:
        """Retrieves the onboarding template for a CSP account

        Args:
            account_id (UUID): ID of the CSP account

        Returns:
            CSPOnboardingTemplate: CSPOnboardingTemplate object
        """
        path: str = f"{self.csp_accounts}/{account_id}/onboardingtemplate"
        response: Response = get(
            self.hybrid_cloud_url_alpha1_version,
            path,
            headers=self.user.authentication_header,
        )
        assert (
            response.status_code == requests.codes.ok
        ), f"GET /csp-accounts/{account_id}/onboardingtemplate Failed with status_code: {response.status_code}  response.text: {response.text}"
        return CSPOnboardingTemplate.from_json(response.text)

    # renamed from 'delete_csp_account_return_response'
    def raw_delete_csp_account(self, account_id: UUID) -> Response:
        """Deletes a CSP Account by its ID and returns raw response

        Args:
            account_id (UUID): ID of the account

        Returns:
            Response: Raw response
        """
        path: str = f"{self.csp_accounts}/{account_id}"
        response: Response = delete(self.hybrid_cloud_url, path, headers=self.user.authentication_header)
        return response

    def delete_csp_account(self, account_id: UUID) -> str:
        """Tries to delete a CSP Account by its ID and expects a success

        Args:
            account_id (UUID): ID of the CSP account

        Returns:
            str: Task ID of the delete action
        """
        response: Response = self.raw_delete_csp_account(account_id=account_id)
        sync_task_id = self.tasks.get_task_id_from_header(response)
        return sync_task_id

    # delete_csp_account_expect_failure and delete_csp_account_with_expectation functions are moved to
    # tests/steps/aws_protection/v1beta1/cloud_account_manager_steps.py file

    # renamed from 'create_csp_account_return_response'
    def raw_create_csp_account(
        self,
        csp_id: str,
        name: str,
        csp_type: CspType = CspType.AWS,
    ) -> Response:
        """Creates a CSP account account of the specified csp_type

        Args:
            csp_id (str): ID of the CSP eg. AWS account ID or Azure Tenant ID
            name (str): Name of the account
            csp_type (CspType, optional): Defaults to CspType.AWS.

        Returns:
            Response: Raw response
        """
        payload = CSPAccountCreate(csp_id=csp_id, csp_type=csp_type, name=name).to_json()
        response: Response = post(
            uri=self.hybrid_cloud_url,
            path=self.csp_accounts,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        return response

    # POST /csp-accounts
    def create_csp_account(self, csp_id: str, name: str, csp_type: CspType = CspType.AWS) -> CSPAccount:
        """Creates a CSP account account of the specified csp_type

        Args:
            csp_id (str): ID of the CSP eg. AWS account ID or Azure Tenant ID
            name (str): Name of the account
            csp_type (CspType, optional): Defaults to CspType.AWS.

        Returns:
            CSPAccount: Created CSP Account object
        """
        response: Response = self.raw_create_csp_account(csp_id=csp_id, name=name, csp_type=csp_type)
        assert (
            response.status_code == requests.codes.created
        ), f"POST /csp-accounts for NAME: {name} ID: {csp_id} Failed with status_code: {response.status_code}  response.text: {response.text}"
        return CSPAccount.from_json(response.text)

    # POST /csp-accounts/{id}/validate
    def validate_csp_account(self, account_id: UUID) -> str:
        """Validates a CSP account by its ID

        Args:
            account_id (UUID): ID of the CSP account

        Returns:
            str: Task ID of the validate account operation
        """
        path: str = f"{self.csp_accounts}/{account_id}/validate"
        response: Response = post(self.hybrid_cloud_url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == requests.codes.accepted
        ), f"POST /csp-accounts/{account_id}/validate Failed with status_code: {response.status_code}  response.text: {response.text}"

        # Validating task status
        sync_task_id = self.tasks.get_task_id_from_header(response)
        sync_task_status = self.tasks.wait_for_task(sync_task_id, timeout=180).upper()
        assert (
            sync_task_status == TaskStatus.success.value or sync_task_status == TaskStatus.failed.value
        ), f"Actual:{sync_task_status}Expected[{TaskStatus.success.value}]||{TaskStatus.failed.value}]"
        return sync_task_id

    def modify_csp_account(self, account_id: UUID, name: str, suspended: bool) -> str:
        """Toggles account's 'suspended' state and 'name' field

        Args:
            account_id (UUID): ID of the CSP account
            name (str): Name of the CSP account
            suspended (bool): Set 'True' to suspend, set 'False' to resume

        Returns:
            str: Task ID of the modify account operation
        """
        response = self.raw_modify_csp_account(
            account_id,
            CSPAccountUpdate(name=name, suspended=suspended).to_json(),
            requests.codes.accepted,
        )

        # Validating task status
        sync_task_id = self.tasks.get_task_id_from_header(response)
        sync_task_status = self.tasks.wait_for_task(sync_task_id, timeout=180).upper()
        assert (
            sync_task_status == TaskStatus.success.value or sync_task_status == TaskStatus.failed.value
        ), f"Actual:{sync_task_status}Expected[{TaskStatus.success.value}]||{TaskStatus.failed.value}]"
        return sync_task_id

    # PATCH /csp-accounts/{id}
    def raw_modify_csp_account(self, account_id: UUID, payload: str, expected_status_code: int) -> Response:
        """Modifies the 'suspended' state and 'name' field of an account

        Args:
            account_id (UUID): ID of the CSP account
            payload (str): Payload to modify an account
            expected_status_code (int): requests.codes.bad_request or requests.codes.accepted.

        Returns:
            Response: Raw response of modify account operation
        """
        path: str = f"{self.csp_accounts}/{account_id}"
        response: Response = patch(
            self.hybrid_cloud_url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert (
            response.status_code == expected_status_code
        ), f"PATCH /csp-accounts/{account_id} Failed with status_code: {response.status_code}  response.text: {response.text}"
        return response

    # negative_modify_csp_account function has been moved to
    # tests/steps/aws_protection/v1beta1/cloud_account_manager_steps.py file

    # Internal API. Refer DCS-9444
    # POST /csp-accounts/resync
    def resync_csp_accounts_return_response(self) -> Response:
        """Resyncs an account

        Returns:
            Response: Raw response of resync operation
        """
        path: str = f"{self.csp_accounts}/resync"
        response: Response = post(uri=self.base_url, path=path, headers=self.user.authentication_header)
        return response

    # POST /csp-accounts/resync
    def resync_csp_accounts(self) -> None:
        """Resyncs an account"""
        response: Response = self.resync_csp_accounts_return_response()
        assert (
            response.status_code == requests.codes.no_content
        ), f"POST /csp-accounts/resync Failed with status_code: {response.status_code}  response.text: {response.text}"

    # POST /csp-accounts/{id}/unprotect
    def unprotect_csp_account(
        self,
        account_id: UUID,
        delete_backups: bool = True,
        expected_status_code: int = requests.codes.accepted,
    ) -> Response:
        """
        Deletes backups and protection jobs for assets in a cloud account

        Args:
            account_id (UUID): CSP Account ID
            delete_backups (bool, optional): To delete of backups while unprotect account and only value "True" is accepted at the moment. Defaults to True.
            expected_status_code (int, optional): Expected status code. Defaults to requests.no_content.

        Returns:
            Response: Returns the response of Unprotect Account API Call
        """
        # delete-backups=true is mandatory query filter for unprotect
        path: str = f"{self.csp_accounts}/{account_id}/unprotect"
        if delete_backups:
            path += "?delete-backups=true"

        response: Response = post(
            self.backup_recovery_url,
            path,
            headers=self.user.authentication_header,
        )

        # Passed the status code check as parameter for other validations
        assert (
            response.status_code == expected_status_code
        ), f"POST csp-account/{account_id}/unprotect failed with status_code: {response.status_code}  response.text: {response.text}"

        # Returning value as response as the header "location" contains taskid
        # We can extract the taskid in wrapper method in CAM steps.
        return response

    # Auth / user context
    # def get_customer_id(self) -> str:
    # This function is now available in tests/e2e/aws_protection/context.py file
