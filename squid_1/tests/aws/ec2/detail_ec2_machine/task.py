import random
from locust import SequentialTaskSet, task
from requests import codes

from tests.aws.config import Paths


class CSPMachineInstance(SequentialTaskSet):

    def on_start(self):
        """Per iteration use one machine intance will be popped and that will be fetched
        when no more instance to process then stop execution
        """
        if self.user.csp_machine_instances:
            self.csp_machine_instance = random.choice(self.user.csp_machine_instances)
        else:
            print("No EC2 machine instance to process. So stop execution")
            self.user.environment.reached_end = True
            self.user.environment.runner.quit()

    @task
    def get_machine_instance(self):
        # self.inventory['resourceUri'] will provide /api/v1/csp-machine-instances/{id}
        with self.client.get(
            f"{self.csp_machine_instance['resourceUri']}",
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.user.proxies,
            name=f"{Paths.EC2_INSTANCES}/instance_id",
        ) as response:
            print(f"Get EC2(CSP) machine instance detail -> response is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure("Failed to get EC2 machine instance , StatusCode: " + str(response.status_code))

            print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
