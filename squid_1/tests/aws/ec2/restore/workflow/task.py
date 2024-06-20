import json
import logging
import time
from locust import SequentialTaskSet, task
import logging
from requests import codes
from common import helpers
from lib.dscc.backup_recovery.aws_protection.assets import ec2
from tests.aws.config import Paths
from tenacity import retry, wait_exponential, stop_after_attempt
from common import common
from locust.exception import StopUser

logger = logging.getLogger(__name__)


class RestoreTasks(SequentialTaskSet):
    """
    Restore ec2_instance from s3 backup by creating new instance.
    That ec2 instance restore will be continue.
    """

    proxies = helpers.set_proxy()
    backup_id = None

    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def restore_ec2_instance_new(self):
        """Restore csp machine instance from the backup simultaneously by creating"""
        logger.info(f"Task [restore_ec2_instance_new] -> START")

        payload = self._restore_payload("restore_new", self.user.restore_tag)
        request_name = "Restore_new"
        with self.client.post(
            f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.user.backup_id}/restore",
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
            name=f"restore_new -> {Paths.CSP_MACHINE_INSTANCE_BACKUPS}/<id>/restore",
        ) as response:
            try:
                logger.info(f"restore to new instance-Response code is {response.status_code}")
                if response.status_code == codes.accepted:
                    start_time = time.time()
                    start_perf_counter = time.perf_counter()
                    self._verify_restore_task_status(response)
                    response.success()
                    restore_time = (time.perf_counter() - start_perf_counter) * 1000
                    try:
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=request_name,
                            exception=None,
                            start_time=start_time,
                            response_time=restore_time,
                            response_result=response.text,
                        )

                    except Exception as e:
                        helpers.custom_locust_response(
                            environment=self.user.environment, name=request_name, exception=e
                        )

                    # Record the restored instance list so that it can be cleaned up at the end
                    logger.info(
                        f"Restore to new is completed. restored ec2:{payload['targetMachineInstanceInfo']['name']}"
                    )
                    self.user.restored_ec2_list.append(payload["targetMachineInstanceInfo"]["name"])
                    logger.info(f"Task [restore_ec2_instance_new] -> PASS")
                else:
                    response.failure(
                        f"[restore_ec2_instance_new] [EC2- {self.user.ec2_object.id}] - Failed to restore , StatusCode: {str(response.status_code)} and response is {response.text}"
                    )
            except Exception as e:
                response.failure(f"Error occured while restore to new instance: {e}")
            finally:
                logger.info(f"restore to new instance:{response.text}")

    def _restore_payload(self, name, tag, operationType="CREATE"):
        """restore to new ec2 instance payload will be created

        Returns:
            dict: payload
        """
        csp_machine = self.user.csp_machine
        cspInfo = csp_machine["cspInfo"]
        nwInfo = csp_machine["cspInfo"]["networkInfo"]
        security_group_id_list = [sgid["cspId"] for sgid in nwInfo["securityGroups"]]

        tags = [dict(item) for item in tag]
        payload = {
            "backupId": self.user.backup_id,
            "operationType": operationType,
            "originalMachineInstanceInfo": {"terminateOriginal": False},
            "targetMachineInstanceInfo": {
                "accountId": self.user.account_id,
                "cspInfo": {
                    "availabilityZone": cspInfo["availabilityZone"],
                    "instanceType": cspInfo["instanceType"],
                    "keyPairName": cspInfo["keyPairName"],
                    "cspRegion": cspInfo["cspRegion"],
                    "securityGroupIds": security_group_id_list,
                    "subnetCspId": cspInfo["networkInfo"]["subnetInfo"]["id"],
                    "cspTags": tags,
                },
                "name": f"{csp_machine['name']}-{name}{helpers.generate_date()}",
            },
        }

        return payload

    def _verify_restore_task_status(self, restore_response):
        """verify restore task status in atlas

        Args:
            restore_response (dict): restore post call response
        """
        task_uri = restore_response.headers["location"]
        # task_uri = restore_response.json()["taskUri"]
        task_status = helpers.wait_for_task(task_uri=task_uri, timeout_minutes=25, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            logger.info("Backup restored successfully")
        else:
            restore_response.failure(
                f"Restore from local backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
            )

    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def restore_ec2_instance_by_replace(self):
        """Restore csp machine instance from the backup simultaneously by replacing"""

        logger.info(f"Task [restore_ec2_instance_by_replace] -> START")
        payload = self._restore_payload("restore_replace", self.user.restore_tag, operationType="REPLACE")
        request_name = "Restore_replace"
        with self.client.post(
            f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.user.backup_id}/restore",
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
            name=f"restore replace-> {Paths.CSP_MACHINE_INSTANCE_BACKUPS}/<id>/restore",
        ) as response:
            try:
                logger.info(f"restore by replace instance-Response code is {response.status_code}")
                if response.status_code == codes.accepted:
                    start_time = time.time()
                    start_perf_counter = time.perf_counter()
                    self._verify_restore_task_status(response)
                    response.success()
                    restore_time = (time.perf_counter() - start_perf_counter) * 1000
                    try:
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=request_name,
                            exception=None,
                            start_time=start_time,
                            response_time=restore_time,
                            response_result=response.text,
                        )
                    except Exception as e:
                        helpers.custom_locust_response(
                            environment=self.user.environment, name=request_name, exception=e
                        )
                    logger.info(
                        f"Restore to replace is completed. restored ec2:{payload['targetMachineInstanceInfo']['name']}"
                    )
                    self.user.restored_ec2_list.append(payload["targetMachineInstanceInfo"]["name"])
                    logger.info(f"Task [restore_ec2_instance_by_replace] -> PASS")
                else:
                    response.failure(
                        f"[restore_ec2_instance_by_replace] [EC2- {self.user.ec2_object.id}] - Failed to restore by replace, StatusCode: {str(response.status_code)} and response is {response.text}"
                    )
            except Exception as e:
                response.failure(f"Error occured while restore to replace instance: {e}")
            finally:
                logger.info(f"restore by replace instance:{response.text}")

    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_block_device_mapping_for_backup(self):
        # Query the block device mapping for given backup
        self._get_first_backup_id()
        with self.client.get(
            f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.backup_to_be_listed}/block-device-mappings",
            headers=self.user.headers.authentication_header,
            proxies=self.proxies,
            catch_response=True,
            name="GetBlockDeviceMappingsOfBackup",
        ) as response:
            logger.info(f"Get block-device-mappings - Response code is {response.status_code}")
            response_data = response.json()
            logger.info(f"Block device mappings response data : {response_data}")
            self.user.block_device_mappings = response_data
            return response_data

    def _get_first_backup_id(self):
        # The user will get first/latest the backup ID of the EC2 instance.
        if self.user.csp_machine_id:
            with self.client.get(
                f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}?filter=assetInfo/id eq '{self.user.csp_machine_id}'",
                headers=self.user.headers.authentication_header,
                proxies=self.proxies,
                catch_response=True,
            ) as response:
                logger.info(f"Get backups - Response code is {response.status_code}")
                response_data = response.json()
                logger.info(f"backup list", response_data)
                if len(response_data["items"]) != 0:
                    logger.info(
                        f"Pick the first backup from list : {response_data['items']} for {self.user.csp_machine_id}"
                    )
                    self.backup_to_be_listed = response_data["items"][0]["id"]
                    logger.info(
                        f"Picked the backup with ID : {response_data['items'][0]['id']} for {self.user.csp_machine_id}"
                    )
                else:
                    logger.error(
                        f"No backups available for ec2 instance with csp_machine_id: {self.user.csp_machine_id}"
                    )
                    self.user.environment.reached_end = True
                    self.user.environment.runner.quit()
        else:
            logger.error("No ec2 instance available")

    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def post_single_volume_restore_attach(self):
        # Post API call for restoing single volume from the backup
        #     """Restore single csp volume from the backup simultaneously by attach"""

        logger.info(f"Task [restore_single_volume_by_attach] -> START")
        payload = self._restore_volume_payload(
            "restore_single_volume_by_attach", self.user.restore_tag, operationType="ATTACH"
        )
        request_name = "RestoreSingleVolumeAttach"
        logging.info(f"Sending payload to restore_single_volume_by_attach post API => {payload}")
        with self.client.post(
            f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.user.backup_id}/restore-volume",
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
            name=f"restore single volume - attach -> {Paths.CSP_MACHINE_INSTANCE_BACKUPS}/<id>/restore-volume",
        ) as response:
            try:
                logger.info(f"restore single volume - attach - Response code is {response.status_code}")
                if response.status_code == codes.accepted:
                    start_time = time.time()
                    start_perf_counter = time.perf_counter()
                    self._verify_restore_task_status(response)
                    response.success()
                    restore_time = (time.perf_counter() - start_perf_counter) * 1000
                    try:
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=request_name,
                            exception=None,
                            start_time=start_time,
                            response_time=restore_time,
                            response_result=response.text,
                        )
                    except Exception as e:
                        helpers.custom_locust_response(
                            environment=self.user.environment, name=request_name, exception=e
                        )
                    logger.info(
                        f"restore single volume - attach is completed. restored ec2:{payload['targetVolumeInfo']['name']}"
                    )
                    self.user.restored_ebs_list.append(payload["targetVolumeInfo"]["name"])
                    logger.info(f"Task [restore_single_volume_by_attach] -> PASS")
                else:
                    response.failure(
                        f"[restore_single_volume_by_attach] [EC2- {self.user.ec2_object.id}] - Failed to restore volume - attach, StatusCode: {str(response.status_code)} and response is {response.text}"
                    )
            except Exception as e:
                response.failure(f"Error occured while restore single volume - attach to an instance: {e}")
            finally:
                logger.info(f"restore single volume - attach instance:{response.text}")

    def _restore_volume_payload(self, name, tag, operationType="ATTACH"):
        """create payload for post call to restore single volume from ec2 instance

        Returns:
            dict: payload
        """
        csp_machine = self.user.csp_machine
        instanceAttachmentInfo = {"attachmentType": operationType, "machineInstanceId": self.user.csp_machine_id}
        block_device_mappings = self.user.block_device_mappings
        logger.info(f"block_device_mappings is {block_device_mappings}")
        cspInfo = csp_machine["cspInfo"]
        tags = [dict(item) for item in tag]
        targetVolumeInfo = {
            "accountId": self.user.account_id,
            "cspInfo": {
                "availabilityZone": cspInfo["availabilityZone"],
                "iops": block_device_mappings[0]["ebs"]["iops"],
                "isEncrypted": False,
                "multiattach": False,
                "cspRegion": cspInfo["cspRegion"],
                "sizeInGiB": block_device_mappings[0]["ebs"]["volumeSize"],
                "cspTags": tags,
                "throughputInMiBps": block_device_mappings[0]["ebs"]["throughputInMiBps"],
                "volumeType": block_device_mappings[0]["ebs"]["volumeType"],
            },
            "name": f"restored-vol-{name}{helpers.generate_date()}",
        }

        if operationType == "REPLACE":
            instanceAttachmentInfo["deleteOriginalVolume"] = True
        else:
            instanceAttachmentInfo["deleteOriginalVolume"] = False
            instanceAttachmentInfo["device"] = "/dev/sdh"
        payload = {
            "backupId": self.user.backup_id,
            "deviceName": block_device_mappings[0]["deviceName"],
            "targetVolumeInfo": targetVolumeInfo,
        }
        return payload

    @task
    @retry(
        retry=common.is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def post_restore_volumes_to_ec2_instance(self):
        # Post API call for restoring multiple volumes from backup of ec2 instance
        #     """Restore multiple volumes the backup of ec2 instance simultaneously by attaching few ebs volumes"""

        logger.info(f"Task [restore_volumes_to_ec2_instance] -> START")
        payload = self._restore_ec2_volumes_payload(
            "restore_volumes_to_ec2_instance", self.user.restore_tag, operationType="CREATE"
        )
        request_name = "RestoreVolumesToEc2Instance"
        logging.info(f"Sending payload to restore_volumes_to_ec2_instance post API => {payload}")
        with self.client.post(
            f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.user.backup_id}/restore",
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
            name=f"restore_volumes_to_ec2_instance - create -> {Paths.CSP_MACHINE_INSTANCE_BACKUPS}/<id>/restore",
        ) as response:
            try:
                logger.info(f"restore_volumes_to_ec2_instance - create - Response code is {response.status_code}")
                if response.status_code == codes.accepted:
                    start_time = time.time()
                    start_perf_counter = time.perf_counter()
                    self._verify_restore_task_status(response)
                    response.success()
                    restore_time = (time.perf_counter() - start_perf_counter) * 1000
                    try:
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=request_name,
                            exception=None,
                            start_time=start_time,
                            response_time=restore_time,
                            response_result=response.text,
                        )
                    except Exception as e:
                        helpers.custom_locust_response(
                            environment=self.user.environment, name=request_name, exception=e
                        )
                    logger.info(
                        f"restore_volumes_to_ec2_instance - create is completed. restored ec2:{payload['targetMachineInstanceInfo']['name']}"
                    )
                    self.user.restored_ec2_list.append(payload["targetMachineInstanceInfo"]["name"])
                    logger.info(f"Task [restore_volumes_to_ec2_instance] -> PASS")
                else:
                    response.failure(
                        f"[restore_volumes_to_ec2_instance] [EC2- {self.user.ec2_object.id}] - Failed to restore_volumes_to_ec2_instance, StatusCode: {str(response.status_code)} and response is {response.text}"
                    )
            except Exception as e:
                response.failure(f"Error occured while restore_volumes_to_ec2_instance - create : {e}")
            finally:
                logger.info(f"restore_volumes_to_ec2_instance - create:{response.text}")

    def _restore_ec2_volumes_payload(self, name, tag, operationType="CREATE"):
        """Returns payload for restore_volumes_to_ec2_instance - create Post call

        Returns:
            dict: payload
        """
        csp_machine = self.user.csp_machine
        block_device_mappings = self.user.block_device_mappings[0:2]
        logger.info(f"block_device_mappings is {block_device_mappings}")
        cspInfo = csp_machine["cspInfo"]
        nwInfo = csp_machine["cspInfo"]["networkInfo"]
        security_group_id_list = [sgid["cspId"] for sgid in nwInfo["securityGroups"]]
        tags = [dict(item) for item in tag]
        targetMachineInstanceInfo = {
            "accountId": self.user.account_id,
            "cspInfo": {
                "availabilityZone": cspInfo["availabilityZone"],
                "instanceType": cspInfo["instanceType"],
                "keyPairName": cspInfo["keyPairName"],
                "cspRegion": cspInfo["cspRegion"],
                "cspTags": tags,
                "securityGroupIds": security_group_id_list,
                "subnetCspId": cspInfo["networkInfo"]["subnetInfo"]["id"],
                "blockDeviceMappings": block_device_mappings,
            },
            "name": f"restored-ec2-{name}{helpers.generate_date()}",
        }
        payload = {
            "backupId": self.user.backup_id,
            "operationType": operationType,
            "originalMachineInstanceInfo": {
                "terminateOriginal": False,
            },
            "targetMachineInstanceInfo": targetMachineInstanceInfo,
        }
        return payload

    @task
    def on_completion(self):
        logger.info("All expected tasks done, raising StopUser interrupt")
        raise StopUser()

    def on_stop(self):
        logger.info(f"Restore instance list:{self.user.restored_ec2_list}")
        logger.info(f"Restore volume list:{self.user.restored_ebs_list}")
