from locust import HttpUser, between
from tests.aws.account.onboard_template.task import OnBoardTask
from common import helpers
import tests.aws.config as config

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class LoadUser(HttpUser):
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    wait_time = between(2, 4)
    # host = "http://10.157.93.69:49218"
    tasks = [OnBoardTask]

    def on_start(self):
        """
        Get the list of csp account created and this list will be used to get onboarding template

        """
        with self.client.get(
            config.Paths.AWS_ACCOUNTS,
            headers=self.headers.authentication_header,
            proxies=self.proxies,
            catch_response=True,
        ) as response:
            print(response.status_code)
            resp_json = response.json()
            self.csp_account = resp_json["items"]
