from typing import Protocol, runtime_checkable

from requests import codes
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_eks_k8s_app_backup_model import (
    CSPK8sAppBackupInfoModel,
    CSPK8sAppBackupListModel,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.patch_csp_eks_k8s_backup import PatchCSPK8sAppBackup
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.post_restore_csp_k8s_app import PostRestoreK8sApp


@runtime_checkable
class IEKSDataProtectionManager(Protocol):
    def get_csp_k8s_app_backups(
        self,
        csp_k8s_application_id: str,
        offset: int = 0,
        limit: int = 100,
        sort: str = "name",
        filter: str = "",
    ) -> CSPK8sAppBackupListModel: ...

    def delete_csp_k8s_app_backup(
        self,
        csp_k8s_application_id: str,
        backup_id: str,
    ) -> str: ...

    def get_csp_k8s_app_backup_details(
        self,
        csp_k8s_application_id: str,
        backup_id: str,
    ) -> CSPK8sAppBackupInfoModel: ...

    def update_csp_k8s_app_backup(
        self,
        csp_k8s_application_id: str,
        backup_id: str,
        patch_backup_payload: PatchCSPK8sAppBackup,
    ) -> str: ...

    def restore_csp_k8s_application(
        self,
        csp_k8s_application_id: str,
        restore_payload: PostRestoreK8sApp,
        return_restore: bool = True,
        negative: bool = False,
        expected_neg_test_response_code=codes.internal_server_error,
    ) -> str: ...
