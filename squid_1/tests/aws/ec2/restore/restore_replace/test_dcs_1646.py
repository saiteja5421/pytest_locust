"""
 Test case:
        Number of simultaneous requests to restore EC2 instance from S3 backup by replacing source instance.
Steps:
    1.Create an Ec2 instance per user.
    2.Do inventory refresh
    3.Take a backup for each instance  
    4. Restore to multiple  EC2 instances from the backup simultaneously by replcing.
"""

from locust import HttpUser, between
from tests.aws.ec2.restore.restore_replace.task import RestoreTasks
from common import helpers
from tests.steps.aws_protection import accounts_steps
from lib.dscc.backup_recovery.aws_protection import backups
from lib.dscc.backup_recovery.aws_protection.assets import ec2

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class LoadUser(HttpUser):
    wait_time = between(60, 75)
    headers = helpers.gen_token()
    tasks = [RestoreTasks]

    # for each user start and stop will executed once

    def on_start(self):
        config = helpers.read_config()
        aws_config = config["testbed"]["AWS"]
        account_config = config["testInput"]["Account"]
        self.ec2_instance_id = "i-042b7705eccf7c8f1"
        self.create_ec2_take_backup(aws_config, account_config)

    def create_ec2_take_backup(self, aws_config, account_config):
        print(f"----Step 1-  Create an ec2 instance  -------")
        # self.ec2_instance_id = ec2_steps.create_ec2_instance(aws_config)
        print(self.ec2_instance_id)

        print(f"----Step 2-  Do inventory refresh  -------")
        account_obj = accounts_steps.refresh_account_inventory(account_config=account_config)
        self.account_id = account_obj.get_csp_account()["id"]

        print(f"----Step 3-  Take a backup for the instance created   -------")
        # TODO: Create protection job stuck at task. Once that issue is resolved need to test taking backup again
        backups.create_csp_machine_instance_backup(self.ec2_instance_id)
        print(f"Take backup manually")

        print(f"---Step 4: Fetch the backup created recently---")
        self.csp_machine = ec2.get_csp_machine(self.ec2_instance_id)
        self.csp_machine_id = self.csp_machine["id"]
        latest_backup = backups.get_recent_backup(self.csp_machine_id)
        self.backup_id = latest_backup["id"]

    def on_stop(self):
        print(f"---- User test completed -------")
