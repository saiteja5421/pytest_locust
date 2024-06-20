"""
 Test case:
        Number of simultaneous requests to delete Backups/HPE cloud backups.
Steps:
    Get the list of EC2 Instances. For ex: 10 Ec2 instance are there
    Each user will get one EC2 instance (At a time 5 users are doing this operation)
    The user will get all the backups in an EC2 instance. All the backup details will be stored
    Then delete the backups one at a time.
"""

from dataclasses import dataclass
from dataclasses_json import LetterCase, dataclass_json
from locust import events, HttpUser, between
import requests
from common import helpers
from tests.aws.backup.delete_backup.task import BackupTasks
import tests.aws.config as config


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CspInstance:
    id: str
    name: str
    account_id: str


# ec2_instances = []


def get_ec2_instance_list():
    """Get list of ec2 instances

    Args:
        base_url (str): base url which contains https://hostname:portnumber

    Returns:
        CspInstance [list]: ec2 instance list objects
    """
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    url = f"{helpers.get_locust_host()}{config.Paths.CSP_MACHINE_INSTANCES}"
    response = requests.request("GET", url, headers=headers.authentication_header, proxies=proxies)
    print(f"Response code is {response.status_code}")
    ec2_instance_list = None
    if response.status_code == requests.codes.ok:
        # print(response.text)
        data = response.json()
        if len(data["items"]) != 0:
            ec2_instance_list = [CspInstance(item["id"], item["name"], item["accountId"]) for item in data["items"]]
        else:
            print(f"No ec2 instances available.Response is::{response.text}")
    return ec2_instance_list


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    ec2_instance_list = None
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [BackupTasks]

    @events.test_start.add_listener
    def on_test_start(environment, **kwargs):
        host = environment.host
        print("---- Step 1- Get list of EC2 instances -----------")  # 1
        LoadUser.ec2_instance_list = get_ec2_instance_list()

    @events.test_stop.add_listener
    def on_test_stop(**kwargs):  # 7
        print("---- Stop Load Test -----------")

    # for each user start and stop will executed once

    def on_start(self):  # 2
        print(f"----Step 2-  Assign an ec2_instance to a user -------")
        if self.ec2_instance_list:

            self.ec2_instance = self.ec2_instance_list.pop()
        else:
            print("No more EC2 instance to process. So stop execution")
            self.environment.reached_end = True
            self.environment.runner.quit()

    def on_stop(self):  # 6
        print(f"---- User test completed -------")
