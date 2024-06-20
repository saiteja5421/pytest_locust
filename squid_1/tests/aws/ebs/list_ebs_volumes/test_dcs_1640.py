from tests.aws.ebs.list_ebs_volumes.task import EBSVolumes
from locust import HttpUser, between
from common import helpers


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [EBSVolumes]
