from locust import SequentialTaskSet, task
import tests.aws.config as config
from requests import codes
from common import helpers


class BackupTasks(SequentialTaskSet):
    """
    Delete all the backups of an ec2_instance.
    In the on_start ,one of the backup will be picked.
    That backup will be deleted.
    Till all the backups are deleted it will continue

    """

    backup_to_be_deleted = None

    def on_start(self):
        # The user will get all the backups in an EC2 instance. All the backup details will be stored
        if self.user.ec2_instance.id:
            self.instance_id = self.user.ec2_instance.id
            with self.client.get(
                f"{config.Paths.CSP_MACHINE_INSTANCE_BACKUPS}?filter=assetInfo/id eq '{self.user.ec2_instance.id}'",
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                catch_response=True,
            ) as response:
                print(f"Get backups-Response code is {response.status_code}")
                response_data = response.json()
                print(f"backup list", response_data)
                if len(response_data["items"]) != 0:
                    print("Pick the first backup to be deleted", response_data["items"])
                    self.backup_to_be_deleted = response_data["items"][0]["id"]
                else:
                    print("No backups available")
                    self.user.environment.reached_end = True
                    self.user.environment.runner.quit()
        else:
            print("No ec2 instance available")

    @task
    def delete_hpe_backup(self):
        """Delete the hpe backup"""
        if self.backup_to_be_deleted != None:
            with self.client.delete(
                f"{config.Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{self.backup_to_be_deleted}",
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                catch_response=True,
            ) as response:
                print(f"Delete hpe backup-Response code is {response.status_code}")
                if response.status_code != codes.accepted:
                    response.failure(f"Failed to to delete Backup, StatusCode: {str(response.status_code)}")
                self.verify_backup_task_status(response)
        else:
            print(f"No backups available with the insatnce id-{self.user.ec2_instance.id}")

    def verify_backup_task_status(self, response):
        """
        Verifies delete backup task status whether it is completed

        Args:
            response (object): Response of the create local backup

        Raises:
            Exception: Timeout error
            Exception: FAILED STATUS error
            Exception: Taskuri failure
        """
        task_uri = response.json()["taskUri"]
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
        if task_status == helpers.TaskStatus.success:
            print("Local Backup completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Local Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"Local Backup failed with status'FAILED' error")
        else:
            raise Exception(f"Delete  backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")

    @task
    def on_completion(self):
        self.interrupt()
