import logging
import time
from tenacity import retry, wait_exponential, stop_after_attempt
from locust import SequentialTaskSet, task, tag
from lib.dscc.backup_recovery.aws_protection.gfrs.gfrs_helper import (
    post_index_guest_files_on_csp_machine_instance_and_volume_backup,
    get_indexed_file_system_info_for_backup,
    restore_csp_instance_or_volume_files_folders,
)
from common import helpers
from tests.aws.config import GFRSPaths
from lib.dscc.backup_recovery.aws_protection.gfrs.models.csp_indexed_file_system_info import (
    CSPIndexedFileSystemInfo,
)

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins
from locust.exception import StopUser


logger = logging.getLogger(__name__)


class RestoreFromNativeAndCloudBackupForCSPVolumeTasks(SequentialTaskSet):
    """
    Post index guest files for those backups and parallel restores from different native/cloud backups for same ebs volume (expecting multiple restore calls to Fail)
    """

    config = helpers.read_config()

    def on_start(self):
        self.csp_volume_id: str = self.user.csp_volume_id
        self.aws_backup_id: str = self.user.aws_backup_id
        self.cloud_backup_id: str = self.user.cloud_backup_id
        self.headers = self.user.headers
        self.proxies = self.user.proxies
        self.environment = self.user.environment

        logger.info(
            f"\n-------------- [AWS Backup - Step 1] POST Index Guest Files on CSP Volume {self.csp_volume_id} for Backup {self.aws_backup_id} --------------"
        )
        post_index_guest_files_on_csp_machine_instance_and_volume_backup(
            self,
            csp_asset_id=self.csp_volume_id,
            csp_asset_backup_id=self.aws_backup_id,
            csp_path_type=GFRSPaths.CSP_VOLUMES_BACKUPS,
        )
        time.sleep(30)
        logger.info(
            f"\n-------------- [AWS Backup - Step 2] GET Indexed Filesystem for CSP Volume {self.csp_volume_id} & Backup {self.aws_backup_id} -------------------------"
        )
        indexed_filesystem = get_indexed_file_system_info_for_backup(
            self,
            csp_asset_id=self.csp_volume_id,
            csp_asset_backup_id=self.aws_backup_id,
            csp_asset_type=GFRSPaths.GET_VOLUME_INDEXED_FILE,
        )
        logger.info(
            f"GET Indexed Filesystem = {indexed_filesystem} for Volume {self.csp_volume_id} & Backup {self.aws_backup_id}"
        )
        csp_indexed_file_system_info: CSPIndexedFileSystemInfo = None
        csp_indexed_file_system_info = indexed_filesystem.items[0]
        logger.info(
            f"mount_path = /etc/passwd, file_system_id = {csp_indexed_file_system_info.id}---------------------------"
        )
        # NOTE: "absoluteSourcePath": f"{csp_indexed_file_system_info.mount_path}" will only work if writing data, using /etc/passwd (common file)
        self.aws_restore_payload = {
            "restoreInfo": [
                {
                    "absoluteSourcePath": "/etc/passwd",
                    "filesystemId": f"{csp_indexed_file_system_info.id}",
                }
            ]
        }
        logger.info(f"Restore Payload = {self.aws_restore_payload}")

        logger.info(
            f"\n-------------- [AWS Backup - Step 3] POST Restore CSP Volume {self.csp_volume_id} with Backup {self.aws_backup_id} and payload {self.aws_restore_payload} --------------"
        )
        restore_csp_instance_or_volume_files_folders(
            self, self.csp_volume_id, self.aws_backup_id, self.aws_restore_payload, GFRSPaths.CSP_VOLUMES_BACKUPS
        )
        logger.info(
            f"\n-------------- [Cloud Backup - Step 1] POST Index Guest Files on CSP Volume {self.csp_volume_id} for Backup {self.cloud_backup_id} --------------"
        )
        post_index_guest_files_on_csp_machine_instance_and_volume_backup(
            self,
            csp_asset_id=self.csp_volume_id,
            csp_asset_backup_id=self.cloud_backup_id,
            csp_path_type=GFRSPaths.CSP_VOLUMES_BACKUPS,
        )
        time.sleep(30)
        logger.info(
            f"\n-------------- [Cloud Backup - Step 2] GET Indexed Filesystem for CSP Volume {self.csp_volume_id} & Backup {self.cloud_backup_id} -------------------------"
        )
        indexed_filesystem = get_indexed_file_system_info_for_backup(
            self,
            csp_asset_id=self.csp_volume_id,
            csp_asset_backup_id=self.cloud_backup_id,
            csp_asset_type=GFRSPaths.GET_VOLUME_INDEXED_FILE,
        )
        logger.info(
            f"GET Indexed Filesystem = {indexed_filesystem} for Volume {self.csp_volume_id} & Backup {self.cloud_backup_id}"
        )
        csp_indexed_file_system_info: CSPIndexedFileSystemInfo = None
        csp_indexed_file_system_info = indexed_filesystem.items[0]
        logger.info(
            f"mount_path = /etc/passwd, file_system_id = {csp_indexed_file_system_info.id}---------------------------"
        )
        # NOTE: "absoluteSourcePath": f"{csp_indexed_file_system_info.mount_path}" will only work if writing data, using /etc/passwd (common file)
        self.cloud_restore_payload = {
            "restoreInfo": [
                {
                    "absoluteSourcePath": "/etc/passwd",
                    "filesystemId": f"{csp_indexed_file_system_info.id}",
                }
            ]
        }
        logger.info(f"Restore Payload = {self.cloud_restore_payload}")

        logger.info(
            f"\n-------------- [Cloud Backup - Step 3] POST Restore CSP Volume {self.csp_volume_id} with Backup {self.cloud_backup_id} and payload {self.cloud_restore_payload} --------------"
        )
        restore_csp_instance_or_volume_files_folders(
            self, self.csp_volume_id, self.cloud_backup_id, self.cloud_restore_payload, GFRSPaths.CSP_VOLUMES_BACKUPS
        )

        # NOTE: Not Deleting the Indexed Files, so expecting Errors when calling POST Index Files

    @tag("flr_negative_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def post_volume_index_files_for_aws_backup_1(self):
        logger.info(
            f"\n-------------- [AWS Backup - Step 1] POST Index Guest Files on CSP Volume {self.csp_volume_id} for Backup {self.aws_backup_id} --------------"
        )
        post_index_guest_files_on_csp_machine_instance_and_volume_backup(
            self,
            csp_asset_id=self.csp_volume_id,
            csp_asset_backup_id=self.aws_backup_id,
            csp_path_type=GFRSPaths.CSP_VOLUMES_BACKUPS,
            expecting_error=True,
        )
        time.sleep(20)

    @tag("flr_negative_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def post_volume_index_files_for_cloud_backup_1(self):
        logger.info(
            f"\n-------------- [Cloud Backup - Step 1] POST Index Guest Files on CSP Volume {self.csp_volume_id} for Backup {self.cloud_backup_id} --------------"
        )
        post_index_guest_files_on_csp_machine_instance_and_volume_backup(
            self,
            csp_asset_id=self.csp_volume_id,
            csp_asset_backup_id=self.cloud_backup_id,
            csp_path_type=GFRSPaths.CSP_VOLUMES_BACKUPS,
            expecting_error=True,
        )
        time.sleep(20)

    @tag("flr_negative_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_volume_index_files_for_aws_backup_1(self):
        logger.info(
            f"\n-------------- [AWS Backup - Step 2] GET Indexed Filesystem for CSP Volume {self.csp_volume_id} & Backup {self.aws_backup_id} -------------------------"
        )
        self.aws_backup_indexed_filesystem = get_indexed_file_system_info_for_backup(
            self,
            csp_asset_id=self.csp_volume_id,
            csp_asset_backup_id=self.aws_backup_id,
            csp_asset_type=GFRSPaths.GET_VOLUME_INDEXED_FILE,
        )
        logger.info(
            f"GET Indexed Filesystem = {self.aws_backup_indexed_filesystem} for Volume {self.csp_volume_id} & Backup {self.aws_backup_id}"
        )

    @tag("flr_negative_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_volume_index_files_for_cloud_backup_1(self):
        logger.info(
            f"\n-------------- [Cloud Backup - Step 2] GET Indexed Filesystem for CSP Volume {self.csp_volume_id} & Backup {self.cloud_backup_id} -------------------------"
        )
        self.cloud_backup_indexed_filesystem = get_indexed_file_system_info_for_backup(
            self,
            csp_asset_id=self.csp_volume_id,
            csp_asset_backup_id=self.cloud_backup_id,
            csp_asset_type=GFRSPaths.GET_VOLUME_INDEXED_FILE,
        )
        logger.info(
            f"GET Indexed Filesystem = {self.cloud_backup_indexed_filesystem} for Volume {self.csp_volume_id} & Backup {self.cloud_backup_id}"
        )

    @tag("flr_negative_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def restore_volume_index_files_for_aws_backup_1(self):
        logger.info(
            f"\n-------------- [AWS Backup - Step 3] POST Restore CSP Volume {self.csp_volume_id} with Backup {self.aws_backup_id} --------------"
        )
        csp_indexed_file_system_info: CSPIndexedFileSystemInfo = None
        csp_indexed_file_system_info = self.aws_backup_indexed_filesystem.items[0]
        logger.info(
            f"mount_path = /etc/passwd, file_system_id = {csp_indexed_file_system_info.id}---------------------------"
        )

        # NOTE: "absoluteSourcePath": f"{csp_indexed_file_system_info.mount_path}" will only work if writing data, using /etc/passwd (common file)
        restore_payload = {
            "restoreInfo": [
                {
                    "absoluteSourcePath": "/etc/passwd",
                    "filesystemId": f"{csp_indexed_file_system_info.id}",
                }
            ]
        }
        logger.info(f"Restore Payload = {restore_payload}")

        restore_csp_instance_or_volume_files_folders(
            self, self.csp_volume_id, self.aws_backup_id, restore_payload, GFRSPaths.CSP_VOLUMES_BACKUPS, True
        )

    @tag("flr_negative_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def restore_volume_index_files_for_cloud_backup_1(self):
        logger.info(
            f"\n-------------- [Cloud Backup - Step 3] POST Restore CSP Volume {self.csp_volume_id} with Backup {self.cloud_backup_id} --------------"
        )
        csp_indexed_file_system_info: CSPIndexedFileSystemInfo = None
        csp_indexed_file_system_info = self.cloud_backup_indexed_filesystem.items[0]
        logger.info(
            f"mount_path = /etc/passwd, file_system_id = {csp_indexed_file_system_info.id}---------------------------"
        )

        # NOTE: "absoluteSourcePath": f"{csp_indexed_file_system_info.mount_path}" will only work if writing data, using /etc/passwd (common file)
        restore_payload = {
            "restoreInfo": [
                {
                    "absoluteSourcePath": "/etc/passwd",
                    "filesystemId": f"{csp_indexed_file_system_info.id}",
                }
            ]
        }
        logger.info(f"Restore Payload = {restore_payload}")

        restore_csp_instance_or_volume_files_folders(
            self, self.csp_volume_id, self.cloud_backup_id, restore_payload, GFRSPaths.CSP_VOLUMES_BACKUPS, True
        )

    @tag("flr_negative_volume")
    @task
    def done(self):
        logger.info("All expected tasks done, raising StopUser interrupt")
        raise StopUser()
