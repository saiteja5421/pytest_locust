"""
 Test case:
        DCS-1647: Number of simultaneous requests to restore EC2 instance from S3 backup by creating new EC2 instance.
        DCS-1646: Number of simultaneous requests to restore EC2 instance from S3 backup by replacing existing EC2 instance.
Steps:
    1. Create an Ec2 instance per user , Do inventory refresh and take a backup instance  
    2. Restore to multiple new EC2 instances from the backup simultaneously.
    3. Restore EC2 instances to existing from the backup simultaneously. (When we do this existing instance will be moved to stopped state but new instance will be created.)

"""

import uuid
from locust import HttpUser, between
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.aws.ec2.restore.restore_new.task import RestoreTasks
from lib.dscc.backup_recovery.aws_protection import backups
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts
from common import helpers
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from lib.dscc.backup_recovery.aws_protection.assets import ec2
from lib.platform.aws.ec2_manager import EC2Manager

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class LoadUser(HttpUser):
    wait_time = between(60, 75)
    headers = helpers.gen_token()
    tasks = [RestoreTasks]
    restored_ec2_list = []

    # for each user start and stop will executed once
    # ec2_instance_id = "i-0997641e6028bfaaa"
    # account_id = "3f477da7-2990-4737-828e-3365eb67b8f4"

    def on_start(self):
        config = helpers.read_config()
        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        self.account = Accounts(csp_account_name=config["testInput"]["Account"]["name"])
        # self.account.refresh_inventory()
        self.zone = config["testbed"]["AWS"]["availabilityzone"]
        self.image_id = config["testbed"]["AWS"]["imageid"]

        self.create_ec2_take_backup(aws_session_manager, self.account, self.zone, self.image_id)

    def create_ec2_take_backup(self, aws_session_manager, account: Accounts, zone, image_id):
        print(f"----Step 1-  Create an ec2 instance  -------")
        self.ec2_manager = EC2Manager(aws_session_manager)
        self.key_name = "Perf_Test_ec2_key" + str(uuid.uuid4())
        self.ec2_manager.create_ec2_key_pair(key_name=self.key_name)
        ec2_instance = self.ec2_manager.create_ec2_instance(
            key_name=self.key_name, image_id=image_id, availability_zone=zone, min_count=1, max_count=1
        )
        ec2_instance = self.ec2_manager.create_ec2_instance()
        self.source_ec2_instance_id = ec2_instance[0].id
        print(self.source_ec2_instance_id)

        print(f"----Step 2-  Do inventory refresh  -------")
        account.refresh_inventory()
        self.account_id = account.get_csp_account()["id"]

        print(f"----Step 3-  Take a backup for the instance created   -------")
        # TODO: Create protection job stuck at task. Once that issue is resolved need to test taking backup again
        self.protection_policy_id, self.protection_job_id = backups.create_csp_machine_instance_backup(
            self.source_ec2_instance_id
        )
        print(f"Take backup")

        print(f"---Step 4: Fetch the backup created recently---")
        self.csp_machine = ec2.get_csp_machine(self.source_ec2_instance_id)
        self.csp_machine_id = self.csp_machine["id"]
        latest_backup = backups.get_recent_backup(self.csp_machine_id)
        self.backup_id = latest_backup["id"]

    def on_stop(self):
        print(f"---- User test completed -------")
        # Unprotect Job
        unprotect_job_response = protection_job.unprotect_job(self.protection_job_id)
        print(unprotect_job_response)

        # Delete protection policy
        delete_protection_policy_response = protection_policy.delete_protection_policy(self.protection_policy_id)
        print(delete_protection_policy_response)

        for ec2_instance_name in self.restored_ec2_list:
            csp_machine = ec2.get_csp_machine_by_name(ec2_instance_name)
            self.ec2_manager.stop_and_terminate_ec2_instance(csp_machine["cspId"])

        self.ec2_manager.stop_and_terminate_ec2_instance(self.source_ec2_instance_id)
        self.ec2_manager.delete_key_pair(self.key_name)
        self.account.refresh_inventory()
