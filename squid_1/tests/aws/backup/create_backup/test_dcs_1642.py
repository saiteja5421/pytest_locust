"""
 Test case:
        Number of simultaneous requests to create on demand Backups.
Steps:
    Create EC2 instances
    Create Protection policy and assign it to EC2 instance
    Each user will get one EC2 instance (At a time 5 users are doing this operation)
    The user will create backups for EC2 instance.
"""

import uuid
from locust import HttpUser, between
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.aws.backup.create_backup.task import CreateLocalBackupTasks
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from lib.dscc.backup_recovery.aws_protection.assets import ec2
from common import helpers
from tests.steps.aws_protection import accounts_steps
from lib.dscc.backup_recovery.aws_protection import backups
from lib.platform.aws.ec2_manager import EC2Manager


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    protection_job_id = None
    protection_policy_id = None
    csp_machine_id = None
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [CreateLocalBackupTasks]

    # for each user start and stop will executed once

    def on_start(self):
        print(f"----Step 1----  Create an ec2 instance  -------")
        config = helpers.read_config()
        self.aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        self.ec2_manager = EC2Manager(self.aws_session_manager)
        zone = config["testbed"]["AWS"]["availabilityzone"]
        image_id = config["testbed"]["AWS"]["imageid"]
        self.key_name = "Perf_Test_ec2_key" + str(uuid.uuid4())
        self.ec2_manager.create_ec2_key_pair(key_name=self.key_name)
        ec2_instance = self.ec2_manager.create_ec2_instance(
            key_name=self.key_name,
            image_id=image_id,
            availability_zone=zone,
            min_count=1,
            max_count=1,
        )
        self.ec2_instance_id = ec2_instance[0].id
        print(f"To create back up- ec2 instance ID:{self.ec2_instance_id}")
        print(self.ec2_instance_id)

        print(f"----Step 2-  Do inventory refresh  -------")
        accounts_steps.refresh_account_inventory(config["testInput"]["Account"])

        print(f"----Step 3-  Create and Assign Protection Policy  -------")
        self.protection_job_id = self.create_and_assign_protection_policy()

    def create_and_assign_protection_policy(self):
        """
        Creates protection job and assigns protection policy to that job

        Returns:
            str : protection job id
        """
        csp_machine_dict = ec2.get_csp_machine(self.ec2_instance_id)
        self.csp_machine_id = csp_machine_dict["id"]
        response = protection_policy.create_protection_policy(backup_only=True)

        protection_policy_id, protection_policy_name, protections_id = (
            response["id"],
            response["name"],
            response["protections"][0]["id"],
        )
        self.protection_policy_id = protection_policy_id

        protection_job.create_protection_job(
            asset_id=self.csp_machine_id, protections_id_one=protections_id, protection_policy_id=protection_policy_id
        )
        protection_job_id = protection_job.find_protection_job_id(protection_policy_name, self.csp_machine_id)
        return protection_job_id

    def on_stop(self):
        print(f"---- User test completed -------")
        # Unprotect Job
        unprotect_job_response = protection_job.unprotect_job(self.protection_job_id)
        print(unprotect_job_response)

        # Delete protection policy
        delete_protection_policy_response = protection_policy.delete_protection_policy(self.protection_policy_id)
        print(delete_protection_policy_response)

        # Delete EC2 backups
        backup_response_data = backups.get_all_csp_machine_instance_backups(self.csp_machine_id)
        for backup in backup_response_data["items"]:
            backup_id = backup["id]"]
            backups.delete_csp_machine_instance_backup(self.csp_machine_id, backup_id)

        # Delete EC2 instance
        self.ec2_manager.stop_and_terminate_ec2_instance(self.ec2_instance_id)
        self.ec2_manager.delete_key_pair(self.key_name)
