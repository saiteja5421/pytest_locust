from locust import HttpUser, between
from tests.ms365.protection.create_protection_group.task import ProtectionGroupTasks
from common import helpers

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [ProtectionGroupTasks]
