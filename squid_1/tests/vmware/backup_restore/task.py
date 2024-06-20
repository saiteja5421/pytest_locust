"""
Test steps
[PSR] Number of simultaneous request to create local backups for ec2 instance
[PSR] Number of simultaneous request to create cloud backups for ec2 instance
[PSR] Number of simultaneous request to restore vm by replacing vm from local backup
[PSR] Number of simultaneous request to restore to new vm from cloud  backup
[PSR] Number of simultaneous requests to delete local backups
[PSR] Number of simultaneous requests to delete cloud backups

"""

from datetime import datetime
import os
import requests
import json
import time
import traceback
from locust import SequentialTaskSet, tag, task
from requests import codes
from common import helpers
from lib.dscc.backup_recovery.vmware_protection.vmware import VMwareSteps
from tests.vmware.vmware_config import Paths
from common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.dscc.backup_recovery.vmware_protection import backups
from tests.steps.vmware_steps import hypervisor
from lib.dscc.backup_recovery.vmware_protection.vcenter import refresh_vcenter

import logging

from tenacity import retry, wait_exponential, stop_after_attempt
from common import common

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins
from locust.exception import StopUser


logger = logging.getLogger(__name__)
VCENTER_NAME = os.environ.get("VCENTER_NAME")
VCENTER_USERNAME = os.environ.get("VCENTER_USERNAME")
VCENTER_PASSWORD = os.environ.get("VCENTER_PASSWORD")


class BackupTasks(SequentialTaskSet):
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
        logger.info("Task started")
        scheduleIds = backups.search_schedule_id_of_stores(self.user.protection_policy_id, BackupTypeScheduleIDs.local)
        backups_list = backups.get_backups(self.user.virtual_machine_id, "backups")
        assert backups_list.status_code == codes.ok, f"{backups_list.content}"
        backups_list = backups_list.json()
        url = f"{Paths.protection_jobs}/{self.user.protection_job_id}/run"
        payload = {"scheduleIds": [scheduleIds[0]]}
        meta_name = "Local backup"
        start_time = time.time()
        start_perf_counter = time.perf_counter()

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name=f"Create Virtual machine Local Backup -> {Paths.protection_jobs}/<protection_job_id>/run",
        ) as response:
            logger.info(f"Create on demand local backup-Response code is {response.status_code}")
            logger.info(f"Create local backup- Response text::{response.text}")
            if response.status_code == codes.accepted:
                try:
                    task_uri = response.headers["location"]
                    task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30, api_header=self.user.headers)
                    time.sleep(30)
                    latest_backup = backups.validate_new_backups(
                        asset_id=self.user.virtual_machine_id,
                        backups_list=backups_list,
                        backup_type=BackupTypeScheduleIDs.local,
                        timeout_minutes=10,
                    )
                    logger.info(
                        f"Local Backup is created successfully for virtual machine {self.user.virtual_machine_id}."
                    )
                    self.local_backup_id = latest_backup["id"]  # This will be used by delete backup task

                    backup_creation_time = (time.perf_counter() - start_perf_counter) * 1000
                    helpers.custom_locust_response(
                        environment=self.user.environment,
                        name=meta_name,
                        exception=None,
                        start_time=start_time,
                        response_time=backup_creation_time,
                        response_result=latest_backup,
                    )
                except requests.exceptions.ProxyError as e:
                    raise e

                except Exception as e:
                    logger.error(traceback.format_exc())
                    helpers.custom_locust_response(environment=self.user.environment, name=meta_name, exception=e)
            else:
                response.failure(
                    f"Failed to to create local Backup, StatusCode: {str(response.status_code)} ,Response text: {response.text}. Partial url {Paths.protection_jobs}/{self.user.protection_job_id}/run"
                )

            logger.info(f"Create local backup- Response text::{response.text}")
            logger.info("Test => [create_on_demand_local_backup] -> PASS")

    @tag("cloud_backup")
    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def create_on_demand_cloud_backup(self):
        """Create HPE Cloud backup on demand"""
        logger.info("Task started")
        scheduleIds = backups.search_schedule_id_of_stores(self.user.protection_policy_id, BackupTypeScheduleIDs.cloud)
        backups_list = backups.get_backups(self.user.virtual_machine_id, "backups")
        assert backups_list.status_code == codes.ok, f"{backups_list.content}"
        backups_list = backups_list.json()
        url = f"{Paths.protection_jobs}/{self.user.protection_job_id}/run"
        payload = {"scheduleIds": [scheduleIds[0]]}
        meta_name = "Cloud backup"
        start_time = time.time()
        start_perf_counter = time.perf_counter()

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name=f"Create Virtual machine Cloud Backup -> {Paths.protection_jobs}/<protection_job_id>/run",
        ) as response:
            logger.info(f"Create on demand Cloud backup-Response code is {response.status_code}")
            logger.info(f"Create Cloud backup- Response text::{response.text}")
            if response.status_code == codes.accepted:
                try:
                    task_uri = helpers.get_task_uri_from_header(response)
                    task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30, api_header=self.user.headers)
                    time.sleep(30)
                    latest_backup = backups.validate_new_backups(
                        asset_id=self.user.virtual_machine_id,
                        backups_list=backups_list,
                        backup_type=BackupTypeScheduleIDs.cloud,
                        timeout_minutes=10,
                    )
                    logger.info(
                        f"Cloud Backup is created successfully for virtual machine {self.user.virtual_machine_id}."
                    )
                    self.cloud_backup_id = latest_backup["id"]  # This will be used by delete backup task

                    backup_creation_time = (time.perf_counter() - start_perf_counter) * 1000
                    helpers.custom_locust_response(
                        environment=self.user.environment,
                        name=meta_name,
                        exception=None,
                        start_time=start_time,
                        response_time=backup_creation_time,
                        response_result=latest_backup,
                    )
                except requests.exceptions.ProxyError as e:
                    raise e

                except Exception as e:
                    logger.error(traceback.format_exc())
                    helpers.custom_locust_response(environment=self.user.environment, name=meta_name, exception=e)
            else:
                response.failure(
                    f"Failed to to create cloud Backup, StatusCode: {str(response.status_code)} ,Response text: {response.text}. Partial url {Paths.protection_jobs}/{self.user.protection_job_id}/run"
                )

            logger.info(f"Create cloud backup- Response text::{response.text}")
            logger.info("Test => [create_on_demand_cloud_backup] -> PASS")

    @tag("restore")
    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def restore_to_existing_vm(self):
        """Restore Local backup by replacing existing VM"""
        logger.info("Task started")
        config = helpers.read_config()
        url = f"{Paths.virtual_machines_backups}/{self.user.virtual_machine_id}/restore"
        payload = {"backupId": self.local_backup_id, "restoreType": "PARENT"}
        meta_name = "Restore to existing VM"
        start_time = time.time()
        start_perf_counter = time.perf_counter()

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name=f"Restore to existing vm from local backup -> {Paths.virtual_machines_backups}/<virtual_machine_id>/restore",
        ) as response:
            logger.info(f"Restore to existing vm from local backup-Response code is {response.status_code}")
            logger.info(f"Restore local backup- Response text::{response.text}")
            if response.status_code == codes.accepted:
                try:
                    task_uri = helpers.get_task_uri_from_header(response)
                    task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30, api_header=self.user.headers)
                    if task_status == helpers.TaskStatus.success:
                        restore_completion_time = (time.perf_counter() - start_perf_counter) * 1000
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=meta_name,
                            exception=None,
                            start_time=start_time,
                            response_time=restore_completion_time,
                            response_result=response,
                        )
                        logger.info("Task => Restore to Existing VM task completed successfully")
                        refresh_vcenter(vcenter_id="dd7f33e1-76f1-4877-a8bd-fa64147df9d4")
                        time.sleep(30)
                        vcenter = VMwareSteps(VCENTER_NAME, VCENTER_USERNAME, VCENTER_PASSWORD)
                        if vcenter.search_vm(self.user.vm_name):
                            logger.info(f"Replaced VM {self.user.vm_name} found successful after restore")
                    elif task_status == helpers.TaskStatus.timeout:
                        raise Exception("Restore to Existing VM task failed with timeout error")
                    elif task_status == helpers.TaskStatus.failure:
                        raise Exception("Restore to Existing VM task failed with status'FAILED' error")
                    else:
                        raise Exception(
                            f"Restore to Existing VM task failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
                        )
                except requests.exceptions.ProxyError as e:
                    raise e

                except Exception as e:
                    logger.error(traceback.format_exc())
                    helpers.custom_locust_response(environment=self.user.environment, name=meta_name, exception=e)

            else:
                response.failure(
                    f"Failed to Restore to Existing VM, StatusCode: {str(response.status_code)} ,Response text: {response.text}. Partial url {Paths.virtual_machines_backups}/{self.user.virtual_machine_id}/restore"
                )
        logger.info(f"Restore to Existing VM - Response text::{response.text}")
        logger.info("Test => [restore_to_existing_vm] -> PASS")

    @tag("restore")
    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def restore_to_new_vm(self):
        """Restore to New VM using Cloud backup"""
        logger.info("Task started")
        config = helpers.read_config()
        datastore_name = config["testInput"]["vcenter_details"]["datastore"]
        host_name = config["testInput"]["vcenter_details"]["host"]
        restore_vm_name = self.user.vm_name + "_restored"
        datastore_id = hypervisor.get_datastore_id(datastore_name, VCENTER_NAME)
        vcenter_id = hypervisor.get_vcenter_id_by_name(VCENTER_NAME)
        host_id = hypervisor.get_host_id(host_name)
        url = f"{Paths.virtual_machines_backups}/{self.user.virtual_machine_id}/restore"
        payload = {
            "backupId": self.cloud_backup_id,
            "restoreType": "ALTERNATE",
            "targetVmInfo": {
                "appInfo": {"vmware": {"datastoreId": datastore_id}},
                "hostId": host_id,
                "name": restore_vm_name,
                "powerOn": True,
            },
        }
        meta_name = "Restore to New VM"
        start_time = time.time()
        logger.info(f"start time {start_time}")
        start_perf_counter = time.perf_counter()

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name=f"Restore to New vm from Cloud backup -> {Paths.virtual_machines_backups}/<virtual_machine_id>/restore",
        ) as response:
            logger.info(f"Restore to New vm from Cloud backup-Response code is {response.status_code}")
            logger.info(f"Restore from Cloud backup- Response text::{response.text}")
            if response.status_code == codes.accepted:
                try:
                    task_uri = helpers.get_task_uri_from_header(response)
                    task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30, api_header=self.user.headers)
                    if task_status == helpers.TaskStatus.success:
                        logger.info("Task => Restore to New VM task completed successfully")
                        restore_completion_time = (time.perf_counter() - start_perf_counter) * 1000
                        logger.info(f"time taken {restore_completion_time}")
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=meta_name,
                            exception=None,
                            start_time=start_time,
                            response_time=restore_completion_time,
                        )
                        refresh_vcenter(vcenter_id=vcenter_id)
                        time.sleep(60)
                        vcenter = VMwareSteps(VCENTER_NAME, VCENTER_USERNAME, VCENTER_PASSWORD)
                        if vcenter.search_vm(restore_vm_name):
                            logger.info(f"Restore VM {restore_vm_name} found successful after restore")
                            vcenter.delete_vm(restore_vm_name)
                            logger.info("Restored VM deleted successfully")
                    elif task_status == helpers.TaskStatus.timeout:
                        raise Exception("Restore to New VM task failed with timeout error")
                    elif task_status == helpers.TaskStatus.failure:
                        raise Exception("Restore to New VM task failed with status'FAILED' error")
                    else:
                        raise Exception(
                            f"Restore to New VM task failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
                        )
                except requests.exceptions.ProxyError as e:
                    raise e

                except Exception as e:
                    logger.error(traceback.format_exc())
                    helpers.custom_locust_response(environment=self.user.environment, name=meta_name, exception=e)

            else:
                response.failure(
                    f"Failed to Restore to New VM, StatusCode: {str(response.status_code)} ,Response text: {response.text}. Partial url {Paths.virtual_machines_backups}/{self.user.virtual_machine_id}/restore"
                )
        logger.info(f"Restore to News VM - Response text::{response.text}")
        logger.info("Test => [restore_to_new_vm] -> PASS")

    @tag("local_backup")
    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def delete_local_backup(self):
        """Delete the hpe local backup"""

        with self.client.delete(
            f"{Paths.virtual_machines_backups}/{self.user.virtual_machine_id}/backups/{self.local_backup_id}",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name=f"Delete Local backup -> {Paths.virtual_machines_backups}/{self.user.virtual_machine_id}/backups/{self.local_backup_id}",
        ) as response:
            logger.info(f"Delete local backup-Response code is {response.status_code}")
            task_uri = helpers.get_task_uri_from_header(response)
            if response.status_code == codes.accepted:
                self.verify_backup_task_status(task_uri)
            else:
                response.failure(
                    f"Failed to to delete local Backup, StatusCode: {str(response.status_code)},Response text: {response.text} . Partial url {self.user.virtual_machine_id}/backups/{self.local_backup_id}"
                )
            logger.info(f"Delete local backup- Response text::{response.text}")
            logger.info("Task [delete_hpe_cloud_backup] -> PASS")

    @tag("cloud_backup")
    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def delete_cloud_backup(self):
        """Delete the hpe cloud backup"""

        with self.client.delete(
            f"{Paths.virtual_machines_backups}/{self.user.virtual_machine_id}/backups/{self.cloud_backup_id}",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name=f"Delete Cloud backup -> {Paths.virtual_machines_backups}/{self.user.virtual_machine_id}/backups/{self.cloud_backup_id}",
        ) as response:
            logger.info(f"Delete local backup-Response code is {response.status_code}")
            if response.status_code == codes.accepted:
                task_uri = helpers.get_task_uri_from_header(response)
                self.verify_backup_task_status(task_uri)
            else:
                response.failure(
                    f"Failed to to delete cloud Backup, StatusCode: {str(response.status_code)},Response text: {response.text} . Partial url {self.user.virtual_machine_id}/backups/{self.cloud_backup_id}"
                )
            logger.info(f"Delete cloud backup- Response text::{response.text}")
            logger.info("Task [delete_hpe_cloud_backup] -> PASS")

    @task
    def on_completion(self):
        logger.info("All expected tasks done, raising StopUser interrupt")
        raise StopUser()

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

        task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            logger.info("Task => Backup completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception("Backup failed with status'FAILED' error")
        else:
            raise Exception(f"Create backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")
