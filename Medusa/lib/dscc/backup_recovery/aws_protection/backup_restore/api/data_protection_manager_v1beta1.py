from json import dumps
import logging
from typing import Union
import requests
from requests import codes, Response

from lib.common.common import get, post, patch, delete, get_task_id_from_header
from lib.common.config.config_manager import ConfigManager
from lib.common.users.user import User

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

from lib.dscc.backup_recovery.aws_protection.backup_restore.models.csp_backup_v1beta1 import CSPBackup, CSPBackupList
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.csp_backup_payload_v1beta1 import (
    PostRestoreCspMachineInstance,
    PostRestoreCspVolumeFromCspInstanceBackup,
    PostRestoreCspVolume,
    PatchEC2EBSBackups,
    PostImportSnapshot,
)

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import GLCPErrorResponse

logger = logging.getLogger()


class DataProtectionManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.beta_url = (
            f"{self.dscc['atlantia-url']}/{self.atlantia_api['backup-recovery']}/{self.dscc['beta-version']}"
        )
        self.csp_accounts = self.atlantia_api["csp-accounts"]
        self.import_csp_backups = self.atlantia_api["import-csp-backups"]
        self.csp_machine_instance_backups = self.atlantia_api["csp-machine-instance-backups"]
        self.csp_volume_backups = self.atlantia_api["csp-volume-backups"]

    # region csp_machine_instances

    def _raw_restore_csp_machine_instance(
        self,
        backup_id: str,
        ec2_restore_payload: PostRestoreCspMachineInstanceModel,
    ) -> Response:
        path: str = f"{self.csp_machine_instance_backups}/{backup_id}/restore"
        payload = PostRestoreCspMachineInstance.from_domain_model(domain_model=ec2_restore_payload)
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        return response

    def restore_csp_machine_instance(
        self,
        backup_id: str,
        ec2_restore_payload: PostRestoreCspMachineInstanceModel,
        status_code: requests.codes = requests.codes.accepted,
    ) -> tuple[str, str]:
        """
        Restore a CSP machine instance from a backup
        POST /backup-recovery/v1beta1/csp-machine-instance-backups/{backupId}/restore

        Args:
            backup_id (str): Unique identifier of a CSP instance backup
            ec2_restore_payload (PostRestoreCspMachineInstanceModel): Payload for restore post operation
            status_code (requests.codes): The expected status_code. Defaults to requests.codes.accepted

        Returns:
            tuple[str, str]: Returns TaskID and ErrorMessage (if any) from Response details after submitting the restore POST request
        """
        response: Response = self._raw_restore_csp_machine_instance(
            backup_id=backup_id, ec2_restore_payload=ec2_restore_payload
        )
        assert response.status_code == status_code, response.content

        task_id: str = ""
        error_message: str = ""
        # task_id only if accepted
        if response.status_code == requests.codes.accepted:
            task_id = get_task_id_from_header(response=response)
        else:
            error: GLCPErrorResponse = GLCPErrorResponse(**response.json())
            error_message = error.message

        return task_id, error_message

    def get_csp_machine_instance_backups(
        self,
        machine_instance_id: str,
        offset: int = 0,
        limit: int = 500,
        sort: str = "name",
        filter: str = "",
    ) -> CSPBackupListModel:
        """
        Get CSP backups of a specific CSP machine instance ID
        GET /backup-recovery/v1beta1/csp-machine-instance-backups

        Args:
            machine_instance_id (str): unique identifier of a CSP instance
            offset (int, optional): The number of items to omit from the beginning of the result set.  Defaults to 0.
            limit (int, optional): The maximum number of items to include in the response. Defaults to 100.
            sort (str, optional): A comma separated list of properties to sort by, followed by a direction indicator ("asc" or "desc"). Defaults to "name" These fields can be used for sorting: createdAt, expiresAt, state and status.
            filter (str, optional): An expression by which to filter the results. Defaults to "".

        Returns:
            CSPBackupListModel: List of CSP backups
        """
        filter = f"{filter} and" if filter else ""
        filter = f"{filter} assetInfo/id eq '{machine_instance_id}'"
        path: str = f"{self.csp_machine_instance_backups}?offset={offset}&limit={limit}&sort={sort}&filter={filter}&"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        csp_backup_list: CSPBackupList = CSPBackupList.from_json(response.text)
        return csp_backup_list.to_domain_model()

    def get_csp_machine_instance_backup_by_id(
        self,
        backup_id: str,
    ) -> CSPBackupModel:
        """
        Get details of a specific backup ID of a CSP machine instance
        GET /backup-recovery/v1beta1/csp-machine-instance-backups/{backup_id}

        Args:
            backup_id (str): CSP instance backup ID

        Returns:
            CSPBackupModel: CSP backup details
        """
        logger.info(f"Getting backup {backup_id}")
        path: str = f"{self.csp_machine_instance_backups}/{backup_id}"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        csp_backup: CSPBackup = CSPBackup.from_json(response.text)
        return csp_backup.to_domain_model()

    def delete_csp_machine_instance_backup_by_id(self, machine_instance_id: str, backup_id: str) -> str:
        """
        Deletes a specific backup of a CSP machine instance
        DELETE /backup-recovery/v1beta1/csp-machine-instance-backups/{backup_id}

        Args:
            machine_instance_id (str): Unique identifier of a CSP instance
            backup_id (str): CSP instance backup ID

        Returns:
            str: DELETE request task ID which can be used to monitor progress of the operation
        """
        logger.info(f"Deleting backup {backup_id} from ec2: {machine_instance_id}")
        path: str = f"{self.csp_machine_instance_backups}/{backup_id}"
        response: Response = delete(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.accepted, response.content
        return get_task_id_from_header(response)

    def update_csp_machine_instance_backup(
        self,
        machine_instance_id: str,
        backup_id: str,
        patch_backup_payload: PatchEC2EBSBackupsModel,
    ) -> str:
        """
        Updates a specific backup ID of a CSP machine instance
        PATCH /backup-recovery/v1beta1/csp-machine-instance-backups/{backup_id}

        Args:
            machine_instance_id (str): Unique identifier of a CSP instance
            backup_id (str): CSP instance backup ID
            patch_backup_payload (PatchEC2EBSBackupsModel): Payload for update backup request

        Returns:
            str: Update request task ID which can be used to monitor progress of the operation
        """
        logger.info(f"Updating backup {backup_id} from ec2: {machine_instance_id}")
        path: str = f"{self.csp_machine_instance_backups}/{backup_id}"
        payload = PatchEC2EBSBackups.from_domain_model(domain_model=patch_backup_payload)
        response: Response = patch(
            self.beta_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.accepted, response.content
        return get_task_id_from_header(response)

    # endregion

    # region csp_volumes

    def restore_csp_volume(self, backup_id: str, ebs_restore_payload: PostRestoreCspVolumeModel) -> str:
        """
        Restore a CSP volume from a backup
        POST /backup-recovery/v1beta1/csp-volume-backups/{backupId}/restore

        Args:
            backup_id (str): Unique identifier of a CSP instance backup_id
            ebs_restore_payload (PostRestoreCspVolumeModel): Payload for restore post operation

        Returns:
            str: Restore request task ID which can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_volume_backups}/{backup_id}/restore"
        payload = PostRestoreCspVolume.from_domain_model(domain_model=ebs_restore_payload)
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == requests.codes.accepted, response.content
        return get_task_id_from_header(response)

    def restore_csp_volume_from_ec2_backup(
        self,
        backup_id: str,
        ebs_restore_payload: PostRestoreCspVolumeFromCspInstanceBackupModel,
        expected_status_code: int = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        """
        Restores a csp volume from a csp volume backup created as part of a csp machine instance backup.
        POST /backup-recovery/v1beta1/csp-machine-instance-backups/{backupId}/restore-volume

        Args:
            backup_id (str): Unique identifier of a CSP instance backup
            ebs_restore_payload (PostRestoreCspVolumeFromCspInstanceBackupModel): Payload for restore post operation
            expected_status_code (int): Status code to compare with expected status code.
                                        Defaults to requests.codes.accepted.

        Returns:
            str: Restore request task ID which can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_machine_instance_backups}/{backup_id}/restore-volume"
        payload = PostRestoreCspVolumeFromCspInstanceBackup.from_domain_model(domain_model=ebs_restore_payload)
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, response.text

        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def get_csp_volume_backups(
        self,
        volume_id: str,
        offset: int = 0,
        limit: int = 500,
        sort: str = "name",
        filter: str = "",
    ) -> CSPBackupListModel:
        """
        Get CSP backups of a specific CSP volume
        GET /backup-recovery/v1beta1/csp-volume-backups

        Args:
            volume_id (str): unique identifier of a CSP volume
            offset (int, optional): The number of items to omit from the beginning of the result set.  Defaults to 0.
            limit (int, optional): The maximum number of items to include in the response. Defaults to 100.
            sort (str, optional): A comma separated list of properties to sort by, followed by a direction indicator ("asc" or "desc"). Defaults to "name" These fields can be used for sorting: createdAt, expiresAt, state and status.
            filter (str, optional): An expression by which to filter the results. Defaults to "" These fields can be used for filtering: backupType, state, status and consistency.

        Returns:
            CSPBackupListModel: List of CSP volume backups
        """
        filter = f"{filter} and" if filter else ""
        filter = f"{filter} assetInfo/id eq '{volume_id}'"
        path: str = f"{self.csp_volume_backups}?offset={offset}&limit={limit}&sort={sort}&filter={filter}"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        csp_backup_list: CSPBackupList = CSPBackupList.from_json(response.text)
        return csp_backup_list.to_domain_model()

    def get_csp_volume_backup_by_id(self, volume_id: str, backup_id: str) -> CSPBackupModel:
        """
        Get details of a specific backup ID of a CSP volume
        GET /backup-recovery/v1beta1/csp-volume-backups/{id}

        Args:
            volume_id (str): unique identifier of a CSP volume
            backup_id (str): CSP volume backup ID

        Returns:
            CSPBackupModel: CSP volume backup details
        """
        logger.info(f"Deleting backup {backup_id} from ec2: {volume_id}")
        path: str = f"{self.csp_volume_backups}/{backup_id}"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        csp_backup: CSPBackup = CSPBackup.from_json(response.text)
        return csp_backup.to_domain_model()

    def delete_csp_volume_backup_by_id(self, volume_id: str, backup_id: str) -> str:
        """
        Delete a specific backup of a CSP volume
        DELETE /backup-recovery/v1beta1/csp-volume-backups/{id}

        Args:
            volume_id (str): Unique identifier of a CSP volume
            backup_id (str): CSP volume backup ID

        Returns:
            str: Delete request task ID which can be used to monitor progress of the operation
        """
        logger.info(f"Deleting backup {backup_id} from ec2: {volume_id}")
        path: str = f"{self.csp_volume_backups}/{backup_id}"
        response: Response = delete(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.accepted, response.content
        return get_task_id_from_header(response)

    def update_csp_volume_backup(
        self, volume_id: str, backup_id: str, patch_backup_payload: PatchEC2EBSBackupsModel
    ) -> str:
        """
        Get details of a specific backup ID of a CSP volume
        PATCH /backup-recovery/v1beta1/csp-volume-backups/{id}

        Args:
            volume_id (str): Unique identifier of a CSP volume
            backup_id (str): CSP volume backup ID
            patch_backup_payload (PatchEC2EBSBackupsModel): Payload for update backup request

        Returns:
            str: Update request task ID which can be used to monitor progress of the operation
        """
        logger.info(f"Deleting backup {backup_id} from ec2: {volume_id}")
        path: str = f"{self.csp_volume_backups}/{backup_id}"
        payload = PatchEC2EBSBackups.from_domain_model(domain_model=patch_backup_payload)
        response: Response = patch(
            self.beta_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.accepted, response.content
        return get_task_id_from_header(response)

    # endregion

    def complete_transient_backup(self, customer_id: str, account_id: str, region: str):
        """
        Run copy2cloud on a specific region of an AWS account

        Args:
            customer_id (str): Unique identifier of a customer on DSCC
            account_id (str): Unique identifier of a cloud account
            region (str): AWS region on which copy2cloud endpoint will be run

        Returns:
            None
        """
        logger.info(
            f"calling copy2cloud endpoint: customer_id: {customer_id}, account_id: {account_id}, region: {region}"
        )
        url = self.dscc["atlantia-url"]
        path = "test/v1/nb-rest.dataprotection/copy2cloud"
        payload = {"customerID": customer_id, "accountID": account_id, "cspRegion": region}
        response: Response = post(url, path, json_data=dumps(payload), headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content

    def import_account_snapshots_and_amis(
        self,
        csp_account_id: str,
        post_import_snapshot: PostImportSnapshotModel,
        expected_status_code: int = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        """
        Import AMI's and snapshots from an AWS account

        Args:
            csp_account_id (str): Unique identifier of a cloud account
            post_import_snapshot (PostImportSnapshotModel): Payload for post import snapshot operation
            expected_status_code (int): Status code to compare with expected status code.
                                        Defaults to requests.codes.accepted.

        Returns:
            str: Returns import request task ID if successful else returns error response
        """
        path: str = f"{self.csp_accounts}/{csp_account_id}/{self.import_csp_backups}"
        payload = PostImportSnapshot.from_domain_model(domain_model=post_import_snapshot)

        logger.info(f"Import Snapshot Payload = {payload}")
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, response.text

        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())
