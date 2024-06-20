"""
Test steps
[PSR] Number of simultaneous request to create a new protection group
[PSR] Number of simultaneous request to get the details of a protection group
[PSR] Number of simultaneous request to modify the protection group
[PSR] Number of simultaneous request to get the list. of protection groups
"""

import time
from locust import SequentialTaskSet, task
from requests import codes
from common import helpers
import tests.aws.config as config
from lib.dscc.backup_recovery.aws_protection.assets import ec2 as ec2asset
import json
import requests
import logging
import uuid
from lib.dscc.backup_recovery.protection import protection_group
from tenacity import retry, wait_exponential, stop_after_attempt
from common.common import is_retry_needed

logger = logging.getLogger(__name__)


class ProtectionGroupTasks(SequentialTaskSet):
    """Protection group tasks such as create,detail,list and modify performance are validated."""

    def on_start(self):
        self.csp_account = self.user.account.get_csp_account()
        self.protection_group_id = None

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def create_protection_group(self):
        self.protection_group_name = f"perfauto_create_protection_group_{uuid.uuid4().hex}"
        try:
            """Creates protection groups will be done simultaneously"""
            protection_group_name = self.protection_group_name
            csp_instance1 = ec2asset.get_csp_machine(self.user.ec2_instance_id1)
            csp_instance2 = ec2asset.get_csp_machine(self.user.ec2_instance_id2)
            csp_instance_ids_list = []
            csp_instance1_id = csp_instance1["id"]
            csp_instance_ids_list.append(csp_instance1_id)
            csp_instance2_id = csp_instance2["id"]
            csp_instance_ids_list.append(csp_instance2_id)

            payload = {
                "accountIds": [self.csp_account["id"]],
                "assetType": "hybrid-cloud/csp-machine-instance",
                "description": "Creating new protection group for perf test",
                "membershipType": "STATIC",
                "name": protection_group_name,
                "cspRegions": [self.user.region],
                "staticMemberIds": csp_instance_ids_list,
            }
            logger.debug(f"[Create protection group ][payload] : {payload}")
            with self.client.post(
                config.Paths.PROTECTION_GROUPS,
                data=json.dumps(payload),
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="Create protection group",
            ) as response:
                try:
                    logger.info(f"Create protection group-Response code is {response.status_code}")
                    if response.status_code == requests.codes.accepted:
                        response_data = response.json()
                        task_uri = response.headers["location"]
                        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
                        if task_status == helpers.TaskStatus.success:
                            logger.info(f"Protection group-{protection_group_name} created successfully")
                            self.protection_group_id = protection_group.get_protection_group_id(protection_group_name)
                            # self.user.protection_group_list.append(protection_group_id)
                        elif task_status == helpers.TaskStatus.timeout:
                            raise Exception(
                                f"Creating protection group-{protection_group_name} failed with timeout error"
                            )
                        elif task_status == helpers.TaskStatus.failure:
                            raise Exception(
                                f"Creating protection group-{protection_group_name} failed with status'FAILED' error"
                            )
                        else:
                            raise Exception(
                                f"Creating protection group-{protection_group_name} failed with unknown error"
                            )
                        # return response_data
                    else:
                        response.failure(
                            f"Failed to create protection group, StatusCode: {str(response.status_code)} , Response text: {response.text}"
                        )
                        logger.info(f"[create_protection_group]: {response.text}")
                except Exception as e:
                    response.failure(f"Error while creatig protection group:{e}")
                    raise e
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment, name="Create Protection group", exception=e
            )
            logger.error(f"Failed to create protection group {e}")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def list_protection_group(self):
        """Return the list of protection groups"""

        try:
            with self.client.get(
                config.Paths.PROTECTION_GROUPS,
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="List protection group",
            ) as response:
                try:
                    logger.info(f"List protection group-response code is: {response.status_code}")
                    if response.status_code == codes.ok:
                        resp_json = response.json()
                        protection_groups = resp_json["items"]
                        logger.debug(f"Protection groups {protection_groups}")
                    else:
                        logger.error(f"List protection group-response is: {response.text}")
                        response.failure(
                            f"Unable to get list of protection_groups StatusCode: {str(response.status_code)} -> response: {response.text}"
                        )

                    logger.info(f"List protection group response text is {response.text}")
                except Exception as e:
                    response.failure(f"Error while list protection group:{e}")
                    raise e

        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="List Protection group",
                exception=e,
            )

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(5),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def detail_protection_group(self):
        """Provides detailed information of specified protection group"""
        try:
            if self.protection_group_id:
                with self.client.get(
                    f"{config.Paths.PROTECTION_GROUPS}/{self.protection_group_id}",
                    proxies=self.user.proxies,
                    headers=self.user.headers.authentication_header,
                    catch_response=True,
                    name="Detail Protection group",
                ) as response:
                    try:
                        logger.debug(
                            f"detail protection group -response status : {response.status_code} -> response text {response.text}"
                        )
                        if response.status_code != codes.ok:
                            response.failure(
                                f"Unable to get detail of a protection_group {self.protection_group_name} . status code {response.status_code} -> response {response.text}"
                            )
                        else:
                            logger.info(f"Detail protection group-response code is: {response.status_code}")
                            logger.info(f"Detail protection group response text is {response.text}")
                    except Exception as e:
                        response.failure(f"Error while detail protection group {self.protection_group_name}:{e}")
                        raise e
            else:
                logger.error(f"Protection group name:{self.protection_group_name} not listed")
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Detail Protection group",
                exception=e,
            )

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(5),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def modify_protection_group_rename(self):
        """Update the existing protection group by modifying protection group name"""
        try:
            if self.protection_group_id:
                modified_protection_name = f"perfauto_update_protection_group_{uuid.uuid4().hex}"
                csp_instance = ec2asset.get_csp_machine(self.user.ec2_instance_id_for_modify_protection)
                csp_instance_list = []
                resource_uri_dict = {}
                resource_uri_dict["resourceUri"] = csp_instance["resourceUri"]
                csp_instance_list.append(resource_uri_dict)
                payload = {
                    "description": "Updating protection group for perf auto test",
                    "name": modified_protection_name,
                }
                test_start_time = time.time()
                start_perf_counter = time.perf_counter()
                with self.client.patch(
                    f"{config.Paths.PROTECTION_GROUPS}/{self.protection_group_id}",
                    data=json.dumps(payload),
                    proxies=self.user.proxies,
                    headers=self.user.headers.authentication_header,
                    catch_response=True,
                    name="Modify Protection group",
                ) as response:
                    try:
                        logger.info(f"Modify protection group-Response code is {response.status_code}")
                        if response.status_code != codes.accepted:
                            response.failure(
                                f"Failed to to modify protecion group , StatusCode: {str(response.status_code)}, response: {response.text} requested URL-> {response.request.url}"
                            )
                        logger.info(f"Modify protection group-Response:{response.text}")
                        response_data = response.json()
                        task_uri = response.headers["location"]
                        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
                        if task_status == helpers.TaskStatus.success:
                            logger.info(f"Protection group- {modified_protection_name} modified successfully")
                        elif task_status == helpers.TaskStatus.timeout:
                            raise Exception(
                                f"Modifying protection group-{modified_protection_name} failed with timeout error"
                            )
                        elif task_status == helpers.TaskStatus.failure:
                            raise Exception(
                                f"Modifying protection group-{modified_protection_name} failed with status'FAILED' error"
                            )
                        else:
                            raise Exception(
                                f"Modifying protection group-{modified_protection_name} failed with unknown error"
                            )
                        logger.info(f"TEST->[modify_protection_group]->PASS")
                        logger.info(
                            f"Name of protection group {self.protection_group_name} modified to {modified_protection_name}"
                        )
                        self.protection_group_name = modified_protection_name
                        time_taken = (time.perf_counter() - start_perf_counter) * 1000
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name="Modify_protection_group",
                            exception=None,
                            start_time=test_start_time,
                            response_time=time_taken,
                        )
                    except Exception as e:
                        response.failure(
                            f"Error while modifying protection group-response code:{response.status_code} -> response {response.text}, error is: {e} and requested URL-> {response.request.url}"
                        )
                        raise e
            else:
                logger.error(f"Protection group name:{self.protection_group_name} not listed")
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Modify Protection group",
                exception=e,
            )

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(5),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def modify_protection_group_members(self):
        """Update the existing protection group by adding additional ec2 machine instances"""
        try:
            if self.protection_group_id:
                csp_instance = ec2asset.get_csp_machine(self.user.ec2_instance_id_for_modify_protection)
                csp_instance_list = []
                csp_instance_id = csp_instance["id"]
                csp_instance_list.append(csp_instance_id)
                payload = {
                    "staticMembersAdded": csp_instance_list,
                }
                test_start_time = time.time()
                start_perf_counter = time.perf_counter()
                with self.client.post(
                    f"{config.Paths.PROTECTION_GROUPS}/{self.protection_group_id}/update-static-members",
                    data=json.dumps(payload),
                    proxies=self.user.proxies,
                    headers=self.user.headers.authentication_header,
                    catch_response=True,
                    name="Modify Protection group static members",
                ) as response:
                    try:
                        logger.info(f"Modify protection group members -Response code is {response.status_code}")
                        if response.status_code != codes.accepted:
                            response.failure(
                                f"Failed to to modify protecion group members, StatusCode: {str(response.status_code)}, response: {response.text} Requested url::{response.request.url}"
                            )
                        logger.info(f"Modify protection group members - Response:{response.text}")
                        response_data = response.json()
                        task_uri = response.headers["location"]
                        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
                        if task_status == helpers.TaskStatus.success:
                            logger.info(f"Protection group- {self.protection_group_name} members modified successfully")
                        elif task_status == helpers.TaskStatus.timeout:
                            raise Exception(
                                f"Modifying protection group members -{self.protection_group_name} failed with timeout error"
                            )
                        elif task_status == helpers.TaskStatus.failure:
                            raise Exception(
                                f"Modifying protection group members -{self.protection_group_name} failed with status'FAILED' error"
                            )
                        else:
                            raise Exception(
                                f"Modifying protection group members -{self.protection_group_name} failed with unknown error"
                            )
                        logger.info(f"TEST->[modify_protection_group_members]->PASS")
                        logger.info(f"Protection group {self.protection_group_name} members updated successfully")
                        time_taken = (time.perf_counter() - start_perf_counter) * 1000
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name="Modify_protection_group_static_members",
                            exception=None,
                            start_time=test_start_time,
                            response_time=time_taken,
                        )
                    except Exception as e:
                        response.failure(
                            f"Error while modifying protection group members -response code:{response.status_code} -> response {response.text}, error is: {e}, Requested URL::{response.request.url}"
                        )
                        raise e
            else:
                logger.error(f"Protection group name:{self.protection_group_name} not listed")
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Modify Protection group static members",
                exception=e,
            )

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(5),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def delete_protection_group(self):
        try:
            if self.protection_group_id:
                with self.client.delete(
                    f"{config.Paths.PROTECTION_GROUPS}/{self.protection_group_id}",
                    proxies=self.user.proxies,
                    headers=self.user.headers.authentication_header,
                    catch_response=True,
                    name="Delete Protection group",
                ) as response:
                    logger.info(f"Delete protection group-> response code:{response.status_code}")
                    if response.status_code != requests.codes.accepted:
                        response.failure(
                            f"Delete protection group failed. Name: {self.protection_group_name} -> Id: {self.protection_group_id}"
                        )
                        logger.error(
                            f"Delete protection group failed. Response code {response.status_code}. Response text: {response.text}"
                        )
            else:
                logger.error(f"Protection group name:{self.protection_group_name} not listed")
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Delete Protection group",
                exception=f"Error while deleting protection group {self.protection_group_name}:: {e}",
            )
            raise e

    @task
    def on_completion(self):
        self.interrupt()
