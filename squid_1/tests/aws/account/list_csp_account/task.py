from locust import SequentialTaskSet, task
import tests.aws.config as config
import time
from requests import codes
from common import helpers


class CspAccountTask(SequentialTaskSet):

    @task
    def list_csp_account(self):
        with self.client.get(
            config.Paths.AWS_ACCOUNTS,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.user.proxies,
        ) as response:

            print(f"Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure("Failed to get csp account list, StatusCode: " + str(response.status_code))

            print(response.text)
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="sample",
                exception=None,
                start_time=time.time(),
                response_time=None,
                response_result=None,
            )

    @task
    def on_completion(self):
        self.interrupt()
