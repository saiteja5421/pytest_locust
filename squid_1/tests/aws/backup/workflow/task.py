"""
Test steps
[PSR] Number of simultaneous request to create backups for ec2 instance
[PSR] Number of simultaneous requests to delete Backups/HPE cloud backups

"""

import requests
import json
import time
import traceback
from locust import SequentialTaskSet, tag, task
from requests import codes
from common import helpers
from tests.aws.config import Paths
import tests.aws.config as config
from lib.dscc.backup_recovery.aws_protection import backups
import logging

from tenacity import retry, wait_exponential, stop_after_attempt
from common import common

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins
from locust.exception import StopUser

logger = logging.getLogger(__name__)


class BackupTasks(SequentialTaskSet):
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

    def on_start(self):
        pass

    @tag("local_backup")
    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def create_on_demand_local_backup(self):
        """Create HPE Local backup on demand"""

        url = f"{Paths.PROTECTION_JOBS}/{self.user.protection_job_id_local}/run"
        payload = {"scheduleIds": [1]}

        meta_name = "Local backup"
        start_time = time.time()
        start_perf_counter = time.perf_counter()

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name=f"Create AWS Local Backup -> {Paths.PROTECTION_JOBS}/<protection_job_id>/run",
        ) as response:
            logger.info(f"Create on demand local backup-Response code is {response.status_code}")
            logger.info(f"Create local backup- Response text::{response.text}")
            if response.status_code == codes.accepted:
                try:
                    task_uri = response.headers["location"]
                    self.verify_backup_task_status(task_uri)
                    # Wait for Creating state backup to be created
                    time.sleep(30)
                    # Though Parent task is successful backup will be created only after backup state is ok.
                    backup = backups.wait_for_backup_creation(
                        csp_machine_id=self.user.local_csp_machine_id, timeout_minutes=10, sleep_seconds=10
                    )
                    logger.info(
                        f"Local Native Backup is created successfully for EC2 {self.user.local_ec2_instance_id}. Backup is stored in AMI image"
                    )
                    self.backup_to_be_deleted = backup["id"]  # This will be used by delete backup task

                    backup_creation_time = (time.perf_counter() - start_perf_counter) * 1000
                    helpers.custom_locust_response(
                        environment=self.user.environment,
                        name=meta_name,
                        exception=None,
                        start_time=start_time,
                        response_time=backup_creation_time,
                        response_result=backup,
                    )
                except requests.exceptions.ProxyError:
                    raise e

                except Exception as e:
                    logger.error(traceback.format_exc())
                    helpers.custom_locust_response(environment=self.user.environment, name=meta_name, exception=e)
            else:
                response.failure(
                    f"Failed to to create local Backup, StatusCode: {str(response.status_code)} ,Response text: {response.text}. Partial url {Paths.PROTECTION_JOBS}/{self.user.protection_job_id_local}/run"
                )

            logger.info(f"Create local backup- Response text::{response.text}")
            logger.info(f"Test => [create_on_demand_local_backup] -> PASS")

    @tag("local_backup")
    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def delete_hpe_backup(self):
        """Delete the hpe backup"""

        with self.client.delete(
            f"{config.Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.backup_to_be_deleted}",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name=f"Delete AWS Local backup -> {config.Paths.CSP_MACHINE_INSTANCE_BACKUPS}/<backup_id>",
        ) as response:
            logger.info(f"Delete hpe backup-Response code is {response.status_code}")
            if response.status_code == codes.accepted:
                self.verify_backup_task_status(response.headers["location"])
            else:
                response.failure(
                    f"Failed to to delete Backup, StatusCode: {str(response.status_code)},Response text: {response.text} . Partial url {self.user.local_csp_machine_id}/backups/{self.backup_to_be_deleted}"
                )
            logger.info(f"Delete backup- Response text::{response.text}")
            logger.info(f"Task [delete_hpe_backup] -> PASS")

    @tag("transient")
    @task  # It creates just a transient backup so it is not executed for now
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def create_hpe_tranient_backup(self):
        """Create HPE transient backup on demand."""

        url = f"{Paths.PROTECTION_JOBS}/{self.user.protection_job_id_local}/run"
        payload = {"scheduleIds": [2]}

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            logger.info(f"Create on demand transient cloud backup-Response code is {response.status_code}")

            meta_name = "Transient cloud backup"
            request_meta = {
                "request_type": "custom",
                "name": meta_name,
                "start_time": time.time(),
                "response_length": 0,
                "exception": None,
                "context": None,
                "response": None,
            }

            try:
                if response.status_code == codes.accepted:
                    try:
                        start_perf_counter = time.perf_counter()
                        task_uri = response.headers["location"]
                        self.verify_backup_task_status(task_uri)
                        # Wait for Creating state backup to be created
                        time.sleep(30)
                        # Though Parent task is successful backup will be created only after backup state is ok.
                        backup = backups.wait_for_backup_creation(
                            self.user.local_csp_machine_id, timeout_minutes=10, sleep_seconds=10
                        )
                        logger.info("Cloud backup is completed successfully. Transient backup is created in AMI")
                        # if request_meta["exception"] == None:
                        self.backup_to_be_deleted = backup["id"]

                        backup_creation_time = (time.perf_counter() - start_perf_counter) * 1000
                        request_meta["response"] = backup
                        request_meta["response_time"] = backup_creation_time
                        self.user.environment.events.request.fire(**request_meta)
                        logger.info(f"Test => [create_hpe_cloud_backup] => PASS")
                    except requests.exceptions.ProxyError:
                        raise e
                    except Exception as e:
                        request_meta["exception"] = e
                        self.user.environment.events.request.fire(**request_meta)
                        logger.info(f"Test => [create_hpe_cloud_backup] => FAIL")

                else:
                    response.failure(
                        f"Failed to to create cloud Backup, StatusCode: {str(response.status_code)},Response text: {response.text}"
                    )
                    logger.info(f"Test => [create_hpe_cloud_backup] => FAIL")

                logger.info(f"Create cloud backup- Response text::{response.text}")
            except Exception as e:
                response.failure(f"Exception occurred during creation of Transient backup:{e}")

    @tag("transient_donotrun")  # Trasient backups can't be deleted so for now it won't be executed
    @task
    def delete_hpe_tranient_backup(self):
        """Delete the hpe backup"""

        with self.client.delete(
            f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.backup_to_be_deleted}",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            try:
                logger.info(f"Delete cloud backup-Response code is {response.status_code}")
                if response.status_code == codes.accepted:
                    self.verify_backup_task_status(response.headers["location"])
                else:
                    response.failure(
                        f"Failed to delete Backup, StatusCode: {str(response.status_code)}, Response text: {response.text}"
                    )
                logger.info(f"Delete cloud backup response:: {response.text}")
                logger.info(f"Test => [delete_hpe_cloud_backup] => PASS")
            except Exception as e:
                logger.error(
                    f"Failed to delete HPE cloud backup for ec2 instance {self.user.local_csp_machine_id}. Exception is {e}"
                )
                response.failure(
                    f"Failed to delete HPE cloud backup for ec2 instance {self.user.local_csp_machine_id}. Exception is {e}"
                )

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
            logger.info("Task => Backup completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"Backup failed with status'FAILED' error")
        else:
            raise Exception(f"Create backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")

    @tag("local_backup")
    @task
    def on_completion(self):
        logger.info("All expected tasks done, raising StopUser interrupt")
        raise StopUser()
