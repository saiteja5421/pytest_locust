import json
import logging
from locust import SequentialTaskSet, task
from tests.aws.config import Paths
from requests import codes
from common import helpers

logger = logging.getLogger(__name__)


class CreateBackupTask(SequentialTaskSet):
    """
    Crate  cloud backups for an ec2_instance.
    In the on_start create ec2 instance,create protection policy and protect ec2_instance.

    """

    # schedule_recurrence = "Weekly"
    # protection_type = "Snapshot"

    @task
    def create_hpe_cloud_backup(self):
        """Create HPE cloud backup on demand."""

        url = f"{Paths.PROTECTION_JOBS}/{self.user.protection_job_id}/run"
        payload = {"scheduleIds": [2]}

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            logger.info(f"Create on demand cloud backup-Response code is {response.status_code}")
            if response.status_code == codes.accepted:
                self.verify_backup_task_status(response)
            else:
                response.failure(f"failed to take transient backup")
            logger.info(f"Create cloud backup- Response text::{response.text}")

    def verify_backup_task_status(self, response):
        """
        Verifies backup task status whether it is completed

        Args:
            response (object): Response of the create cloud backup

        Raises:
            Exception: Timeout error
            Exception: FAILED STATUS error
            Exception: Taskuri failure
        """
        task_uri = response.json()["taskUri"]
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            logger.info("Cloud Backup completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Cloud Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"Cloud Backup failed with status'FAILED' error")
        else:
            raise Exception(
                f"Create cloud backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
            )

    @task
    def on_completion(self):
        self.interrupt()
