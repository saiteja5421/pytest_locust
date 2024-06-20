from tests.ms365.protection.list_protection_policy.task import ProtectionJobTasks
from locust import HttpUser, between
from common import helpers

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [ProtectionJobTasks]
