"""
Test steps
[PSR] Number of simultaneous request to get the list. of protection groups
"""

import time
from locust import SequentialTaskSet, task
from requests import codes
from common import helpers
import tests.ms365.config as config
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
    """Protection group task list is validated."""

    @task
    def list_protection_group(self):
        """Return the list of protection groups"""

        try:
            with self.client.get(
                config.MS365Paths.PROTECTION_GROUPS,
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="List protection group",
            ) as response:
                try:
                    logger.info(
                        f"List protection group-response code is: {response.status_code}"
                    )
                    if response.status_code == codes.ok:
                        resp_json = response.json()
                        protection_groups = resp_json["items"]
                        logger.debug(f"Protection groups {protection_groups}")
                    else:
                        logger.error(
                            f"List protection group-response is: {response.text}"
                        )
                        response.failure(
                            f"Unable to get list of protection_groups StatusCode: {str(response.status_code)} -> response: {response.text}"
                        )

                    logger.info(
                        f"List protection group response text is {response.text}"
                    )
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
    def on_completion(self):
        self.interrupt()
