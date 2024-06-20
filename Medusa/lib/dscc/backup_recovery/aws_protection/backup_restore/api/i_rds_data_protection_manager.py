from typing import Protocol, Union, runtime_checkable
import requests

from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_model import (
    CSPRDSInstanceBackupModel,
    CSPRDSInstanceBackupListModel,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_restore_payload_model import (
    PostRestoreCspRdsInstanceModel,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import GLCPErrorResponse


@runtime_checkable
class IRDSDataProtectionManager(Protocol):
    def get_csp_rds_instance_backups(
        self,
        csp_rds_id: str,
        limit: int = 20,
        offset: int = 0,
        filter: str = "",
    ) -> CSPRDSInstanceBackupListModel: ...

    def get_csp_rds_instance_backup_by_id(self, backup_id: str) -> CSPRDSInstanceBackupModel: ...

    def patch_csp_rds_instance_backup_by_id(
        self,
        backup_id: str,
        new_expires_at: str,
    ) -> CSPRDSInstanceBackupModel: ...

    def restore_csp_rds_instance(
        self,
        backup_id: str,
        rds_restore_payload: PostRestoreCspRdsInstanceModel,
        response_code: int = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...

    def delete_csp_rds_instance_backup_by_id(
        self, backup_id: str, expected_code: int = requests.codes.accepted
    ) -> Union[str, GLCPErrorResponse]: ...
