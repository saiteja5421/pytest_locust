import logging
import time
from locust import SequentialTaskSet, task, tag
from common import helpers
from lib.dscc.backup_recovery.aws_protection.cloud_backups import start_cvsa, wait_for_cloudbackup_completion
from lib.dscc.backup_recovery.protection import protection_job
from lib.dscc.backup_recovery.tasks import task_helper

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins
from locust.exception import StopUser

logger = logging.getLogger(__name__)


class CreateHPECloudBackupCopy2CloudTask(SequentialTaskSet):
    """
    Create  cloud backups for an ec2_instance and then restore the cloud backup.
    In the on_start create ec2 instance,create protection policy and protect ec2_instance.

    """

    config = helpers.read_config()

    @tag("local_backup")
    @task
    def create_hpe_cloud_backup_copy2cloud(self):
        """Create HPE cloud backup on demand."""
        logger.info("\nStarting tasks . . .")
        logger.info("\n----Step 8-  Create HPE Cloud Backups  -------")
        response = protection_job.run_protection_job(protection_job_id=self.user.protection_job_id, scheduleIds=[1])
        logger.info(f"Run Protection Job Response: {response}")
        task_uri = response.headers["location"]
        logger.info(f"Run Protection Job taskUri: {task_uri}")

        logger.info("Wait for Cloud Backup task to reach 50 percentages completed . . .")
        # NOTE: Task percentage API seems to be off (reaching 50% when only at 21%)
        time.sleep(480)
        trigger_task_id = task_uri.rsplit("/", 1)[1]
        logger.info(f"Wait for Cloud Backup Task ID: {trigger_task_id}")
        task_helper.wait_for_task_percent_complete(task_id=trigger_task_id)

        logger.info("\n----Step 9-  Run Copy 2 Cloud & Validate  -------")
        response = start_cvsa(
            customer_id=self.user.customer_id,
            account_id=self.user.csp_account_id,
            region=self.user.aws.region_name,
        )

        # NOTE: Task percentage API seems to be off (reaching 100% when only at 21%)
        time.sleep(300)
        wait_for_cloudbackup_completion(
            account_id=self.user.csp_account_id,
            customer_id=self.user.customer_id,
            region=self.user.aws.region_name,
            account_name=self.user.csp_account_name,
        )

        logger.info(f"Validate Cloud Backup Task Status: {task_uri}")
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            logger.info("Backup was successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception("Backup failed with status'FAILED' error")
        else:
            raise Exception(f"Cloud Backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")
        """
        NOTE: Discussed with Ruben who wrote this TC: No longer performing Restore Operation as other Test Cases have that handled as we only need to test for max configurations w/Backup
        """

    @tag("local_backup")
    @task
    def on_completion(self):
        logger.info("All expected tasks done, raising StopUser interrupt")
        raise StopUser()
