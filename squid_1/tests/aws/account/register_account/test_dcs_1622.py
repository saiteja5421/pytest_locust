from locust import HttpUser, between
from tests.aws.account.register_account.task import RegisterAccountTask
from common import helpers

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    # host = "http://10.157.93.69:49218"

    tasks = [RegisterAccountTask]

    def on_start(self):
        """
        Get the list of test aws accounts and this list will be used to register account

        """
        config = helpers.read_config()
        self.aws_account_id_list = config["testInput"]["RegisterAccount"]["AWS"]["accountid"]
