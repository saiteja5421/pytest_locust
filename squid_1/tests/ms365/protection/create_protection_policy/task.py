import random
import string
import logging

from locust import SequentialTaskSet, task
import tests.aws.config as config
from requests import codes
from lib.dscc.backup_recovery.protection.protection_policy import (
    ProtectionType,
    ScheduleRecurrence,
    ExpireAfter,
)
from common.enums.app_type import AppType
from tenacity import retry, wait_exponential, stop_after_attempt
from common.common import is_retry_needed
from common import helpers

logger = logging.getLogger(__name__)


def random_choice() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choices(alphabet, k=8))


class ProtectionPolicyTasks(SequentialTaskSet):
    """Get Protection policy will be done simultaneously"""

    @task
    def create_protection_policy_cloudbackup(self):
        """Create protection policies simulataneously"""
        logger.info(self.user.host)
        self.random_protection_policy_name = f"AAA_PerfTest_{random_choice()}"
        payload = {
            "applicationType": AppType.ms365.value,
            "description": "Protection Policy created by perftest",
            "name": f"{self.random_protection_policy_name}",
            "protections": [
                {
                    "schedules": [
                        {
                            "scheduleId": 2,
                            "namePattern": {"format": "Cloud_Backup_{DateFormat}"},
                            "expireAfter": {
                                "unit": ExpireAfter.WEEKS.value,
                                "value": 1,
                            },
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
            logger.info(f"Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to create protection policy, StatusCode: {str(response.text)}"
                )
            else:
                self.protection_policy_id = response.json()["id"]

            logger.info(response.text)

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(1),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def delete_protection_policy(
        self,
    ):
        """delete protection policies simulataneously"""

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
            logger.error(
                f"No protection policy found with name::{self.protection_policy_id}"
            )

    @task
    def on_completion(self):
        self.interrupt()
