"""
 Test case:`    1
       Number of simultaneous requests to create HPE cloud backup on demand.
Steps:
    1.Create an Ec2 instance per user.
    2.Do inventory refresh
    3.Take on demand HPE cloud backup for each simultaneously. 
"""

import logging
import uuid
from locust import HttpUser, between
from tests.aws.backup.create_hpe_cloud_backup.task import CreateBackupTask
from common import helpers
from tests.steps.aws_protection import accounts_steps, protection_policy_steps
from lib.platform.aws.aws_session import create_aws_session_manager
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from lib.dscc.backup_recovery.aws_protection import backups
from lib.platform.aws.ec2_manager import EC2Manager

logger = logging.getLogger(__name__)


class LoadUser(HttpUser):
    wait_time = between(60, 120)
    proj_id = None
    protection_policy_id = None
    csp_machine_id = None
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [CreateBackupTask]

    def on_start(self):
        logger.info(f"----Step 1----  Create an ec2 instance  -------")
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

        logger.info(f"----Step 2-  Do inventory refresh  -------")
        accounts_steps.refresh_account_inventory(config["testInput"]["Account"])

        logger.info(f"----Step 3-  Create and Assign Protection Policy  -------")
        (
            self.protection_job_id,
            self.csp_machine_id,
            self.protection_policy_id,
        ) = protection_policy_steps.create_and_assign_protection_policy(
            ec2_instance_id=self.ec2_instance_id, backup_only=False
        )

    def on_stop(self):
        logger.info(f"---- User test completed -------")
        unprotect_job_response_local = protection_job.unprotect_job(self.protection_job_id)
        logger.info(unprotect_job_response_local)

        # Delete protection policy
        delete_protection_policy_response = protection_policy.delete_protection_policy(self.protection_policy_id)
        logger.info(delete_protection_policy_response)

        # Delete EC2 backups
        backup_response_data = backups.get_all_csp_machine_instance_backups(self.csp_machine_id)
        for backup in backup_response_data["items"]:
            backup_id = backup["id]"]
            backups.delete_csp_machine_instance_backup(self.csp_machine_id, backup_id)

        # Delete EC2 instance
        self.ec2_manager.stop_and_terminate_ec2_instance(self.ec2_instance_id)
        self.ec2_manager.delete_key_pair(self.key_name)
