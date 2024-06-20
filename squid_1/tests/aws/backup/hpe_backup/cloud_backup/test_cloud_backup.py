"""
 Test case: 
      Task-1: Number of simultaneous requests to create HPE cloud backup on demand.
      Task-2: Number of simultaneous requests to delete HPE cloud backup on demand.
Steps:
    1.Create an Ec2 instance per user.
    2.Do inventory refresh
    3.Take on demand HPE cloud backup for each simultaneously. and delete the backups simultaneously which created at task1
"""

import uuid
from locust import HttpUser, between
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.aws.backup.hpe_backup.cloud_backup.task import CreateBackupTask
from common import helpers
from tests.steps.aws_protection import accounts_steps, protection_policy_steps
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
import logging

from lib.platform.aws.ec2_manager import EC2Manager


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    proj_id = None
    protection_policy_id = None
    csp_machine_id = None
    ec2_instance_id = None
    protection_job_id = None
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [CreateBackupTask]

    def on_start(self):
        logging.info(f"----Step 1----  Create an ec2 instance  -------")
        config = helpers.read_config()
        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        self.ec2_manager = EC2Manager(aws_session_manager)
        zone = config["testbed"]["AWS"]["availabilityzone"]
        image_id = config["testbed"]["AWS"]["imageid"]
        self.key_name = "Perf_Test_ec2_key" + str(uuid.uuid4())
        self.ec2_manager.create_ec2_key_pair(key_name=self.key_name)
        ec2_response = self.ec2_manager.create_ec2_instance(
            key_name=self.key_name, image_id=image_id, availability_zone=zone, min_count=1, max_count=1
        )
        self.ec2_instance_id = ec2_response[0].id

        logging.info(f"----Step 2-  Do inventory refresh  -------")
        accounts_steps.refresh_account_inventory(config["testInput"]["Account"])

        logging.info(f"----Step 3-  Create and Assign Protection Policy  -------")
        self.protection_job_id = protection_policy_steps.create_and_assign_protection_policy(self.ec2_instance_id)

    def on_stop(self):
        logging.info(f"---- User test completed -------")

        # Unprotect Job
        unprotect_job_response = protection_job.unprotect_job(self.protection_job_id)
        logging.info(unprotect_job_response)

        # Delete protection policy
        delete_protection_policy_response = protection_policy.delete_protection_policy(self.protection_policy_id)
        logging.info(delete_protection_policy_response)

        # Delete EC2 instance
        self.ec2_manager.stop_and_terminate_ec2_instance(self.ec2_instance_id)
        self.ec2_manager.delete_key_pair(self.key_name)
