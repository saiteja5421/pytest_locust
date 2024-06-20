from locust import SequentialTaskSet, task
from requests import codes


class CSPVolume(SequentialTaskSet):

    def on_start(self):
        """Per iteration  one volume will be popped and that will be fetched
        when no more volume to process then stop execution
        """
        if self.user.csp_volumes:
            self.csp_volume = self.user.csp_volumes.pop()
        else:
            print("No more ebs volume to process. So stop execution")
            self.user.environment.reached_end = True
            self.user.environment.runner.quit()

    @task
    def get_csp_volume(self):
        # self.csp_volume['resourceUri'] will provide /api/v1/csp-volumes/{id}
        with self.client.get(
            f"{self.csp_volume['resourceUri']}",
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
        ) as response:
            print(f"Get csp volume detail -> response is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure("Failed to get csp volume , StatusCode: " + str(response.status_code))
            print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
