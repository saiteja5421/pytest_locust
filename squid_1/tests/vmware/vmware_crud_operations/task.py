import json
import logging
import random
import string
import time

from locust.exception import StopUser
from locust import SequentialTaskSet, task
import requests
from common import helpers
from lib.dscc.backup_recovery.vmware_protection.protection_store import get_protection_store_by_name
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway import get_psg_by_name
from tests.steps.vmware_steps.psg_steps import generate_psg_payload, generate_payload_for_nic_creation
from tests.vmware.vmware_config import Paths, AwsStorageLocation
from tests.steps.vmware_steps.protection_store_steps import generate_protection_store_payload
from tests.steps.vmware_steps import hypervisor

logger = logging.getLogger(__name__)


class ProtectionStoregateway(SequentialTaskSet):
    """CRUD workflow for PSG.

    Args:
        SequentialTaskSet: this helps to run tasks in sequential order
    """

    def on_start(self):
        if self.user.ip_address:
            self.user_ip = self.user.ip_address.pop()
        else:
            logger.info("No more ip_address to process.")
            # StopUser() will stop single user if there is no ip_address.
            raise StopUser()

        if self.user.nic_ip:
            self.nic_ip = self.user.nic_ip.pop()
        else:
            logger.info("No more nic_ip to process.")
            # self.user.environment.runner.quit()
            # StopUser() will stop single user if there is no nic_ip.
            raise StopUser()

    @task
    def create_psg(self):
        """creates protection store gateways simultaneously for number of users"""
        psgw_name = "PSR_S1_PQA"
        psg_name_suffix = "".join(random.choice(string.ascii_letters) for _ in range(8))
        psg_name = f"{psgw_name.split('#')[0]}_{psg_name_suffix}"
        network_ip = f"{self.user_ip}"
        payload = generate_psg_payload(
            psg_name,
            self.user.vcenter_id,
            self.user.host_id,
            self.user.network_name,
            network_ip,
            self.user.subnet_mask,
            self.user.gateway,
            self.user.network_type,
            self.user.dns_ip,
            self.user.datastore_id,
        )
        logger.info(f"payload for creating psg: {payload}")
        meta_name = "Create Protection store gateway"
        start_time = time.time()
        start_perf_counter = time.perf_counter()
        self.user.psg_name = psg_name
        path = f"{Paths.protection_store_gateways}"
        with self.client.post(
            path,
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            data=payload,
            catch_response=True,
        ) as response:
            logger.info(response)
            logger.info(f"Create psg - Response text::{response.text}")
            if response.status_code == requests.codes.accepted:
                task_id = response.headers.get("Location")
                logger.info(f"create psg task id : {task_id.split('/')[-1]}")
                self.verify_task_status(response, "create psg")

            else:
                response.failure(f"Failed to to create psg, StatusCode: {str(response.status_code)}")
        psg_details = get_psg_by_name(self.user.psg_name)
        self.user.psg_id = psg_details["id"]
        psg_creation_time = (time.perf_counter() - start_perf_counter) * 1000
        helpers.custom_locust_response(
            environment=self.user.environment,
            name=meta_name,
            exception=None,
            start_time=start_time,
            response_time=psg_creation_time,
            response_result=psg_details,
        )
        logger.info(f"Successfully deployed PSGW.")

    @task
    def create_local_store(self):
        """creates local protection store simultaneously for number of users"""
        if self.user.psg_id:
            payload = generate_protection_store_payload(self.user.psg_name, "ON_PREMISES")
            logger.info(f"payload for creating local protection store: {payload}")
            payload_obj = json.loads(payload)
            meta_name = "Create Local Protection Store"
            start_time = time.time()
            start_perf_counter = time.perf_counter()
            self.user.local_protection_store_name = payload_obj["displayName"]
            url = f"{Paths.protection_stores}"
            with self.client.post(
                url,
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                data=payload,
                catch_response=True,
            ) as response:
                logger.info(f"Create local protection store- Response text::{response.text}")
                if response.status_code == requests.codes.accepted:
                    task_id = response.headers.get("Location")
                    logger.info(f"create protection store task id : {task_id.split('/')[-1]}")
                    self.verify_task_status(response, "create local protection store")
                else:
                    response.failure(f"Failed to to create protection store, StatusCode: {str(response.status_code)}")
            protection_store = get_protection_store_by_name(self.user.local_protection_store_name)
            self.user.local_protection_store_id = protection_store["id"]
            logger.info(f"Successfully deployed local protection store.")
            localstore_creation_time = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name=meta_name,
                exception=None,
                start_time=start_time,
                response_time=localstore_creation_time,
                response_result=protection_store,
            )
        else:
            logger.error(f"No psg found with name: {self.user.psg_name}")

    @task
    def create_network_interface(self):
        """creates nic simultaneously for number of users"""
        if self.user.psg_id:
            nic_ip = f"{self.nic_ip}"
            network_name = "Data1"
            network_type = "STATIC"
            subnet = "255.255.248.0"
            gateway = ""
            payload = generate_payload_for_nic_creation(nic_ip, network_name, network_type, subnet, gateway)
            logger.info(f"payload for creating networt interface for {self.user.psg_name}: {payload}")
            meta_name = "Create Network Interface"
            start_time = time.time()
            start_perf_counter = time.perf_counter()
            url = f"{Paths.protection_store_gateways}/{self.user.psg_id}/createNic"
            with self.client.post(
                url,
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                data=payload,
                catch_response=True,
            ) as response:
                logger.info(f"Create nic- Response text::{response.text}")
                if response.status_code == requests.codes.accepted:
                    task_id = response.headers.get("Location")
                    logger.info(f"create nic task id : {task_id.split('/')[-1]}")
                    self.verify_task_status(response, "create nic")
                    nw_interface_creation_time = (time.perf_counter() - start_perf_counter) * 1000
                    helpers.custom_locust_response(
                        environment=self.user.environment,
                        name=meta_name,
                        exception=None,
                        start_time=start_time,
                        response_time=nw_interface_creation_time,
                        response_result=response.text,
                    )
                else:
                    response.failure(f"Failed to to create nic, StatusCode: {str(response.status_code)}")
        else:
            logger.error(f"No psg found with name: {self.user.psg_name}")

    @task
    def create_cloud_store(self):
        """
        creates cloud protection store simultaneously for number of users
        """
        if self.user.cloud_regions:
            self.cloud_region = self.user.cloud_regions.pop()

        if self.user.psg_id:
            payload = generate_protection_store_payload(self.user.psg_name, "CLOUD", self.cloud_region)
            logger.info(f"payload for creating cloud protection store {payload}")
            payload_obj = json.loads(payload)
            self.user.cloud_protection_store_name = payload_obj["displayName"]
            meta_name = "Create Cloud protection store"
            start_time = time.time()
            start_perf_counter = time.perf_counter()
            url = f"{Paths.protection_stores}"
            with self.client.post(
                url,
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                data=payload,
                catch_response=True,
            ) as response:
                logger.info(f"Create local protection store- Response text::{response.text}")
                if response.status_code == requests.codes.accepted:
                    task_id = response.headers.get("Location")
                    logger.info(f"create protection store task id : {task_id.split('/')[-1]}")
                    self.verify_task_status(response, "create cloud protection store")
                else:
                    response.failure(f"Failed to to create protection store, StatusCode: {str(response.status_code)}")
            protection_store = get_protection_store_by_name(self.user.cloud_protection_store_name)
            self.user.cloud_protection_store_id = protection_store["id"]
            cloud_store_creation_time = (time.perf_counter() - start_perf_counter) * 1000
            helpers.custom_locust_response(
                environment=self.user.environment,
                name=meta_name,
                exception=None,
                start_time=start_time,
                response_time=cloud_store_creation_time,
                response_result=protection_store,
            )
            logger.info(f"Successfully deployed cloud protection store.")
        else:
            logger.error(f"No psg found with name: {self.user.psg_name}")

    @task
    def delete_cloud_protection_store(self):
        """Delete cloud protection store simultaneously for number of users

        Raises:
            e: Error while deleting cloud store
        """
        if self.user.cloud_protection_store_id:
            meta_name = "Delete Cloud protection store"
            start_time = time.time()
            start_perf_counter = time.perf_counter()
            path = f"{Paths.protection_stores}/{self.user.cloud_protection_store_id}"
            logger.info(f"Delete protection policy with path: {path}")
            with self.client.delete(
                path,
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
            ) as response:
                try:
                    logger.info(
                        f"Delete protection store-Response code is {response.status_code} and response text is {response.text}"
                    )
                    if response.status_code == requests.codes.accepted:
                        task_id = response.headers.get("Location")
                        logging.info(f"delete protection store task id : {task_id.split('/')[-1]}")
                        self.verify_task_status(response, "delete cloud protection store")
                        cloud_store_deletion_time = (time.perf_counter() - start_perf_counter) * 1000
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=meta_name,
                            exception=None,
                            start_time=start_time,
                            response_time=cloud_store_deletion_time,
                            response_result=response.text,
                        )
                    else:
                        logger.error(
                            f"Protection store name:{self.user.protection_store_name}, ID::{self.user.cloud_protection_store_id}  not deleted. requested url::{response.request.url}"
                        )
                except Exception as e:
                    response.failure(
                        f"Error while deleting protection store name::{self.user.protection_store_name}, ID:: {self.user.cloud_protection_store_id}::{e}"
                    )
                    raise e
            self.user.cloud_protection_store_id = None
        else:
            logger.error(f"No protection store found with name::{self.user.cloud_protection_store_name}")

    @task
    def delete_local_protection_store(self):
        """Delete local protection store simultaneously for number of users

        Raises:
            e: error while deleting local protection store.
        """
        if self.user.local_protection_store_id:
            path = f"{Paths.protection_stores}/{self.user.local_protection_store_id}"
            logger.info(f"Delete protection policy with path: {path}")
            meta_name = "Delete Local protection store"
            start_time = time.time()
            start_perf_counter = time.perf_counter()
            with self.client.delete(
                path,
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
            ) as response:
                try:
                    logger.info(
                        f"Delete protection store-Response code is {response.status_code} and response text is {response.text}"
                    )
                    if response.status_code == requests.codes.accepted:
                        task_id = response.headers.get("Location")
                        logger.info(f"delete protection store task id : {task_id.split('/')[-1]}")
                        self.verify_task_status(response, "delete local protection store")
                        local_store_deletion_time = (time.perf_counter() - start_perf_counter) * 1000
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=meta_name,
                            exception=None,
                            start_time=start_time,
                            response_time=local_store_deletion_time,
                            response_result=response.text,
                        )
                    else:
                        logger.error(
                            f"Protectionstore name:{self.local_protection_store_name}, ID::{self.user.local_protection_store_id}  not deleted. requested url::{response.request.url}"
                        )
                except Exception as e:
                    response.failure(
                        f"Error while deleting protection store name::{self.user.protection_store_name}, ID:: {self.user.local_protection_store_id}::{e}"
                    )
                    raise e
            self.user.local_protection_store_id = None
        else:
            logger.error(f"No protection store found with name::{self.user.local_protection_store_name}")

    @task
    def delete_psg(self):
        """Deletes psg

        Raises:
            e: Error while deleting psg.
        """
        if self.user.psg_id:
            path = f"{Paths.protection_store_gateways}/{self.user.psg_id}"
            logger.info(f"Delete psg with path: {path}")
            meta_name = "Delete Protection store gateway"
            start_time = time.time()
            start_perf_counter = time.perf_counter()
            with self.client.delete(
                path,
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
            ) as response:
                try:
                    logger.info(
                        f"Delete psg -- Response code is {response.status_code} and response text is {response.text}"
                    )
                    if response.status_code == requests.codes.accepted:
                        task_id = response.headers.get("Location")
                        logger.info(f"Delete psg task id : {task_id.split('/')[-1]}")
                        self.verify_task_status(response, "delete psg")
                        psg_deletion_time = (time.perf_counter() - start_perf_counter) * 1000
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=meta_name,
                            exception=None,
                            start_time=start_time,
                            response_time=psg_deletion_time,
                            response_result=response.text,
                        )
                    else:
                        logger.error(
                            f"Psg name:{self.user.psg_name}, ID::{self.user.psg_id}  not deleted. requested url::{response.request.url}"
                        )
                except Exception as e:
                    response.failure(
                        f"Error while deleting psg name::{self.user.psg_name}, ID:: {self.user.psg_id}::{e}"
                    )
                    raise e
            self.user.psg_id = None
        else:
            logger.error(f"No psg found with name::{self.user.psg_name}")

    @task
    def on_completion(self):
        logger.info("All expected tasks done, raising StopUser interrupt")
        raise StopUser()

    def verify_task_status(self, response, task_name):
        """
        Verifies  task status whether it is completed

        Args:
            response (object): Response of the task

        Raises:
            Exception: Timeout error
            Exception: FAILED STATUS error
            Exception: Taskuri failure
        """
        task_uri = response.headers.get("Location")

        task_status = helpers.wait_for_task(task_uri=task_uri, timeout_minutes=30, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            logger.info(f"{task_name} task completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception(f"{task_name} task failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"{task_name} task failed with status'FAILED' error")
        else:
            raise Exception(f"{task_name} failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")
