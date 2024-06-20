import random
import string
from locust import SequentialTaskSet, task
import tests.aws.config as config
from lib.dscc.backup_recovery.protection.protection_policy import ExpireAfter, ProtectionType, ScheduleRecurrence
from requests import codes
from common import helpers
import logging

from tenacity import retry, wait_exponential, stop_after_attempt
from common.common import is_retry_needed
from common.enums.app_type import AppType

logger = logging.getLogger(__name__)


def random_choice() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choices(alphabet, k=8))


class ProtectionPolicyTasks(SequentialTaskSet):
    """Get Protection Job will be done simultaneously"""

    def on_start(self):
        self.protection_policy_id = None

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def create_protection_policy_cloudbackup(self):
        """Create protection policies simulataneously"""

        self.random_protection_policy_name = f"AAA_PerfTest_{random_choice()}"
        # In case of VMware protection, HPE Array Snapshot backup is must.
        # But in EC2/EBS backup ,there is no need for snapshot backup.
        # Tjhat's why Payload not contains HPE Array snapshot backup schedule.
        payload = {
            "description": "Protection Policy created by perftest",
            "name": f"{self.random_protection_policy_name}",
            "applicationType": AppType.aws.value,
            "protections": [
                {
                    "schedules": [
                        {
                            "scheduleId": 1,  # Just a unique id within the list of protections
                            "namePattern": {
                                "format": "Local_Backup_{DateFormat}"
                            },  # DateFormat is standard , no need to define it.
                            "schedule": {"recurrence": ScheduleRecurrence.DAILY.value, "repeatInterval": {"every": 2}},
                        }  # on is not required for Daily schedules
                    ],
                    "type": ProtectionType.BACKUP.value,
                },
                {
                    "schedules": [
                        {
                            "scheduleId": 2,
                            "namePattern": {"format": "Cloud_Backup_{DateFormat}"},
                            "expireAfter": {"unit": ExpireAfter.WEEKS.value, "value": 1},
                            "schedule": {
                                "recurrence": ScheduleRecurrence.WEEKLY.value,
                                "repeatInterval": {"every": 1, "on": [2]},
                            },
                        }  # on is mandatory for weekly and monthly schedules
                    ],
                    "type": ProtectionType.CLOUD_BACKUP.value,
                },
            ],
        }

        with self.client.post(
            config.Paths.PROTECTION_POLICIES,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            json=payload,
            name="Create protection policy",
        ) as response:
            try:
                logging.info(
                    f"Create protection policy:::::::::\nResponse code is----> {response.status_code},\n\nresponse text----> {response.text}"
                )
                if response.status_code == codes.ok:
                    self.protection_policy_id = response.json()["id"]
                else:
                    response.failure(
                        f":::::::::Failed to create protection policy:::::::::\nResponse code is----> {response.status_code},\n\nresponse text----> {response.text}, \n\npayload---->{payload}, \n\nrequested URL---->{response.request.url},\n\nresponse_content--->{response.content},\n\nraw_response---->{response.raw},\n\nmeta_data---->{response.request_meta}"
                    )

            except Exception as e:
                response.failure(
                    f"Error while creating protection policy: {e}, StatusCode: {str(response.status_code)} and response is {response.text}"
                )
                raise e

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def list_protection_policy(self):
        """List protection policies simulataneously"""

        with self.client.get(
            config.Paths.PROTECTION_POLICIES,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            name="List protection policies",
        ) as response:
            try:
                logger.info(f"List protection policy-Response code is {response.status_code}")
                if response.status_code != codes.ok:
                    logger.error(f"list_protection_policy response->{response.text}")
                    response.failure(
                        f"Failed to get protection policy list, StatusCode: {str(response.status_code)}, Response text: {response.text}"
                    )
            except Exception as e:
                response.failure(f"Error while list protection policies ::{e}")
                raise e

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    @task
    def list_protection_jobs(self):
        """list protection jobs simulataneously"""
        with self.client.get(
            config.Paths.PROTECTION_JOBS,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            name="List protection jobs",
        ) as response:
            try:
                logger.info(f"List protection jobs-Response code is {response.status_code}")
                if response.status_code != codes.ok:
                    logger.error(f"list_protection_jobs-response->{response.text}")
                    response.failure(
                        f"Failed to get protection job list, StatusCode: {str(response.status_code)},Response text: {response.text}"
                    )

                else:
                    jobs_length = response.json()["items"]
                    if not jobs_length:
                        logger.info(f"There are no protection jobs available")
            except Exception as e:
                response.failure(f"Error while list protection jobs ::{e}")
                raise e

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(1),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def delete_protection_policy(self):
        """list protection jobs simulataneously"""

        if self.protection_policy_id:
            path = f"{config.Paths.PROTECTION_POLICIES}/{self.protection_policy_id}"
            logger.info(f"Delete protection policy with path: {path}")
            with self.client.delete(
                path,
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name=f"Delete protection policy",
            ) as response:
                try:
                    logger.info(
                        f"Delete protection policy-Response code is {response.status_code} and response text is {response.text}"
                    )
                    if response.status_code == codes.no_content:
                        logger.info(
                            f"Protection policy name:{self.random_protection_policy_name}, ID::{self.protection_policy_id} deleted successfully"
                        )
                    else:
                        logger.error(
                            f"Protection policy name:{self.random_protection_policy_name}, ID::{self.protection_policy_id}  not deleted. requested url::{response.request.url}"
                        )
                except Exception as e:
                    response.failure(
                        f"Error while deleting protection policy name::{self.random_protection_policy_name}, ID:: {self.protection_policy_id}::{e}"
                    )
                    raise e
            self.protection_policy_id = None
        else:
            logger.error(f"No protection policy found with name::{self.protection_policy_id}")

    @task
    def on_completion(self):
        self.interrupt()

    def on_stop(self):
        logger.info("Delete remaining Protection Policy . . .")
        self.delete_protection_policy()
