from typing import Protocol, Union, runtime_checkable
import requests

from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import (
    CSPBackupListModel,
    CSPBackupModel,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_payload_model import (
    PostRestoreCspMachineInstanceModel,
    PostRestoreCspVolumeFromCspInstanceBackupModel,
    PostRestoreCspVolumeModel,
    PatchEC2EBSBackupsModel,
    PostImportSnapshotModel,
)

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import GLCPErrorResponse


@runtime_checkable
class IDataProtectionManager(Protocol):
    def restore_csp_machine_instance(
        self,
        backup_id: str,
        ec2_restore_payload: PostRestoreCspMachineInstanceModel,
        status_code: requests.codes = requests.codes.accepted,
    ) -> tuple[str, str]: ...

    def get_csp_machine_instance_backups(
        self,
        machine_instance_id: str,
        offset: int = 0,
        limit: int = 500,
        sort: str = "name",
        filter: str = "",
    ) -> CSPBackupListModel: ...

    def get_csp_machine_instance_backup_by_id(
        self,
        backup_id: str,
    ) -> CSPBackupModel: ...

    def delete_csp_machine_instance_backup_by_id(self, machine_instance_id: str, backup_id: str) -> str: ...

    def update_csp_machine_instance_backup(
        self,
        machine_instance_id: str,
        backup_id: str,
        patch_backup_payload: PatchEC2EBSBackupsModel,
    ) -> str: ...

    def restore_csp_volume(self, backup_id: str, ebs_restore_payload: PostRestoreCspVolumeModel) -> str: ...

    def restore_csp_volume_from_ec2_backup(
        self,
        backup_id: str,
        ebs_restore_payload: PostRestoreCspVolumeFromCspInstanceBackupModel,
        expected_status_code: int = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...

    def get_csp_volume_backups(
        self,
        volume_id: str,
        offset: int = 0,
        limit: int = 500,
        sort: str = "name",
        filter: str = "",
    ) -> CSPBackupListModel: ...

    def get_csp_volume_backup_by_id(self, volume_id: str, backup_id: str) -> CSPBackupModel: ...

    def delete_csp_volume_backup_by_id(self, volume_id: str, backup_id: str) -> str: ...

    def update_csp_volume_backup(
        self, volume_id: str, backup_id: str, patch_backup_payload: PatchEC2EBSBackupsModel
    ) -> str: ...

    def complete_transient_backup(self, customer_id: str, account_id: str, region: str): ...

    def import_account_snapshots_and_amis(
        self,
        csp_account_id: str,
        post_import_snapshot: PostImportSnapshotModel,
        expected_status_code: int = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...
