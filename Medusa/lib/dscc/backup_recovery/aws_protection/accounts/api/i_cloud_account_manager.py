from typing import Protocol, Union, runtime_checkable

import requests

from lib.common.enums.csp_type import CspType
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import (
    CSPAccountModel,
    CSPAccountListModel,
    CSPAccountValidateModel,
    CSPOnboardingTemplateModel,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import GLCPErrorResponse


@runtime_checkable
class ICloudAccountManager(Protocol):
    def get_csp_accounts(
        self,
        offset: int = 0,
        limit: int = 1000,
        sort: str = "name",
        filter: str = "",
    ) -> CSPAccountListModel: ...

    def get_csp_account_by_id(self, csp_account_id: str) -> CSPAccountModel: ...

    def get_csp_account_by_name(self, name: str) -> CSPAccountModel: ...

    def get_csp_account_onboarding_template(self, csp_account_id: str) -> CSPOnboardingTemplateModel: ...

    def raw_delete_csp_account_status_code_task_id(self, csp_account_id: str) -> tuple[int, str]: ...

    def create_csp_account_status_code(self, csp_id: str, name: str, csp_type: CspType = CspType.AWS) -> int: ...

    def create_csp_account(self, csp_id: str, name: str, csp_type: CspType = CspType.AWS) -> CSPAccountModel: ...

    def modify_csp_account(self, csp_account_id: str, payload: str, expected_status_code: int) -> str: ...

    def resync_csp_accounts(self): ...

    # Skipping `get_customer_id` function as it was moved to context by Roger

    def unprotect_csp_account(
        self,
        account_id: str,
        delete_backups: bool = True,
        expected_status_code: int = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...

    def validate_csp_account(self, csp_account_id: str) -> CSPAccountValidateModel: ...
