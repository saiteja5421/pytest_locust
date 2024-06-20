import logging
import time
from tenacity import retry, wait_exponential, stop_after_attempt
from locust import SequentialTaskSet, task, tag
from lib.dscc.backup_recovery.aws_protection.gfrs.gfrs_helper import (
    delete_indexed_files_from_csp_backup,
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
v1_beta_1_api, v1_beta_2_api = helpers.get_v1_beta_api_prefix()


class CSPVolumeBackupIndexFileRestoreTasks(SequentialTaskSet):
    """
    Post index guest files for those backups.
    """

    config = helpers.read_config()

    def on_start(self):
        self.csp_volume_id: str = self.user.csp_volume_id
        self.aws_backup_ids: list = self.user.aws_backup_ids
        self.cloud_backup_ids: list = self.user.cloud_backup_ids
        self.headers = self.user.headers
        self.proxies = self.user.proxies
        self.environment = self.user.environment

    @tag("flr_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def post_volume_index_files_for_aws_backup_1(self):
        logger.info(
            f"\n-------------- [AWS Backup 1 - Step 1] POST Index Guest Files on CSP Volume {self.csp_volume_id} for Backup {self.aws_backup_ids[0]} --------------"
        )
        start_time = time.time()
        start_perf_counter = time.perf_counter()
        request_name = "Post-FLR-Index-Native-Backup-EBS"
        try:
            post_index_guest_files_on_csp_machine_instance_and_volume_backup(
                self,
                csp_asset_id=self.csp_volume_id,
                csp_asset_backup_id=self.aws_backup_ids[0],
                csp_path_type=GFRSPaths.CSP_VOLUMES_BACKUPS,
            )
            index_time = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name=request_name,
                exception=None,
                start_time=start_time,
                response_time=index_time,
                response_result={},
            )
        except Exception as e:
            helpers.custom_locust_response(environment=self.user.environment, name=request_name, exception=e)

    @tag("flr_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def post_volume_index_files_for_cloud_backup_1(self):
        logger.info(
            f"\n-------------- [Cloud Backup 1 - Step 1] POST Index Guest Files on CSP Volume {self.csp_volume_id} for Backup {self.cloud_backup_ids[0]} --------------"
        )
        start_time = time.time()
        start_perf_counter = time.perf_counter()
        request_name = "Post-FLR-Index-Cloud-Backup-EBS"
        try:
            post_index_guest_files_on_csp_machine_instance_and_volume_backup(
                self,
                csp_asset_id=self.csp_volume_id,
                csp_asset_backup_id=self.cloud_backup_ids[0],
                csp_path_type=GFRSPaths.CSP_VOLUMES_BACKUPS,
            )
            index_time = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name=request_name,
                exception=None,
                start_time=start_time,
                response_time=index_time,
                response_result={},
            )
        except Exception as e:
            helpers.custom_locust_response(environment=self.user.environment, name=request_name, exception=e)

    @tag("flr_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_volume_index_files_for_aws_backup_1(self):
        logger.info(
            f"\n-------------- [AWS Backup 1 - Step 2] GET Indexed Filesystem for CSP Volume {self.csp_volume_id} & Backup {self.aws_backup_ids[0]} -------------------------"
        )
        start_time = time.time()
        start_perf_counter = time.perf_counter()
        request_name = "Get-Indexed-FileSystem-From-Native-Backup-EBS"
        try:
            self.aws_backup_1_indexed_filesystem = get_indexed_file_system_info_for_backup(
                self,
                csp_asset_id=self.csp_volume_id,
                csp_asset_backup_id=self.aws_backup_ids[0],
                csp_asset_type=GFRSPaths.GET_VOLUME_INDEXED_FILE,
            )
            logger.info(
                f"GET Indexed Filesystem = {self.aws_backup_1_indexed_filesystem} for Volume {self.csp_volume_id} & Backup {self.aws_backup_ids[0]}"
            )
            get_indexed_fs_time = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name=request_name,
                exception=None,
                start_time=start_time,
                response_time=get_indexed_fs_time,
                response_result={},
            )
        except Exception as e:
            helpers.custom_locust_response(environment=self.user.environment, name=request_name, exception=e)

    @tag("flr_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_volume_index_files_for_cloud_backup_1(self):
        logger.info(
            f"\n-------------- [Cloud Backup 1 - Step 2] GET Indexed Filesystem for CSP Volume {self.csp_volume_id} & Backup {self.cloud_backup_ids[0]} -------------------------"
        )
        start_time = time.time()
        start_perf_counter = time.perf_counter()
        request_name = "Get-Indexed-FileSystem-From-Cloud-Backup-EBS"
        try:
            self.cloud_backup_1_indexed_filesystem = get_indexed_file_system_info_for_backup(
                self,
                csp_asset_id=self.csp_volume_id,
                csp_asset_backup_id=self.cloud_backup_ids[0],
                csp_asset_type=GFRSPaths.GET_VOLUME_INDEXED_FILE,
            )
            logger.info(
                f"GET Indexed Filesystem = {self.cloud_backup_1_indexed_filesystem} for Volume {self.csp_volume_id} & Backup {self.cloud_backup_ids[0]}"
            )
            get_indexed_fs_time = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name=request_name,
                exception=None,
                start_time=start_time,
                response_time=get_indexed_fs_time,
                response_result={},
            )
        except Exception as e:
            helpers.custom_locust_response(environment=self.user.environment, name=request_name, exception=e)

    @tag("flr_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def restore_volume_index_files_for_aws_backup_1(self):
        logger.info(
            f"\n-------------- [AWS Backup 1 - Step 3] POST Restore CSP Volume {self.csp_volume_id} with Backup {self.aws_backup_ids[0]} --------------"
        )
        csp_indexed_file_system_info: CSPIndexedFileSystemInfo = None
        csp_indexed_file_system_info = self.aws_backup_1_indexed_filesystem.items[0]
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
        start_time = time.time()
        start_perf_counter = time.perf_counter()
        request_name = "Restore-Files-From-Native-Backup-EBS"
        try:
            restore_csp_instance_or_volume_files_folders(
                self, self.csp_volume_id, self.aws_backup_ids[0], restore_payload, GFRSPaths.CSP_VOLUMES_BACKUPS
            )
            restore_files_time = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name=request_name,
                exception=None,
                start_time=start_time,
                response_time=restore_files_time,
                response_result={},
            )
        except Exception as e:
            helpers.custom_locust_response(environment=self.user.environment, name=request_name, exception=e)

    @tag("flr_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def restore_volume_index_files_for_cloud_backup_1(self):
        logger.info(
            f"\n-------------- [Cloud Backup 1 - Step 3] POST Restore CSP Volume {self.csp_volume_id} with Backup {self.cloud_backup_ids[0]} --------------"
        )
        csp_indexed_file_system_info: CSPIndexedFileSystemInfo = None
        csp_indexed_file_system_info = self.cloud_backup_1_indexed_filesystem.items[0]
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
        start_time = time.time()
        start_perf_counter = time.perf_counter()
        request_name = "Restore-EBS-Files-From-Cloud-Backup"
        try:
            restore_csp_instance_or_volume_files_folders(
                self, self.csp_volume_id, self.cloud_backup_ids[0], restore_payload, GFRSPaths.CSP_VOLUMES_BACKUPS
            )
            restore_files_time = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name=request_name,
                exception=None,
                start_time=start_time,
                response_time=restore_files_time,
                response_result={},
            )
        except Exception as e:
            helpers.custom_locust_response(environment=self.user.environment, name=request_name, exception=e)

    @tag("flr_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def delete_volume_index_files_for_aws_backup_1(self):
        logger.info(
            f"\n-------------- [AWS Backup 1 - Step 4] POST Delete Indexed File on CSP Volume {self.csp_volume_id} for Backup {self.aws_backup_ids[0]} --------------"
        )
        delete_indexed_files_from_csp_backup(
            self, self.csp_volume_id, self.aws_backup_ids[0], GFRSPaths.GET_VOLUME_INDEXED_FILE
        )

    @tag("flr_volume")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=5, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def delete_volume_index_files_for_cloud_backup_1(self):
        logger.info(
            f"\n-------------- [Cloud Backup 1 - Step 4] POST Delete Indexed File on CSP Volume {self.csp_volume_id} for Backup {self.cloud_backup_ids[0]} --------------"
        )
        delete_indexed_files_from_csp_backup(
            self, self.csp_volume_id, self.cloud_backup_ids[0], GFRSPaths.GET_VOLUME_INDEXED_FILE
        )

    @tag("flr_volume")
    @task
    def done(self):
        logger.info("All expected tasks done, raising StopUser interrupt")
        raise StopUser()
