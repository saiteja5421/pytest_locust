from locust import SequentialTaskSet, task
from requests import codes


# from common.helpers import gen_token


class RefreshTask(SequentialTaskSet):
    def on_start(self):
        """Per iteration use one inventory will be popped and that will be refreshed
        when no more inventory to process then stop execution
        """
        if self.user.csp_machine_instances:
            self.csp_machine_instance = self.user.csp_machine_instances.pop()
        else:
            print("No more inventory to process. So stop execution")
            self.user.environment.reached_end = True
            self.user.environment.runner.quit()

    @task
    def refresh_inventory(self):
        # self.inventory['resourceUri'] will provide /api/v1/csp-machine-instances/{id}
        with self.client.post(
            f"{self.csp_machine_instance['resourceUri']}/refresh",
            headers=self.user.headers.authentication_header,
            catch_response=True,
        ) as response:
            print(f"Refresh inventory response is {response.status_code}")
            if response.status_code != codes.accepted:
                response.failure("Failed to refresh inventory, StatusCode: " + str(response.status_code))
            else:
                print(response.text)

        # TODO: get the Task Uri
        # TODO: Verify task status

    @task
    def on_completion(self):
        self.interrupt()
