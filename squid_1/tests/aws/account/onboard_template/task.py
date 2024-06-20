from locust import SequentialTaskSet, task
from requests import codes



class OnBoardTask(SequentialTaskSet):

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
    def get_onboard_template(self):
        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        with self.client.get(
            f"{self.csp_account['resourceUri']}/onboardingtemplate",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            print(response.status_code)
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to Get onboarding template for csp account {self.csp_account['name']}, StatusCode: {response.status_code}"
                )
            print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
