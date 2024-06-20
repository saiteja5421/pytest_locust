import logging

from lib.common.common import get, get_task_id_from_header, post, patch, delete
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_eks_k8s_app_backup_model import (
    CSPK8sAppBackupInfoModel,
    CSPK8sAppBackupListModel,
)
from lib.common.users.user import User
from lib.dscc.backup_recovery.aws_protection.backup_restore.models.csp_eks_k8s_app_backup_v1beta1_filepoc import (
    CSPK8sAppBackupInfo,
    CSPK8sAppBackupList,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.post_restore_csp_k8s_app import (
    PostRestoreK8sApp,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.patch_csp_eks_k8s_backup import (
    PatchCSPK8sAppBackup,
)
from lib.common.config.config_manager import ConfigManager
from requests import codes, Response

logger = logging.getLogger()


class EKSDataProtectionManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.api_group = config["API-GROUP"]
        self.url = f"{self.dscc['atlantia-url']}/{self.api_group['backup-recovery']}/{self.dscc['beta-version']}"
        self.csp_k8s_applications = self.atlantia_api["csp-k8s-applications"]

    def get_csp_k8s_app_backups(
        self,
        csp_k8s_application_id: str,
        offset: int = 0,
        limit: int = 100,
        sort: str = "name",
        filter: str = "",
    ) -> CSPK8sAppBackupListModel:
        """Get information about CSP K8s Application backups.
            End Point: csp-k8s-applications/{k8sApplicationId}/backups

        Args:
            csp_k8s_application_id (str): unique identifier of a Namespaced application
            offset (int, optional): The number of items to omit from the beginning of the result set.  Defaults to 0.
            limit (int, optional): The maximum number of items to include in the response. Defaults to 100.
            sort (str, optional): A comma separated list of properties to sort by, followed by a direction indicator ("asc" or "desc"). Defaults to "name" These fields can be used for sorting: createdAt, expiresAt, state and status.
            filter (str, optional): An expression by which to filter the results. Defaults to "" These fields can be used for filtering: backupType, state, status and consistency.

        Returns:
            CSPK8sAppBackupListModel: List of csp K8s Namespaced application backups
        """
        if filter != "":
            path: str = (
                f"{self.csp_k8s_applications}/{csp_k8s_application_id}"
                + f"/backups?offset={offset}&limit={limit}&sort={sort}&filter={filter}&"
            )
        else:
            path: str = f"{self.csp_k8s_applications}/{csp_k8s_application_id}/backups"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        csp_k8s_app_backup_list = CSPK8sAppBackupList.from_json(response.text)
        return csp_k8s_app_backup_list.to_domain_model()

    def delete_csp_k8s_app_backup(
        self,
        csp_k8s_application_id: str,
        backup_id: str,
    ) -> str:
        """Delete a CSP K8s Application backup.
            End point: csp-k8s-applications/{k8sApplicationId}/backups/{id}

        Args:
            csp_k8s_application_id (str): unique identifier of a Namespaced application
            backup_id (str): unique identifier of a Namespaced application backup.

        Returns:
            str: The async-operation task id that can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_k8s_applications}/{csp_k8s_application_id}/backups/{backup_id}"
        response: Response = delete(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.accepted, response.content
        # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
        # remove string strip after fix
        return get_task_id_from_header(response)

    def get_csp_k8s_app_backup_details(
        self,
        csp_k8s_application_id: str,
        backup_id: str,
    ) -> CSPK8sAppBackupInfoModel:
        """Get details of a CSP K8s Application backup.
            End point: csp-k8s-applications/{k8sApplicationId}/backups/{id}

        Args:
            csp_k8s_application_id (str): unique identifier of a Namespaced application
            backup_id (str): unique identifier of a Namespaced application backup

        Returns:
            CSPK8sAppBackupInfoModel: Returns details of a specified cloud service provider (CSP) K8s Application backup
        """
        path: str = f"{self.csp_k8s_applications}/{csp_k8s_application_id}/backups/{backup_id}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        csp_app_backup_info = CSPK8sAppBackupInfo.from_json(response.text)
        return csp_app_backup_info.to_domain_model()

    def update_csp_k8s_app_backup(
        self,
        csp_k8s_application_id: str,
        backup_id: str,
        patch_backup_payload: PatchCSPK8sAppBackup,
    ) -> str:
        """Modify the properties of a CSP K8s Application backup
            csp-k8s-applications/{k8sApplicationId}/backups/{id}

        Args:
            csp_k8s_application_id (str): unique identifier of a Namespaced application
            backup_id (str): unique identifier of a Namespaced application backup
            patch_backup_payload (PatchCSPK8sAppBackup): payload for update operation

        Returns:
            str: Update request task ID which can be used to monitor progress of the operation
        """
        path: str = f"{self.csp_k8s_applications}/{csp_k8s_application_id}/backups/{backup_id}"
        payload = patch_backup_payload.to_json()
        response: Response = patch(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.accepted, response.content
        # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
        # remove string strip after fix
        return get_task_id_from_header(response)[:-1]

    def restore_csp_k8s_application(
        self,
        csp_k8s_application_id: str,
        restore_payload: PostRestoreK8sApp,
        return_restore: bool = True,
        negative: bool = False,
        expected_neg_test_response_code=codes.internal_server_error,
    ) -> str:
        """Restore a CSP K8s Application from a backup
            csp-k8s-applications/{k8sApplicationId}/restore

        Args:
            csp_k8s_application_id (str): unique identifier of a Namespaced application
            restore_payload (PostRestoreK8sApp): payload for restore post operation
            return_restore (bool) : if True return task id, if false return response
            negative (bool) : if True return restore request response, if false continue response validation.
        Returns:
            CSPK8sAppBackupInfo: Returns details of a specified cloud service provider (CSP) K8s Application backup
        """
        path: str = f"{self.csp_k8s_applications}/{csp_k8s_application_id}/restore"
        payload = restore_payload.to_json()
        response: Response = post(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        if negative:
            # Check restore response
            assert response.status_code == expected_neg_test_response_code, response.content
            return response
        assert response.status_code == codes.accepted, response.content
        if return_restore:
            # TODO: BUG https://nimblejira.nimblestorage.com/browse/DCS-16929
            # remove string strip after fix
            return get_task_id_from_header(response)
        else:
            return response
