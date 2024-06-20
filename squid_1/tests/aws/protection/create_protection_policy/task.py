import random
import string

from locust import SequentialTaskSet, task
import tests.aws.config as config
from requests import codes
from lib.dscc.backup_recovery.protection.protection_policy import ProtectionType, ScheduleRecurrence, ExpireAfter
from common.enums.app_type import AppType


def random_choice() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choices(alphabet, k=8))


class ProtectionPolicyTasks(SequentialTaskSet):
    """Get Protection Job will be done simultaneously"""

    @task
    def create_protection_policy_cloudbackup(self):
        """Create protection policies simulataneously"""
        print(self.user.host)
        random_protection_policy_name = f"AAA_PerfTest_{random_choice()}"
        # In case of VMware protection, HPE Array Snapshot backup is must.
        # But in EC2/EBS backup, there is no need for snapshot backup.
        # That's why Payload not contains HPE Array snapshot backup schedule.
        payload = {
            "description": "Protection Policy created by perftest",
            "name": f"{random_protection_policy_name}",
            "protections": [
                {
                    "schedules": [
                        {
                            "id": 1,  # Just a unique id within the list of protections
                            "namePattern": {
                                "format": "Local_Backup_{DateFormat}"
                            },  # DateFormat is standard , no need to define it.
                            "schedule": {
                                "recurrence": ScheduleRecurrence.DAILY.value,
                                "repeatInterval": {"every": 2},
                            },
                        }  # on is not required for Daily schedules
                    ],
                    "type": ProtectionType.BACKUP.value,
                    "applicationType": AppType.aws.value,
                },
                {
                    "schedules": [
                        {
                            "id": 2,
                            "namePattern": {"format": "Cloud_Backup_{DateFormat}"},
                            "expireAfter": {"unit": ExpireAfter.WEEKS.value, "value": 1},
                            "schedule": {
                                "recurrence": ScheduleRecurrence.WEEKLY.value,
                                "repeatInterval": {"every": 1, "on": [2]},
                            },
                        }  # on is mandatory for weekly and monthly schedules
                    ],
                    "type": ProtectionType.CLOUD_BACKUP.value,
                    "applicationType": AppType.aws.value,
                },
            ],
        }

        # TODO: Test the payload by printing it
        print(f"Payload is -> {payload}")

        # TODO: Test it with protection protection policy with Ec2 resource

        with self.client.post(
            config.Paths.PROTECTION_POLICIES,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            json=payload,
        ) as response:
            print(f"Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(f"Failed to get protection job list, StatusCode: {str(response.text)}")

            print(response.text)

    @task
    def on_completion(self):
        self.interrupt()
