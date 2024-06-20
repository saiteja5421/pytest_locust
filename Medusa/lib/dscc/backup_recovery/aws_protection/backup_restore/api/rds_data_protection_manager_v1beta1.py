import requests
import logging
from requests import Response
from typing import Union

# Internal libraries
from lib.common.common import get, patch, post, delete, get_task_id_from_header
from lib.common.config.config_manager import ConfigManager
from lib.common.users.user import User

from lib.dscc.backup_recovery.aws_protection.backup_restore.models.csp_rds_instance_backup_v1beta1 import (
    CSPRDSInstanceBackup,
    CSPRDSInstanceBackupList,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.csp_rds_backup_restore_payload_v1beta1 import (
    PostRestoreCspRdsInstance,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_model import (
    CSPRDSInstanceBackupModel,
    CSPRDSInstanceBackupListModel,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.patch_csp_rds_instance_backup import (
    PatchCSPRDSInstanceBackup,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_restore_payload_model import (
    PostRestoreCspRdsInstanceModel,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    GLCPErrorResponse,
)

logger = logging.getLogger()


class RDSDataProtectionManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        # blocks from INI file
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        # https://scdev01-app.qa.cds.hpe.com/backup-recovery/v1beta1
        self.beta_url = (
            f"{self.dscc['atlantia-url']}/{self.atlantia_api['backup-recovery']}/{self.dscc['beta-version']}"
        )
        self.csp_rds_instance_backups = self.atlantia_api["csp-rds-instance-backups"]

    # GET /backup-recovery/v1beta1/csp-rds-instance-backups?filter="assetInfo/id eq '{csp_rds_id}'"
    def get_csp_rds_instance_backups(
        self,
        csp_rds_id: str,
        limit: int = 20,
        offset: int = 0,
        filter: str = "",
    ) -> CSPRDSInstanceBackupListModel:
        """Returns all the backups for the provided csp_rds_id

        Args:
            csp_rds_id (str): DB ID
            limit (int, optional): The maximum number of items to include in the response. Defaults to 20.
            offset (int, optional): The number of items to omit from the beginning of the result set. Defaults to 0.
            filter (str, optional): An expression by which to filter the results. Defaults to "".
            These fields can be used for filtering:
                backupType
                state
                status

        Returns:
            CSPRDSInstanceBackupListModel: List of CSPRDSInstanceBackup
        """
        # initial filter string for "assetInfo/id"
        backup_filter = f"assetInfo/id eq '{csp_rds_id}'"
        # if a "filter" value was provided, add it to the backup_filter string
        if filter:
            backup_filter += f" and {filter}"

        path: str = f"{self.csp_rds_instance_backups}?filter={backup_filter}&limit={limit}&offset={offset}"

        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        csp_rds_backup_list: CSPRDSInstanceBackupList = CSPRDSInstanceBackupList.from_json(response.text)
        return csp_rds_backup_list.to_domain_model()

    # GET /backup-recovery/v1beta1/csp-rds-instance-backups/<backup_id>
    def get_csp_rds_instance_backup_by_id(self, backup_id: str) -> CSPRDSInstanceBackupModel:
        """Returns details of a specified cloud service provider (CSP) RDS machine instance backup

        Args:
            backup_id (str): Unique identifier of a CSP RDS machine instance backup

        Returns:
            CSPRDSInstanceBackupModel: Details of a CSP RDS machine instance backup
        """
        path: str = f"{self.csp_rds_instance_backups}/{backup_id}"

        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        csp_rds_backup: CSPRDSInstanceBackup = CSPRDSInstanceBackup.from_json(response.text)
        return csp_rds_backup.to_domain_model()

    # PATCH /backup-recovery/v1beta1/csp-rds-instance-backups/{backup_id}
    def patch_csp_rds_instance_backup_by_id(
        self,
        backup_id: str,
        new_expires_at: str,
    ) -> CSPRDSInstanceBackupModel:
        """Update CSP RDS machine instance backup

        Args:
            backup_id (str): Unique identifier of a CSP RDS machine instance backup
            new_expires_at (str): New retention period datetime in str.
            The retention period needs to be specified as an absolute value of UTC.

        Returns:
            CSPRDSInstanceBackupModel: Updated backup
        """
        aws_backup_patch: PatchCSPRDSInstanceBackup = PatchCSPRDSInstanceBackup(
            expires_at=new_expires_at,
        )
        path: str = f"{self.csp_rds_instance_backups}/{backup_id}"
        payload = aws_backup_patch.to_json()
        logger.info(f"Patch CSP RDS Instance Backup Payload = {payload}")
        response: Response = patch(
            self.beta_url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == requests.codes.ok, response.content
        csp_rds_backup: CSPRDSInstanceBackup = CSPRDSInstanceBackup.from_json(response.text)
        return csp_rds_backup.to_domain_model()

    # POST /backup-recovery/v1beta1/csp-rds-instance-backups/{backup_id}/restore
    def restore_csp_rds_instance(
        self,
        backup_id: str,
        rds_restore_payload: PostRestoreCspRdsInstanceModel,
        response_code: int = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        """
        Restore CSP RDS instance from a backup

        Args:
            backup_id (str): Unique identifier of a CSP RDS backup
            rds_restore_payload (PostRestoreCspRdsInstanceModel): RDS restore payload
            response_code (int): Status code to compare with response code. Defaults to requests.codes.accepted.

        Returns:
            Returns restore request task ID if successful else returns error response
        """
        path: str = f"{self.csp_rds_instance_backups}/{backup_id}/restore"
        payload = PostRestoreCspRdsInstance.from_domain_model(domain_model=rds_restore_payload)
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )

        assert response.status_code == response_code, response.content
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    # DELETE /backup-recovery/v1beta1/csp-rds-instance-backups/{backup_id}
    def delete_csp_rds_instance_backup_by_id(
        self, backup_id: str, expected_code: int = requests.codes.accepted
    ) -> Union[str, GLCPErrorResponse]:
        """
        Deletes a specific CSP RDS instance backup ID

        Args:
            backup_id (str): CSP RDS backup ID
            expected_code (int): Status code to compare with expected status code. Defaults to requests.codes.accepted

        Returns:
            Returns delete request task ID if successful else returns error response
        """
        path: str = f"{self.csp_rds_instance_backups}/{backup_id}"

        response: Response = delete(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == expected_code, response.content
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())
