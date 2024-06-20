from locust import SequentialTaskSet, task
import requests
import urllib.parse


class TagKeyTasks(SequentialTaskSet):

    def on_start(self):
        """
        Per iteration use one csp account and fetch details
        when no more csp account is there to process stop execution
        """

        if self.user.csp_account:
            self.csp_account = self.user.csp_account.pop()
        else:
            print("No more csp account to process. So stop execution")
            self.user.environment.reached_end = True
            self.user.environment.runner.quit()

    @task
    def get_tag_keys(self):
        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        with self.client.get(
            f"{self.csp_account['resourceUri']}/tag-keys",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            print(response.status_code)
            # Getting tag value for each tag key
            if response.status_code == requests.codes.ok:
                tag_list = response.json()
                for key in tag_list:
                    # encoding key since it contains special characters
                    key = urllib.parse.quote(key)
                    with self.client.get(
                        f"{self.csp_account['resourceUri']}/tags?filter=key%20eq%20'{key}'",
                        headers=self.user.headers.authentication_header,
                        proxies=self.user.proxies,
                        catch_response=True,
                    ) as response:
                        print(response.status_code)
                        if response.status_code != requests.codes.ok:
                            response.failure("Failed to get tagkey values, StatusCode: " + str(response.status_code))
                            self.interrupt()
                        print(response.text)
            else:
                response.failure("Failed to get tag-keys , StatusCode: " + str(response.status_code))
                self.interrupt()

            print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
