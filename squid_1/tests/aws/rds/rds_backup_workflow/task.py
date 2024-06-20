import json
import time
import uuid
import logging
from requests import codes
from locust import SequentialTaskSet, tag, task
from tenacity import retry, wait_exponential, stop_after_attempt
from common.enums.asset_info_types import AssetType
from common.enums.asset_type_uri_prefix import AssetTypeURIPrefix
from common.enums.aws_availability_zone import AWSAvailabilityZone
from lib.dscc.backup_recovery.aws_protection.backup_restore.models.csp_rds_instance_backup import (
    CSPRDSInstanceBackup,
    CSPRDSInstanceBackupList,
)
from lib.dscc.backup_recovery.aws_protection.rds.models.csp_rds_instance import (
    CSPRDSInstance,
    CSPRDSInstanceList,
)
from lib.platform.aws.ec2_manager import EC2Manager
from lib.platform.aws.rds_manager import RDSManager
from tests.aws.config import Paths, RDSPaths
from common import helpers
from lib.dscc.backup_recovery.aws_protection.rds import rds_helper
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.steps.aws_protection import accounts_steps


# Below import is needed for locust-grafana integration, do not remove
import locust_plugins
from locust.exception import StopUser

logger = logging.getLogger(__name__)

v1_beta_1_api, _ = helpers.get_v1_beta_api_prefix()

# DB_NAME: str = "west4345"
# DB_ID: str = "west4345"
# RDS_ID: str = DB_ID
TRIGGER_BACKUP_DISPLAY_NAME: str = "Initiated RDS Instance backup[{}]"
DB_IDENTIFIERS: list[str] = []


class RDSBackupTasks(SequentialTaskSet):
    """RDS backup and restore jobs will be done like create backup, list backups and details about backups and restore instance simultaneously"""

    def create_rds_instance(self):
        # global RDS_ID

        config = helpers.read_config()
        aws_session = create_aws_session_manager(config["testbed"]["AWS"])
        db_name = "west4345" + str(uuid.uuid4()).replace("-", "")
        db_id = "west4345-" + str(uuid.uuid4())
        RDS_ID: str = db_id

        ec2_manager = EC2Manager(aws_session=aws_session)
        availability_zone = ec2_manager.get_availability_zone()
        logger.info(f"Availability Zone = {availability_zone}")

        logger.info(f"Created RDS Instance {db_id}")
        rds_manager = RDSManager(aws_session=aws_session)
        master_user_name, master_user_password = helpers.get_rds_db_master_username_password()
        rds_db = rds_manager.create_db_instance(
            db_name=db_name,
            db_instance_identifier=db_id,
            allocated_storage=10,
            availability_zone=AWSAvailabilityZone(availability_zone),
            master_username=master_user_name,
            master_user_password=master_user_password,
            max_allocated_storage=20,
        )
        logger.info(f"Created RDS instance is {rds_db}")
        DB_IDENTIFIERS.append(RDS_ID)

        RDS_ID = rds_db["DBInstanceIdentifier"]
        return RDS_ID

    def delete_rds_instance(self, db_identifier: str):
        config = helpers.read_config()
        aws_session = create_aws_session_manager(config["testbed"]["AWS"])

        rds_manager = RDSManager(aws_session=aws_session)
        rds_manager.delete_db_instance_by_id(db_instance_identifier=db_identifier)

    def refresh_account_inventory(self):
        config = helpers.read_config()
        accounts_steps.refresh_account_inventory(config["testInput"]["Account"], account_type="RDS")

    def create_and_assign_protection_policy_to_rds_instance(
        self,
        csp_rds_instance: CSPRDSInstance,
    ):
        response = protection_policy.create_protection_policy(
            backup_only=True,
        )

        protection_policy_id, protection_policy_name, protections_id = (
            response["id"],
            response["name"],
            response["protections"][0]["id"],
        )

        logger.info(f"Protection Policy ID = {protection_policy_id}, name {protection_policy_name}")

        logging.info(f"Creating protection job for RDS instance {csp_rds_instance.id}")
        protection_job.create_protection_job(
            asset_id=csp_rds_instance.id,
            protections_id_one=protections_id,
            protection_policy_id=protection_policy_id,
            asset_type=AssetType.CSP_RDS_DATABASE_INSTANCE,
        )

        protection_job_id = protection_job.get_protection_job_id(csp_rds_instance.id)
        logging.info(f"Protection Policy {protection_policy_id} is assigned to RDS {csp_rds_instance.id}")
        return protection_job_id, protection_policy_id

    def on_start(self):
        self.csp_rds_instances: CSPRDSInstanceList = None
        self.csp_rds_instance: CSPRDSInstance = None
        self.csp_rds_backups: CSPRDSInstanceBackupList = None
        self.csp_rds_backup: CSPRDSInstanceBackup = None
        self.protection_job_id = None
        self.protection_policy_id = None

        config = helpers.read_config()
        region: str = config["testbed"]["AWS"]["region"]

        self.rds_id = self.create_rds_instance()
        DB_IDENTIFIERS.append(self.rds_id)
        self.refresh_account_inventory()
        self.csp_rds_instances = rds_helper.get_csp_rds_instances()
        self.csp_rds_instance = rds_helper.get_csp_rds_instance_using_db_identifier(
            db_identifier=self.rds_id,
            region=region,
        )
        self.protection_job_id, self.protection_policy_id = self.create_and_assign_protection_policy_to_rds_instance(
            csp_rds_instance=self.csp_rds_instance,
        )

    @tag("rds_backup_and_restore")
    @task
    def create_rds_local_backup(self):
        """Create RDS Local backup on demand"""

        url = f"{Paths.PROTECTION_JOBS}/{self.protection_job_id}/run"
        payload = {"scheduleIds": [1]}

        meta_name = "rds local backup"
        start_time = time.time()
        start_perf_counter = time.perf_counter()

        with self.client.post(
            url,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name="Create RDS Local Backup",
        ) as response:
            logger.info(f"RDS backup response code is {response.status_code}, response is {response.text}")
            if response.status_code == codes.accepted:
                try:
                    # task_uri = response.json()["taskUri"]
                    task_uri = helpers.get_task_uri_from_header(response=response)
                    self.verify_task_status(task_uri, is_backup_task=True)

                    logger.info(f"Local Native Backup is created successfully for RDS {self.csp_rds_instance.id}")

                    backup_creation_time = (time.perf_counter() - start_perf_counter) * 1000
                    helpers.custom_locust_response(
                        environment=self.user.environment,
                        name=meta_name,
                        exception=None,
                        start_time=start_time,
                        response_time=backup_creation_time,
                        response_result=task_uri,
                    )

                except Exception as e:
                    logger.error(f"Error is {e}")
                    helpers.custom_locust_response(environment=self.user.environment, name=meta_name, exception=e)
            else:
                response.failure(
                    f"Failed to to create local Backup, StatusCode: {str(response.status_code)} ,Response text: {response.text}. Partial url {Paths.PROTECTION_JOBS}/{self.protection_job_id}/run"
                )

            logger.info("Test => [create_on_demand_rds_local_backup] -> PASS")

    @tag("rds_backup_and_restore")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def list_csp_rds_backups(self):
        """List rds backup's simultaneously"""

        # /backup-recovery/v1beta1/csp-rds-instances/{instanceId}/backups
        if self.csp_rds_instance:
            with self.client.get(
                f"{RDSPaths.CSP_RDS_INSTANCES_BACKUPS}",
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="List CSP RDS Backups",
            ) as response:
                logger.info(f"List CSP RDS Backups-> Response code is {response.status_code}")
                logger.info(f"List CSP RDS Backups-> Response text{response.text}")
                if response.status_code == codes.ok:
                    self.csp_rds_backups: CSPRDSInstanceBackupList = CSPRDSInstanceBackupList.from_json(response.text)
                    if self.csp_rds_backups.total == 0:
                        logger.warning("CSP RDS Backup list is empty")
                    else:
                        self.csp_rds_backup = self.csp_rds_backups.items[-1]
                        logger.info(f"Backup is {self.csp_rds_backup.id}")
                else:
                    response.failure(
                        f"Failed to get RDS backup list->Response code is {response.status_code}\n Response text {response.text}"
                    )
        else:
            raise Exception("No CSP RDS instance backups available")

    @tag("rds_backup_and_restore")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def detail_rds_backups(self):
        """Details rds backup simultaneously"""

        # /backup-recovery/v1beta1/csp-rds-instances/{instanceId}/backups/{id}
        if self.csp_rds_backup:
            with self.client.get(
                f"{RDSPaths.CSP_RDS_INSTANCES_BACKUPS}/{self.csp_rds_backup.id}",
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="GET RDS Backup Details",
            ) as response:
                logger.info(f"RDS Backup {self.csp_rds_backup.id} in details-> Response code is {response.status_code}")
                logger.info(f"RDS Backup {self.csp_rds_backup.id} in details-> Response text is {response.text}")

                if response.status_code == codes.ok:
                    self.csp_rds_backup = CSPRDSInstanceBackup.from_json(response.text)
                else:
                    response.failure(
                        f"Failed to get RDS Backup in details->Response code is :{response.status_code}\n Response text {response.text}"
                    )
        else:
            raise Exception("No CSP RDS backups available")

    @tag("rds_backup_and_restore")
    @task
    def restore_rds_instance(self):
        """Restore rds instance from the backup simultaneously"""
        # /backup-recovery/v1beta1/csp-rds-instances/{instanceId}/restore
        logger.info("Task [restore_rds_instance] -> START")

        db_identifier: str = "restore-rds" + str(uuid.uuid4()).split("-")[0]
        payload = {"databaseIdentifier": db_identifier}
        request_name = "Restore RDS Instance"
        with self.client.post(
            f"{RDSPaths.CSP_RDS_INSTANCES_BACKUPS}/{self.csp_rds_backup.id}/restore",
            data=json.dumps(payload, default=str),
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.user.proxies,
            name=request_name,
        ) as response:
            try:
                logger.info(
                    f"restore rds instance->Response code is::: {response.status_code} and Response text:::{response.text}"
                )
                if response.status_code == codes.accepted:
                    start_time = time.time()
                    start_perf_counter = time.perf_counter()
                    self.verify_task_status(response.headers["location"])

                    DB_IDENTIFIERS.append(db_identifier)

                    restore_time = (time.perf_counter() - start_perf_counter) * 1000
                    try:
                        helpers.custom_locust_response(
                            environment=self.user.environment,
                            name=request_name,
                            exception=None,
                            start_time=start_time,
                            response_time=restore_time,
                            response_result=response.text,
                        )

                    except Exception as e:
                        helpers.custom_locust_response(
                            environment=self.user.environment, name=request_name, exception=e
                        )

                else:
                    response.failure(
                        f"[restore_rds_instance] [RDS- {self.csp_rds_instance.id}] - Failed to restore , StatusCode: {str(response.status_code)} and response is {response.text}"
                    )
            except Exception as e:
                response.failure(f"Error occured while restore to rds instance: {e}")
            finally:
                logger.info(f"restore rds instance:{response.text}")

    @tag("rds_backup_and_restore")
    @task
    def delete_rds_local_backup(self):
        """Delete rds local backup on demand"""
        # /backup-recovery/v1beta1/csp-rds-instances/{instanceId}/backups/{id}
        if self.csp_rds_backup:
            with self.client.delete(
                f"{RDSPaths.CSP_RDS_INSTANCES_BACKUPS}/{self.csp_rds_backup.id}",
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                catch_response=True,
                name="Delete RDS Local Backup ",
            ) as response:
                logger.info(f"Delete rds local backup-Response code is {response.status_code}")
                if response.status_code == codes.accepted:
                    self.verify_task_status(response.headers["location"])
                else:
                    response.failure(
                        f"Failed to to delete rds local Backup, StatusCode: {str(response.status_code)},Response text: {response.text} . Partial url {self.csp_rds_instance.id}/backups/{self.backup_id}"
                    )
                logger.info(f"Delete rds local backup- Response text::{response.text}")
                logger.info("Task [delete_rds_local_backup] -> PASS")

    def verify_task_status(self, task_uri, is_backup_task: bool = False):
        """
        Verifies backup/restore task status whether it is completed

        Args:
            task_uri : uri of the backup/restore task

        Raises:
            Exception: Timeout error
            Exception: FAILED STATUS error
            Exception: Taskuri failure
        """

        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)

        if is_backup_task:
            trigger_task_id = (
                helpers.get_tasks_by_name_and_resource(
                    task_name=TRIGGER_BACKUP_DISPLAY_NAME.format(self.csp_rds_instance.id),
                    resource_uri=f"{AssetTypeURIPrefix.RDS_INSTANCES_RESOURCE_URI_PREFIX_HYBRID_CLOUD.value}{self.csp_rds_instance.id}",
                )
                .items[0]
                .id
            )
            logger.info(f"Backup Trigger Task ID {trigger_task_id}")

            logger.info(f"Waiting for backup task {trigger_task_id} to complete")
            trigger_task_status = helpers.wait_for_task(
                task_uri=f"/api/v1/tasks/{trigger_task_id}",
                api_header=self.user.headers,
            )
            logger.info(f"Task Status {trigger_task_status}")

        trigger_task_id = trigger_task_id if is_backup_task else task_uri
        trigger_task_status = trigger_task_status if is_backup_task else task_status

        if trigger_task_status == helpers.TaskStatus.success:
            logger.info(f"Task => {trigger_task_id} completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception(f"{trigger_task_id} failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"{trigger_task_id} failed with status'FAILED' error")
        else:
            raise Exception(f"Failed in wait_for_task, task_id: {trigger_task_id} , task status: {task_status}")

    @tag("rds_backup_and_restore")
    @task
    def on_completion(self):
        for db_identifier in DB_IDENTIFIERS:
            self.delete_rds_instance(db_identifier=db_identifier)

        logger.info("All expected tasks done, raising StopUser interrupt")
        raise StopUser()
