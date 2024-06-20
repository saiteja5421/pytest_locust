from locust import HttpUser, between
from tests.aws.ebs.detail_ebs_volume.task import CSPVolume
from common import helpers
import tests.aws.config as config

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [CSPVolume]

    def on_start(self):
        """
        Get the list of inventory

        """
        with self.client.get(
            config.Paths.EBS_VOLUMES,
            headers=self.headers.authentication_header,
            proxies=self.proxies,
            catch_response=True,
        ) as response:
            print(response.status_code)
            resp_json = response.json()
            if response.status_code == 404:
                print(f"Failed to load EBS volumes -> {response.status_code}")
                self.environment.runner.quit()
            self.csp_volumes = resp_json["items"]
