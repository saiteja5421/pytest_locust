"""
Test steps
[PSR] Number of simultaneous request to create backups for ec2 instance
[PSR] Number of simultaneous requests to delete Backups/HPE cloud backups

"""

import json
from locust import SequentialTaskSet, task
from requests import codes
from common import helpers
from tests.aws.config import Paths
import tests.aws.config as config
import logging


class LocalBackupTasks(SequentialTaskSet):
    """
    task1:
    Crate backups for an ec2_instance.
    In the on_start create ec2 instance,create protection policy and protect ec2_instance.

    task2:
    Delete all the backups of an ec2_instance.
    In the on_start ,one of the backup will be picked.
    That backup will be deleted.
    Till all the backups are deleted it will continue

    """

    backup_to_be_deleted = None

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
            logging.info(f"Create on demand local backup-Response code is {response.status_code}")
            logging.info(f"Create local backup- Response text::{response.text}")
            if response.status_code == codes.accepted:
                self.backup_to_be_deleted = ((response.json()["taskUri"]).split("/"))[4]
                self.verify_backup_task_status(response)
            else:
                response.failure(f"Failed to to create Backup, StatusCode: {str(response.status_code)}")
            logging.info(f"Create local backup- Response text::{response.text}")

    @task
    def delete_hpe_backup(self):
        """Delete the hpe backup"""

        with self.client.delete(
            f"{config.Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.backup_to_be_deleted}",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            logging.info(f"Delete hpe backup-Response code is {response.status_code}")
            if response.status_code == codes.accepted:
                self.verify_backup_task_status(response)
            else:
                response.failure(f"Failed to to delete Backup, StatusCode: {str(response.status_code)}")
            logging.info(f"Delete backup- Response text::{response.text}")

    def verify_backup_task_status(self, response):
        """
        Verifies backup task status whether it is completed

        Args:
            response (object): Response of the create local backup

        Raises:
            Exception: Timeout error
            Exception: FAILED STATUS error
            Exception: Taskuri failure
        """
        task_uri = response.json()["taskUri"]
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            logging.info("Local Backup completed successfully")
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
