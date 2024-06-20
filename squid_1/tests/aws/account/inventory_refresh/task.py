import uuid
from locust import SequentialTaskSet, task
import logging
from common import helpers
import requests
import time
from lib.platform.aws.models.instance import Tag
from tests.aws.config import Paths
from tenacity import retry, wait_exponential, stop_after_attempt
from common.common import is_retry_needed

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

logger = logging.getLogger(__name__)


class RefreshInventoryTask(SequentialTaskSet):
    def on_start(self):
        """Per iteration use one csp account and fetch details"""
        self.csp_account = self.user.csp_account
        logger.info(f"----Step 1-  Create an ec2 instance  -------")
        source_tag = Tag(Key=f"perf_test_{helpers.generate_date()}", Value=f"Refresh_Inventory")

        zone = self.user.config["testbed"]["AWS"]["availabilityzone"]
        image_id = self.user.config["testbed"]["AWS"]["imageid"]
        self.key_name = "Perf_Test_ec2_key" + str(uuid.uuid4())
        self.user.ec2_manager.create_ec2_key_pair(key_name=self.key_name)

        ec2_instance = self.user.ec2_manager.create_ec2_instance(
            key_name=self.key_name,
            image_id=image_id,
            availability_zone=zone,
            min_count=1,
            max_count=1,
            tags=[source_tag],
        )
        self.ec2_instance_id = ec2_instance[0].id

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(5),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def refresh_account_inventory(self):
        """CSP account refresh

        Raises:
            Exception: No csp account
        """
        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        request_name = "Refresh inventory"
        if self.user.csp_account:
            with self.client.post(
                f"{self.csp_account['resourceUri']}/refresh",
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                catch_response=True,
                name=f"{Paths.AWS_ACCOUNTS}/<account_id>/refresh",
            ) as response:
                try:
                    logger.info(f"Refresh_account_inventory response code->{response.status_code}")
                    if response.status_code == requests.codes.accepted:
                        start_time = time.time()
                        start_perf_counter = time.perf_counter()
                        self._verify_refresh_inventory_status(response)
                        refresh_completion_time = (time.perf_counter() - start_perf_counter) * 1000
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=request_name,
                            exception=None,
                            start_time=start_time,
                            response_time=refresh_completion_time,
                            response_result=response.json(),
                        )
                except Exception as e:
                    exp = f"Exception occured while refresh inventory: {e}"
                    logger.error(exp)
                    helpers.custom_locust_response(environment=self.user.environment, name=request_name, exception=e)
                    response.failure(
                        f"Failed to Refresh inventory for csp account {self.csp_account['name']}, StatusCode: {response.status_code}, , Response text: {response.text}, error is {e}"
                    )
                    raise e
                finally:
                    logger.info(f"Refresh_account_inventory response->{response.text}")
        else:
            logger.error("No csp account for account refresh inventory.")
            raise Exception(f"No csp account for account refresh inventory.")

    def _verify_refresh_inventory_status(self, response):
        task_uri = response.headers["location"]
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            logger.info("Refresh inventory completed successfully")
        else:
            response.failure(
                f"Refresh inventory failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
            )

    @task
    def on_completion(self):
        self.interrupt()

    def on_stop(self):
        try:
            # teardown source ec2 which is used for refresh inventory
            self.user.ec2_manager.stop_and_terminate_ec2_instance(self.ec2_instance_id)
            self.user.ec2_manager.delete_key_pair(self.key_name)
        except Exception as e:
            logger.error(f"[on_stop] Error while deleting ec2 instance::{e}")
