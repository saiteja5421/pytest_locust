"""
Test steps
[PSR] Number of simultaneous request to create backups for ec2 instance
[PSR] Number of simultaneous request to get backups for ec2 instance
[PSR] Number of simultaneous requests to delete Backups/HPE cloud backups

"""

from asyncio.log import logger
import json
import time
from locust import SequentialTaskSet, task
from requests import codes
from common import helpers
from tests.aws.config import Paths
from lib.dscc.backup_recovery.aws_protection.cloud_backups import (
    start_cvsa,
    wait_for_staging_backup_task,
    wait_for_cloudbackup_completion,
)
from lib.dscc.backup_recovery.tasks.task_helper import SubTaskDisplayName, wait_for_subtask_to_complete


class CreateMultipleCloudBackups(SequentialTaskSet):
    """
    Create cloud backups for an ec2_instance.
    In the on_start create ec2 instance,create protection policy and protect ec2_instance.

    """

    proxies = helpers.set_proxy()

    @task
    def create_staging_backups(self):
        """Create staging backup"""
        task_uris = []
        triggered_task_ids = []
        timer_dict = {}
        for ec2_instance_id in self.user.instance_to_protection_job.keys():
            protection_job_id = self.user.instance_to_protection_job[ec2_instance_id]["protection_job_id"]
            url = f"{Paths.PROTECTION_JOBS}/{protection_job_id}/run"
            payload = {"scheduleIds": [1]}
            test_start_time = time.time()
            start_perf_counter = time.perf_counter()
            timer_dict[ec2_instance_id] = {}
            timer_dict[ec2_instance_id]["staging_backup_start_time"] = test_start_time
            timer_dict[ec2_instance_id]["start_perf_counter_staging"] = start_perf_counter
            with self.client.post(
                url,
                data=json.dumps(payload),
                headers=self.user.headers.authentication_header,
                proxies=self.proxies,
                catch_response=True,
            ) as response:
                if response.status_code == codes.accepted:
                    task_uris.append(response.json()["taskUri"])
        for task_uri in task_uris:
            self.verify_staging_backup_initiate_task_status(task_uri)

        for ec2_instance_id in self.user.instance_to_protection_job.keys():
            csp_machine_id = self.user.instance_to_protection_job[ec2_instance_id]["asset_id"]
            triggered_task = wait_for_staging_backup_task(csp_machine_id)
            triggered_task_ids.append(triggered_task)
            self.user.instance_to_protection_job[ec2_instance_id]["triggered_task_id"] = triggered_task
            start_perf_counter = timer_dict[ec2_instance_id]["start_perf_counter_staging"]
            test_start_time = timer_dict[ec2_instance_id]["staging_backup_start_time"]
            time_taken = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Staging_Backup_Time",
                exception=None,
                start_time=test_start_time,
                response_time=time_taken,
            )
        print("Staging backup Task execution finished for all instances")
        logger.info("Staging backup Task execution finished for all instances")
        self.user.task_uris = task_uris
        self.user.triggerred_task_ids = triggered_task_ids

    def verify_staging_backup_initiate_task_status(self, task_uri):
        """
        Verifies staging backup task status whether it is completed

        Args:
            response (object): Response of the create local backup

        Raises:
            Exception: Timeout error
            Exception: FAILED STATUS error
            Exception: Taskuri failure
        """
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            print("Staging Backup initialization task completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Staging Backup initialization task failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"Staging Backup initialization task failed with status'FAILED' error")
        else:
            raise Exception(
                f"Create staging backup initiation task failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
            )

    def wait_for_cloud_backup_of_multiple_instances(self):
        """This function will wait till backup of all ec2 instances are complete"""
        subtask_name = SubTaskDisplayName.INSTANCE_CLOUD_BACKUP_WORKFLOW.value
        for ec2_instance_id in self.user.instance_to_protection_job.keys():
            test_start_time = time.time()
            start_perf_counter = time.perf_counter()
            trigger_task_id = self.user.instance_to_protection_job[ec2_instance_id]["triggered_task_id"]
            wait_for_subtask_to_complete(subtask_name=subtask_name, task_id=trigger_task_id, timeout=15 * 60)
            time_taken = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Cloud_Backup_Time",
                exception=None,
                start_time=test_start_time,
                response_time=time_taken,
            )

    @task()
    def create_cloud_backups(self):
        """_summary_"""
        print("Calling copy2cloud API")
        csp_account = self.user.csp_account
        # This function will call API which will deploy CVSA and power it ON.
        start_cvsa(
            account_id=csp_account["id"],
            customer_id=csp_account["customerId"],
            region=self.user.region,
        )
        self.wait_for_cloud_backup_of_multiple_instances()
        print("InstanceCloudBackup Workflow done for all instances")
        logger.info("InstanceCloudBackup Workflow done for all instances")
        # This function will wait for CVSA to be powered OFF and respective task to complete
        wait_for_cloudbackup_completion(
            account_id=csp_account["id"],
            customer_id=csp_account["customerId"],
            region=self.user.region,
            account_name=self.user.account_name,
        )
        print("CVSA Task execution finished")
        logger.info("CVSA Task execution finished")
        print(f"In on_completion.. calling stop user")
        logger.info("In on_completion.. calling stop user")
        self.user.environment.runner.stop()
