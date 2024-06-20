from locust import SequentialTaskSet, task
from requests import codes

from common import helpers


class ValidateCspAccountTask(SequentialTaskSet):

    def on_start(self):
        """Per iteration use one csp account and get onboard template
        when no more csp account is there to process stop execution
        """
        if self.user.csp_account:
            self.csp_account = self.user.csp_account.pop()
        else:
            print("No more csp account to process. So stop execution")
            self.user.environment.reached_end = True
            self.user.environment.runner.quit()

    @task
    def validate_csp_account(self):
        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        with self.client.post(
            f"{self.csp_account['resourceUri']}/validate",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            print(f"Validate csp account response is {response.status_code}")
            if response.status_code != codes.accepted:
                response.failure(
                    f"Failed to validate csp account {self.csp_account['name']}, StatusCode: {response.status_code}"
                )
            else:
                response_data = response.json()
                task_uri = response_data["taskUri"]
                task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
                if task_status == helpers.TaskStatus.success:
                    print("CSP account validated successfully")
                elif task_status == helpers.TaskStatus.timeout:
                    raise Exception("CSP account validation failed with timeout error")
                elif task_status == helpers.TaskStatus.failure:
                    raise Exception("CSP account validation failed with status'FAILED' error")
                else:
                    raise Exception("CSP account validation failed with unknown error")
            print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
