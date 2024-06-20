import tests.aws.config as config
from requests import codes
from locust import SequentialTaskSet, task


class ProtectionPolicyTasks(SequentialTaskSet):
    """Get Protection Job will be done simultaneously"""

    @task
    def list_protection_policy(self):
        """List protection policies simulataneously"""
        print(self.user.host)
        # TODO: Test it with VM protection protection policy

        with self.client.get(
            config.Paths.PROTECTION_POLICIES,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
        ) as response:

            print(f"Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(f"Failed to get protection policy list, StatusCode: {str(response.status_code)}")
            else:
                print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
