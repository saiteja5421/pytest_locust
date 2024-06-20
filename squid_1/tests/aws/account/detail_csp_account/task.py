import random

from locust import SequentialTaskSet, task


class CspAccountDetailsTask(SequentialTaskSet):

    def on_start(self):
        """Per iteration use one csp account and fetch details
        when no more csp account is there to process stop execution
        """
        if self.user.csp_account:
            self.csp_account = random.choice(self.user.csp_account)
        else:
            print("No csp account to process. So stop execution")
            self.user.environment.reached_end = True
            self.user.environment.runner.quit()

    @task
    def get_csp_account_details(self):

        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        with self.client.get(
            f"{self.csp_account['resourceUri']}",
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.user.proxies,
        ) as response:
            print(response.status_code)
            if response.status_code != 200:
                response.failure("Failed to get csp account detail, StatusCode: " + str(response.status_code))

            print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
