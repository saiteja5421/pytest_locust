import json
from locust import SequentialTaskSet, task
from tests.aws.config import Paths
from requests import codes
from common import helpers
import logging


class CreateBackupTask(SequentialTaskSet):
    """
    Crate  and delete cloud backups for an ec2_instance.
    In the on_start create ec2 instance,create protection policy and protect ec2_instance.

    """

    # schedule_recurrence = "Weekly"
    # protection_type = "Snapshot"

    @task
    def create_hpe_cloud_backup(self):
        """Create HPE cloud backup on demand."""

        url = f"{Paths.PROTECTION_JOBS}/{self.user.protection_job_id}/run"
        payload = {"scheduleIds": [1]}

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            logging.info(f"Create on demand cloud backup-Response code is {response.status_code}")
            if response.status_code == codes.accepted:
                self.backup_to_be_deleted = ((response.json()["taskUri"]).split("/"))[4]
                # self.verify_backup_task_status(response)
            else:
                response.failure(f"Failed to to create Backup, StatusCode: {str(response.status_code)}")
            logging.info(f"Create cloud backup- Response text::{response.text}")

    @task
    def delete_hpe_backup(self):
        """Delete the hpe backup"""

        with self.client.delete(
            f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.backup_to_be_deleted}",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            logging.info(f"Delete cloud backup-Response code is {response.status_code}")
            if response.status_code == codes.accepted:
                response.failure(f"Failed to to delete Backup, StatusCode: {str(response.status_code)}")
                # self.verify_backup_task_status(response)
            else:
                response.failure(f"Failed to to delete Backup, StatusCode: {str(response.status_code)}")
            logging.info(f"Delete cloud backup response:: {response.text}")

    def verify_backup_task_status(self, response):
        """
        Verifies backup task status whether it is completed

        Args:
            response (object): Response of the  cloud backup

        Raises:
            Exception: Timeout error
            Exception: FAILED STATUS error
            Exception: Taskuri failure
        """
        task_uri = response.json()["taskUri"]
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            logging.info("Cloud Backup completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Cloud Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"Cloud Backup failed with status'FAILED' error")
        else:
            raise Exception(f"Cloud backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")

    @task
    def on_completion(self):
        self.interrupt()
