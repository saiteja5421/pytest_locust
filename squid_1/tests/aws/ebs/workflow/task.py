from locust import SequentialTaskSet, task
import locust_plugins
import tests.aws.config as config
from requests import codes
import random
from common import helpers
import logging
from tenacity import retry, wait_exponential, stop_after_attempt
from common.common import is_retry_needed


class EBSVolumes(SequentialTaskSet):

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def list_ebs_volumes(self):
        with self.client.get(
            config.Paths.EBS_VOLUMES,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            name="List csp volumes",
        ) as response:

            logging.info(f"List ebs volumes -> Response code is: {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get ebs volumes list, StatusCode: {str(response.status_code)} , Response text: {response.text}"
                )
            else:
                response_length = len(response.json()["items"])
                if response_length < 1:
                    logging.info(f"Ebs volumes list is empty")
                else:
                    self.csp_volumes = response.json()["items"]
            logging.info(f"List ebs volumes->Response is::{response.text}")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_csp_volume(self):
        # self.csp_volume['resourceUri'] will provide /api/v1/csp-volumes/{id}
        if self.csp_volumes:
            csp_volume = random.choice(self.csp_volumes)
            with self.client.get(
                f"{csp_volume['resourceUri']}",
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="Get csp volumes",
            ) as response:
                logging.info(f"Get csp volume detail -> response code is: {response.status_code}")
                if response.status_code != codes.ok:
                    response.failure(
                        f"Failed to get csp volume-{csp_volume} , StatusCode: {str(response.status_code)} , Response text: {response.text}"
                    )
                logging.info(f"Get csp volume details response->{response.text}")
        else:
            logging.error("No more ebs volume available to get csp volumes")

    @task
    def on_completion(self):
        self.interrupt()
