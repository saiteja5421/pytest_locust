from locust import SequentialTaskSet, task
import tests.aws.config as config
from requests import codes


class ProtectionJobTasks(SequentialTaskSet):
    """Get Protection Job will be done simultaneously"""

    @task
    def list_protection_jobs(self):
        """list protection jobs simulataneously"""
        print(self.user.host)
        # Proxies had to be passed .it is not taking from environment variable
        with self.client.get(
            config.Paths.PROTECTION_JOBS,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
        ) as response:

            print(f"Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(f"Failed to get protection job list, StatusCode: {str(response.status_code)}")
            else:
                print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
