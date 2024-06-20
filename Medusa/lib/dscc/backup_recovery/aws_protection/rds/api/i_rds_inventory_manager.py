import requests
from typing import Protocol, Union, runtime_checkable
from lib.dscc.backup_recovery.aws_protection.rds.domain_models.csp_rds_account_model import CSPRDSAccountModel
from lib.dscc.backup_recovery.aws_protection.rds.domain_models.csp_rds_instance_model import (
    CSPRDSInstanceListModel,
    CSPRDSInstanceModel,
)

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
    GLCPErrorResponse,
)


@runtime_checkable
class IRDSInventoryManager(Protocol):
    def get_csp_rds_instance_by_id(self, csp_rds_instance_id: str) -> CSPRDSInstanceModel: ...

    def get_csp_rds_instances(
        self,
        offset: int = 0,
        limit: int = 1000,
        filter: str = "",
        expected_status_code: int = requests.codes.ok,
    ) -> Union[CSPRDSInstanceListModel, ErrorResponse]: ...

    def refresh_rds_account(self, csp_account_id: str) -> Union[str, ErrorResponse]: ...

    def refresh_rds_account_status_code(self, csp_account_id: str) -> tuple[requests.codes, str]: ...

    def refresh_rds_instance(self, csp_rds_instance_id: str) -> Union[str, ErrorResponse]: ...

    def get_csp_rds_account_by_id(
        self, csp_rds_account_id: str, expected_status_code: int = requests.codes.ok
    ) -> Union[CSPRDSAccountModel, GLCPErrorResponse]: ...
