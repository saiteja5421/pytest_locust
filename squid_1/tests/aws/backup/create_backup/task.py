"""
Test steps
[PSR] Number of simultaneous request to create backups for ec2 instance
[PSR] Number of simultaneous request to get backups for ec2 instance
[PSR] Number of simultaneous requests to delete Backups/HPE cloud backups

"""

import json
from locust import SequentialTaskSet, task
from requests import codes
from common import helpers
from tests.aws.config import Paths


class CreateLocalBackupTasks(SequentialTaskSet):
    """
    Crate backups for an ec2_instance.
    In the on_start create ec2 instance,create protection policy and protect ec2_instance.

    """

    @task
    def create_on_demand_local_backup(self):
        """Create HPE Local backup on demand"""

        url = f"{Paths.PROTECTION_JOBS}/{self.user.protection_job_id}/run"
        payload = {"scheduleIds": [1]}

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:

            print(f"Create on demand local backup-Response code is {response.status_code}")
            if response.status_code == codes.accepted:
                self.verify_backup_task_status(response.json()["taskUri"])
            print(f"Create local backup- Response text::{response.text}")

    def verify_backup_task_status(self, task_uri):
        """
        Verifies backup task status whether it is completed

        Args:
            response (object): Response of the create local backup

        Raises:
            Exception: Timeout error
            Exception: FAILED STATUS error
            Exception: Taskuri failure
        """
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            print("Local Backup completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Local Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"Local Backup failed with status'FAILED' error")
        else:
            raise Exception(
                f"Create local backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
            )

    @task
    def on_completion(self):
        self.interrupt()
