from tests.aws.account.list_csp_account.task import CspAccountTask
from locust import HttpUser, between
from common import helpers

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class LoadUser(HttpUser):
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    wait_time = between(2, 4)
    tasks = [CspAccountTask]
