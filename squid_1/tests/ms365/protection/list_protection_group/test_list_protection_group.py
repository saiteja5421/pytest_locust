from locust import HttpUser, between, events
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.ms365.protection.list_protection_group.task import ProtectionGroupTasks
from common import helpers
import logging

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


logger = logging.getLogger(__name__)


class LoadUser(HttpUser):
    between(30, 60)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [ProtectionGroupTasks]
