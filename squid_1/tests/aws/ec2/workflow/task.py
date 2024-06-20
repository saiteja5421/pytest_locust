from locust import SequentialTaskSet, task
import tests.aws.config as config
from requests import codes
import random
from common import helpers
import logging
from tenacity import retry, wait_exponential, stop_after_attempt
from common.common import is_retry_needed

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

logger = logging.getLogger(__name__)


class Ec2Instances(SequentialTaskSet):
    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def list_running_ec2_instances(self):
        with self.client.get(
            f"{config.Paths.CSP_MACHINE_INSTANCES}?filter=state%20eq%20'OK'&limit=100",
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.user.proxies,
        ) as response:
            logger.info(f"List csp machine instances -> Response code is: {response.status_code}")
            if response.status_code != codes.ok:
                logger.error(f"List csp machine instances -> Response:{response.text}")
                response.failure(
                    f"Failed to get CSP instance list, StatusCode: {str(response.status_code)} , Response text: {response.text}"
                )
            else:
                self.user.csp_machine_instances = response.json()["items"]
                csp_machine_length = len(response.json()["items"])
                if not csp_machine_length:
                    logger.info(f"There are no ec2 instances available")
            logger.info(f"List csp machine instances -> Response:{response.text}")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_machine_instance(self):
        # self.inventory['resourceUri'] will provide /api/v1/csp-machine-instances/{id}
        if self.user.csp_machine_instances:
            self.csp_machine_instance = random.choice(self.user.csp_machine_instances)
        else:
            logger.error("No EC2 machine instance to process.")
            helpers.custom_locust_response(
                self.user.environment,
                name="get_machine_instance",
                exception="No EC2 machine instance to process. Please add some EC2 instance for this test",
            )
            return
        with self.client.get(
            f"{self.csp_machine_instance['resourceUri']}",
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.user.proxies,
            name="Get csp machine instances",
        ) as response:
            logger.info(f"Get EC2(CSP) machine instance details -> response code: {response.status_code}")
            if response.status_code != codes.ok:
                logger.error(response.text)
                response.failure(
                    f"Failed to get CSP machine instance , StatusCode:{ str(response.status_code)} , Response text: {response.text}"
                )

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def refresh_csp_machine_instances(self):
        # self.inventory['resourceUri'] will provide /api/v1/csp-machine-instances/{id
        try:
            with self.client.post(
                f"{self.csp_machine_instance['resourceUri']}/refresh",
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                catch_response=True,
                name="refresh csp machine instance",
            ) as response:
                try:
                    logger.info(f"Refresh csp machine instance response code -> {response.status_code}")
                    if response.status_code == codes.accepted:
                        response_data = response.json()
                        task_uri = response.headers["location"]
                        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
                        if task_status == helpers.TaskStatus.success:
                            logger.info(f"Refresh csp machine instance success")
                        elif task_status == helpers.TaskStatus.timeout:
                            raise Exception(f"Refresh csp machine instance failed with timeout error")
                        elif task_status == helpers.TaskStatus.failure:
                            raise Exception(f"Refresh csp machine instance failed with status'FAILED' error")
                        else:
                            raise Exception(f"Refresh csp machine instance failed with unknown error")
                    else:
                        logger.error(f"Refresh inventory response -> {response.text}")
                        response.failure(
                            f"Failed to refresh inventory, StatusCode: {str(response.status_code)} , Response text: {response.text}"
                        )
                except Exception as e:
                    response.failure(f"Exception during refresh csp instance {e}")
                    raise e
        except Exception as e:
            helpers.custom_locust_response(self.user.environment, name="refresh_csp_machine_instances", exception=e)

    @task
    def on_completion(self):
        self.interrupt()
