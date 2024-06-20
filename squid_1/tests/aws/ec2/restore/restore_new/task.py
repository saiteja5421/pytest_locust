import json
from locust import SequentialTaskSet, task

from requests import codes
from common import helpers
from tests.aws.config import Paths
from lib.dscc.backup_recovery.aws_protection import backups


class RestoreTasks(SequentialTaskSet):
    """
    Restore ec2_instance from s3 backup by creating new instance.
    That ec2 instance restore will be continue.
    """

    proxies = helpers.set_proxy()
    backup_id = None

    @task
    def restore_ec2_instance_new(self):
        """Restore csp machine instance from the backup simultaneously by creating"""
        print("restore to new instance")
        payload = self._restore_new_payload()
        print(f"Path is {self.client.base_url}{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.user.backup_id}/restore")
        with self.client.post(
            f"{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.user.backup_id}/restore",
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            print(f"Response code is {response.status_code}")
            if response.status_code == codes.accepted:
                print(response.text)
                self._verify_restore_task_status(response)
                # Record the restored instance list so that it can be cleaned up at the end
                self.user.restored_ec2_list.append(payload["targetMachineInstanceInfo"]["name"])
            else:
                response.failure(
                    f"Failed to to restore , StatusCode: {str(response.status_code)} and response is {response.text}"
                )

    def _restore_new_payload(self):
        """restore to new ec2 instance payload will be created

        Returns:
            dict: payload
        """
        csp_machine = self.user.csp_machine
        cspInfo = csp_machine["cspInfo"]
        nwInfo = csp_machine["cspInfo"]["networkInfo"]
        security_group_id_list = [sgid["cspId"] for sgid in nwInfo["securityGroups"]]
        payload = {
            "backupId": self.user.backup_id,
            "operationType": "CREATE",
            "originalMachineInstanceInfo": {"terminateOriginal": False},
            "targetMachineInstanceInfo": {
                "accountId": self.user.account_id,
                "cspInfo": {
                    "availabilityZone": cspInfo["availabilityZone"],
                    "instanceType": cspInfo["instanceType"],
                    "keyPairName": cspInfo["keyPairName"],
                    "cspRegion": cspInfo["cspRegion"],
                    "cspTags": [{"key": "Name", "value": "Perf-Autotest"}],
                    "securityGroupIds": security_group_id_list,
                    "subnetCspId": cspInfo["networkInfo"]["subnetInfo"]["id"],
                },
                "name": f"{csp_machine['name']}-new-restore{helpers.generate_date()}",
            },
        }

        return payload

    def _verify_restore_task_status(self, restore_response):
        """verify restore task status in atlas

        Args:
            restore_response (dict): restore post call response
        """
        task_uri = restore_response.json()["taskUri"]
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.headers)
        if task_status == helpers.TaskStatus.success:
            print("Local Backup restored successfully")
        else:
            restore_response.failure(
                f"Restore from local backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
            )

    @task
    def on_completion(self):
        self.interrupt()
