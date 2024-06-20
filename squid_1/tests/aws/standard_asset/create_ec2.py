"""
 Test case:
        Number of simultaneous requests to create and delete on demand Backups and hpe backup.
Steps: To create backup
    Create EC2 instances
    Create Protection policy and assign it to EC2 instance
    Each user will get one EC2 instance (At a time 5 users are doing this operation)
    The user will create backups for EC2 instance.

Steps: To delete backup
    Get the list of EC2 Instances. For ex: 10 Ec2 instance are there
    Each user will get one EC2 instance (At a time 5 users are doing this operation)
    The user will get all the backups in an EC2 instance. All the backup details will be stored
    Then delete the backups one at a time.

"""

# from http.server import HTTPServer
import uuid
from locust import between, events, task, SequentialTaskSet, HttpUser
from common import helpers
from common import assets
import logging
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts
from lib.platform.aws.ec2_manager import EC2Manager
from lib.platform.aws.aws_session import create_aws_session_manager

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        print("---- Start Load Test -----------")
        user_count = environment.parsed_options.num_users
        logging.debug(f"Number of users are {user_count}")
        config = helpers.read_config()
        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        account = Accounts(csp_account_name=config["testInput"]["Account"]["name"])
        global ec2_manager
        ec2_manager = EC2Manager(aws_session_manager)
        # global source_ec2_list
        # global source_tag
        # source_tag = assets.standard_asset_tag()
        # # source_tag = Tag(Key=f"{standard_asset_tag['key']}", Value=f"{standard_asset_tag['value']}")

        # logging.debug(f"Step 1 -> Create Ec2 instance per user")

        # zone = config["testbed"]["AWS"]["availabilityzone"]
        # image_id = config["testbed"]["AWS"]["imageid"]
        # global key_name
        # key_name = "Perf_Test_ec2_key" + str(uuid.uuid4())
        key_pairs = ec2_manager.get_all_ec2_key_pair()
        for key_pair in key_pairs:
            key_name = key_pair.name
            if key_name.startswith("TC57482271"):
                print(f"Deleting Keypair {key_name}")
                ec2_manager.delete_key_pair(key_name=key_name)
        # ec2_manager.create_ec2_key_pair(key_name=key_name)
        # source_ec2_list = ec2_manager.create_ec2_instance(
        #     key_name=key_name,
        #     image_id=image_id,
        #     availability_zone=zone,
        #     min_count=1,
        #     max_count=user_count,
        #     tags=[source_tag],
        # )

        # logging.info(f"Step 2-> Do inventory refresh  -------")
        # account.refresh_inventory()

        # ec2_instances = ec2_manager.get_running_ec2_instances_by_tag(tag=source_tag)
        # ec2_list = [ec2.id for ec2 in ec2_instances]
        # logging.info(f"ec2_list created :: {ec2_list}")

        # exit()
    except Exception as e:
        logging.error(f"[on_test_start] Error while creating prerequsites::{e}")
        logging.info(f"-----Delete Ec2 instance----")
        # for ec2_instance in source_ec2_list:
        #     ec2_manager.stop_and_terminate_ec2_instance(ec2_instance.id)
        # ec2_manager.delete_key_pair(key_name)
        exit()


class MyTasks(SequentialTaskSet):
    @task
    def dummy_task(self):
        print("EC2 instances are created")
        self.user.environment.reached_end = True
        self.user.environment.runner.quit()


class MyUser(HttpUser):
    wait_time = between(2, 3)
    tasks = [MyTasks]
