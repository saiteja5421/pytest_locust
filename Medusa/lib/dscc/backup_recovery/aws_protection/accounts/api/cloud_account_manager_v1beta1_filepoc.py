from typing import Union
import logging

import requests
from lib.common.enums.csp_type import CspType

from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import (
    CSPAccountModel,
    CSPAccountListModel,
    CSPAccountValidateModel,
    CSPOnboardingTemplateModel,
    PatchCSPAccountModel,
)
from lib.dscc.backup_recovery.aws_protection.accounts.models.csp_account_v1beta1_filepoc import (
    CSPAccount,
    CSPAccountList,
    CSPAccountValidate,
    CSPOnboardingTemplate,
    PatchCSPAccount,
)
from lib.dscc.backup_recovery.aws_protection.accounts.payload.post_csp_account import PostCSPAccount
from lib.common.users.user import User
from lib.common.config.config_manager import ConfigManager
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import GLCPErrorResponse
from requests import codes, Response
from lib.common.common import get, post, patch, delete, get_task_id_from_header

logger = logging.getLogger()


class CloudAccountManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.base_url = f"{self.dscc['atlantia-url']}"
        self.api_group = config["API-GROUP"]
        self.backup_recovery_url = (
            f"{self.dscc['atlantia-url']}/{self.api_group['backup-recovery']}/{self.dscc['beta-version']}"
        )
        self.virtualization_url = (
            f"{self.dscc['atlantia-url']}/{self.api_group['virtualization']}/{self.dscc['beta-version']}"
        )
        self.virtualization_url_alpha1_version = (
            f"{self.dscc['atlantia-url']}/{self.api_group['virtualization']}/{self.dscc['alpha1-version']}"
        )
        self.csp_accounts = self.atlantia_api["csp-accounts"]

    # GET /csp-accounts
    def get_csp_accounts(
        self, offset: int = 0, limit: int = 1000, sort: str = "name", filter: str = ""
    ) -> CSPAccountListModel:
        response: Response = self._raw_get_csp_accounts(offset=offset, limit=limit, sort=sort, filter=filter)
        assert (
            response.status_code == codes.ok
        ), f"GET csp-account/?{offset=}&{sort=}&{filter=} Failed with status_code: {response.status_code}  response.text: {response.text}"
        csp_accounts_list: CSPAccountList = CSPAccountList.from_json(response.text)
        return csp_accounts_list.to_domain_model()

    def _raw_get_csp_accounts(
        self, offset: int = 0, limit: int = 1000, sort: str = "name", filter: str = ""
    ) -> Response:
        path: str = f"{self.csp_accounts}?offset={offset}&limit={limit}&sort={sort}"
        # only add "filter" if it's provided
        if len(filter):
            path += f"&filter={filter}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # GET /csp-accounts/{id}
    def get_csp_account_by_id(self, csp_account_id: str) -> CSPAccountModel:
        path: str = f"{self.csp_accounts}/{csp_account_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == codes.ok
        ), f"GET /csp_accounts/{csp_account_id} Failed with status_code: {response.status_code}  response.text: {response.text}"
        csp_account: CSPAccount = CSPAccount.from_json(response.text)
        return csp_account.to_domain_model()

    # GET /csp-accounts?filter=name eq '<name>'
    def get_csp_account_by_name(self, name: str) -> CSPAccountModel:
        path: str = f"{self.csp_accounts}?filter=name eq '{name}'"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == codes.ok
        ), f"GET /csp_accounts Failed with status_code: {response.status_code}  response.text: {response.text}"
        csp_account_list = CSPAccountList.from_json(response.text)
        csp_account: CSPAccount = csp_account_list.items[-1] if csp_account_list.total > 0 else None
        return csp_account.to_domain_model() if csp_account else None

    # GET /csp-accounts/{id}/onboardingtemplate
    def get_csp_account_onboarding_template(self, csp_account_id: str) -> CSPOnboardingTemplateModel:
        path: str = f"{self.csp_accounts}/{csp_account_id}/onboardingtemplate"
        response: Response = get(self.virtualization_url_alpha1_version, path, headers=self.user.authentication_header)
        assert (
            response.status_code == codes.ok
        ), f"GET /csp-accounts/{csp_account_id}/onboardingtemplate Failed with status_code: {response.status_code}  response.text: {response.text}"
        csp_onboarding_template: CSPOnboardingTemplate = CSPOnboardingTemplate.from_json(response.text)
        return csp_onboarding_template.to_domain_model()

    def _raw_delete_csp_account(self, csp_account_id: str) -> Response:
        path: str = f"{self.csp_accounts}/{csp_account_id}"
        response: Response = delete(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def raw_delete_csp_account_status_code_task_id(self, csp_account_id: str) -> tuple[int, str]:
        response: Response = self._raw_delete_csp_account(csp_account_id=csp_account_id)
        sync_task_id = get_task_id_from_header(response)
        return response.status_code, sync_task_id

    # POST /csp-accounts
    def _raw_create_csp_account(self, csp_id: str, name: str, csp_type: CspType = CspType.AWS) -> Response:
        payload = PostCSPAccount(csp_id=csp_id, name=name, csp_type=csp_type).to_json()
        response: Response = post(
            uri=self.virtualization_url,
            path=self.csp_accounts,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        return response

    def create_csp_account_status_code(self, csp_id: str, name: str, csp_type: CspType = CspType.AWS) -> int:
        response: Response = self._raw_create_csp_account(csp_id=csp_id, name=name, csp_type=csp_type)
        return response.status_code

    # POST /csp-accounts
    def create_csp_account(self, csp_id: str, name: str, csp_type: CspType = CspType.AWS) -> CSPAccountModel:
        response: Response = self._raw_create_csp_account(csp_id=csp_id, name=name, csp_type=csp_type)
        assert (
            response.status_code == codes.created
        ), f"POST /csp-accounts for NAME: {name} ID: {csp_id} Failed with status_code: {response.status_code}  response.text: {response.text}"
        csp_account: CSPAccount = CSPAccount.from_json(response.text)
        return csp_account.to_domain_model()

    # PATCH /csp-accounts/{id}
    def modify_csp_account(self, csp_account_id: str, payload: PatchCSPAccountModel, expected_status_code: int) -> str:
        path: str = f"{self.csp_accounts}/{csp_account_id}"
        payload = PatchCSPAccount.from_domain_model(payload)
        response: Response = patch(
            self.virtualization_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert (
            response.status_code == expected_status_code
        ), f"PATCH /csp-accounts/{csp_account_id} Failed with status_code: {response.status_code}  response.text: {response.text}"
        sync_task_id = get_task_id_from_header(response)
        return sync_task_id

    # POST /csp-accounts/resync
    def _resync_csp_accounts_return_response(self) -> Response:
        path: str = f"{self.csp_accounts}/resync"
        response: Response = post(uri=self.base_url, path=path, headers=self.user.authentication_header)
        return response

    # POST /csp-accounts/resync
    def resync_csp_accounts(self):
        response: Response = self._resync_csp_accounts_return_response()
        assert (
            response.status_code == codes.no_content
        ), f"POST /csp-accounts/resync Failed with status_code: {response.status_code}  response.text: {response.text}"

    # POST /csp-accounts/{id}/unprotect
    def _raw_unprotect_csp_account(
        self,
        account_id: str,
        delete_backups: bool = True,
    ) -> Response:
        """
        Deletes backups and protection jobs for assets in a cloud account

        Args:
            account_id (str): CSP Account ID
            delete_backups (bool, optional): To delete of backups while unprotect account and only value "True" is accepted at the moment. Defaults to True.

        Returns:
            Response: Returns the response of Unprotect Account API Call
        """
        # delete-backups=true is mandatory query filter for unprotect
        path: str = f"{self.csp_accounts}/{account_id}/unprotect?delete-backups={str(delete_backups).lower()}"

        response: Response = post(
            self.backup_recovery_url,
            path,
            headers=self.user.authentication_header,
        )

        return response

    def unprotect_csp_account(
        self,
        account_id: str,
        delete_backups: bool = True,
        expected_status_code: int = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        """
        Deletes backups and protection jobs for assets in a cloud account

        Args:
            account_id (str): CSP Account ID
            delete_backups (bool, optional): To delete of backups while unprotect account and only value "True" is accepted at the moment. Defaults to True.
            expected_status_code (int, optional): Expected status code. Defaults to requests.codes.accepted.

        Returns:
            str: Task ID of the unprotect action if the response is successful else returns GLCPErrorResponse
        """
        response: Response = self._raw_unprotect_csp_account(
            account_id=account_id,
            delete_backups=delete_backups,
        )

        assert (
            response.status_code == expected_status_code
        ), f"POST csp-account/{account_id}/unprotect failed with status_code: {response.status_code}  response.text: {response.text}"

        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_validate_csp_account(self, csp_account_id: str) -> Response:
        """Triggers csp account validation and returns the response

        Args:
            csp_account_id (str): csp account id to validate

        Returns:
            Response: request response
        """
        path: str = f"{self.csp_accounts}/{csp_account_id}/validate"
        response: Response = post(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def validate_csp_account(self, csp_account_id: str) -> CSPAccountValidateModel:
        """Triggers csp account validation and returns the response

        Args:
            csp_account_id (str): csp account id to validate

        Returns:
            CSPAccountValidateModel | GLCPErrorResponse
        """
        response: Response = self._raw_validate_csp_account(csp_account_id)
        assert (
            response.status_code == codes.accepted
        ), f"POST /csp-accounts/{csp_account_id}/validate Failed with status_code: {response.status_code}  response.text: {response.text}"
        csp_account_validate: CSPAccountValidate = CSPAccountValidate.from_json(response.text)
        csp_account_validate_model: CSPAccountValidateModel = csp_account_validate.to_domain_model()
        csp_account_validate_model.task_id = get_task_id_from_header(response)

        if response.status_code == requests.codes.accepted:
            return csp_account_validate_model
        else:
            return GLCPErrorResponse(**response.json())
