from locust import SequentialTaskSet, task
import tests.aws.config as config
from requests import codes


class EBSVolumes(SequentialTaskSet):

    @task
    def list_ebs_volumes(self):
        with self.client.get(
            config.Paths.EBS_VOLUMES,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
        ) as response:

            print(f"Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(f"Failed to get ebs volumes list, StatusCode: {str(response.status_code)}")
            print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
