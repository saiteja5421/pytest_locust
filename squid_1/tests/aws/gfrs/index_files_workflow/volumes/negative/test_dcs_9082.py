"""
 Test case: DCS-9082
    FLR: [PSR] Run parallel restore-files API on different native/cloud backups for same ebs volume. (5 operations) - Negative
    https://nimblejira.nimblestorage.com/browse/DCS-9082
Steps:
    1. Create 1 cloud and 1 native backup of EBS Volume.
    2. Post index-files based off of backup.
    2. Using locust framework for API stress testing call
        "<>/backup-recovery/v1beta1/csp-volumes/{id}/backups/{backupId}/restore-files" in parallel different native backups of same ebs volume. (5 users)
    3. Repeat Step 2 for different cloud backups.
Test Plan: https://confluence.eng.nimblestorage.com/display/WIQ/Atlantia+FRS+PQA+Test+plan
"""

import sys
import time
import uuid
from locust import HttpUser, between
import logging
import random
import string
from locust import HttpUser, between, events
from locust.runners import WorkerRunner
from lib.logger import rp_agent
from lib.platform.aws.aws_session import create_aws_session_manager, aws
from lib.dscc.backup_recovery.aws_protection.assets import ec2, ebs
from lib.dscc.backup_recovery.aws_protection import backups
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from lib.dscc.backup_recovery.aws_protection.cloud_backups import start_cvsa, wait_for_cloudbackup_completion
from lib.dscc.backup_recovery.tasks import task_helper
from common import helpers
from tests.steps.aws_protection import accounts_steps
from tests.aws.gfrs.index_files_workflow.volumes.negative.task import (
    RestoreFromNativeAndCloudBackupForCSPVolumeTasks,
)
from common.enums.linux_file_system_types import LinuxFileSystemTypes
from common.enums.asset_info_types import AssetType
from lib.dscc.backup_recovery.aws_protection.accounts.models.csp_account import CSPAccount
from lib.platform.aws.models.instance import Tag
from lib.platform.aws.ebs_manager import EBSManager
from common.enums.ebs_volume_type import EBSVolumeType
from lib.platform.aws.ec2_manager import EC2Manager
from lib.platform.aws.vpc_manager import VPCManager
from lib.platform.aws.security_group_manager import SecurityGroupManager
from common.enums.csp_backup_type import CSPBackupType
from tests.steps.aws_protection.ami_chooser import random_ami_chooser

import locust_plugins

logger = logging.getLogger(__name__)

# /dev/sdh is renamed to /dev/xvdh when viewed from file system
VOLUME_DEVICE: str = "/dev/sdh"
VOLUME_FS_DEVICE: str = "/dev/xvdh"
# we will mount the attached EBS to this directory
VOLUME_MOUNT: str = "/mnt/ebs_volume"

FILE_SYSTEM_TYPES = [LinuxFileSystemTypes.EXT3, LinuxFileSystemTypes.EXT4]

SG_NAME: str = "DCS_9067-" + str(uuid.uuid4())

special_characters = "!#$%&+-.?@^_~"
filename_characters = string.ascii_letters + special_characters

TAG_KEY: str = "Test_DCS_9082_" + str(uuid.uuid4())
TAG_VALUE: str = "Test_DCS_9082"
KEY_PAIR_NAME: str = "Test_DCS_9082_key_" + str(uuid.uuid4())


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        logging.info("---- Start Load Test -----------")
        report_portal_dict = helpers.get_report_portal_info()
        user_count = environment.parsed_options.num_users
        run_time_mins = environment.parsed_options.run_time / 60
        logging.info("On test start: Add Report portal start launch ")
        global rp_mgr
        global rp_test_id
        global rp_logger
        test_case_name = "FLR Negative Volume Workflow"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="FLR",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
        logging.info(f"Number of users are {user_count}")
        config = helpers.read_config()
        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        global vpc_manager
        vpc_manager = VPCManager(aws_session_manager)
        global security_group_manager
        security_group_manager = SecurityGroupManager(aws_session_manager)
        global ec2_manager
        ec2_manager = EC2Manager(aws_session_manager)
        logger.info("Fetching a VPC for new subnet creation.")
        vpcs = vpc_manager.get_all_vpcs()
        vpc = [vpc for vpc in vpcs][0]
        logger.info(f"Fetched VPC {vpc.id}")
        # Creating a security group because "default" one does not have ingress enabled for SSH.
        logger.info(f"Creating new Security Group {SG_NAME}")
        global security_group
        security_group = security_group_manager.create_security_group(
            description="TC-SG", group_name=SG_NAME, vpc_id=vpc.id
        )
        logger.info(f"Created new Security Group {SG_NAME}")

        logger.info(f"Updating Ingress rule for SG {SG_NAME}")
        security_group_manager.update_security_group_ingress_allow_all(security_group)

        # Create Key Pair & EC2 Instance
        logger.info(f"Generating Key Pair {KEY_PAIR_NAME}")
        ec2.generate_key_pair(ec2_manager=ec2_manager, key_pair=KEY_PAIR_NAME)

    except Exception as e:
        logging.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(60, 120)
    protection_policy_id = None
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [RestoreFromNativeAndCloudBackupForCSPVolumeTasks]

    def on_start(self):
        self.protection_policy_id: str = None
        self.protection_job_id: str = None
        self.protection_job = None
        self.protection_policy = None
        self.protection_job_task_uri: str = None
        self.account = None
        self.csp_account = None
        self.csp_account_id = None
        self.csp_account_resource_uri = None

        headers = helpers.gen_token()
        config = helpers.read_config()
        self.aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        aws_session = aws(config["testbed"]["AWS"])
        self.ebs_manager = EBSManager(self.aws_session_manager)
        self.vpc_manager = VPCManager(self.aws_session_manager)
        self.security_group_manager = SecurityGroupManager(self.aws_session_manager)

        logger.info("Create protection policy")
        self.protection_policy_name = "Test_DCS_9082_Protection_Policy_" + str(uuid.uuid4())
        self.protection_policy_obj = protection_policy.create_protection_policy(
            policy_name=self.protection_policy_name, backup_only=False
        )
        self.protection_policy_id = self.protection_policy_obj["id"]
        self.backup_protections_id = self.protection_policy_obj["protections"][0]["id"]
        self.cloud_protections_id = self.protection_policy_obj["protections"][1]["id"]
        logger.info(f"Protection Policy created, Name: {self.protection_policy_name}, ID: {self.protection_policy_id}")
        global ebs_manager
        ebs_manager = EBSManager(self.aws_session_manager)
        tag = Tag(Key=TAG_KEY, Value=TAG_VALUE)
        availability_zone = ec2_manager.get_availability_zone()

        self.aws_ec2_instance = ec2_manager.create_ec2_instance(
            image_id=random_ami_chooser(aws_session),
            key_name=KEY_PAIR_NAME,
            availability_zone=availability_zone,
            tags=[tag],
            resource_type="instance",
            security_groups=[SG_NAME],
        )[0]
        self.aws_ec2_instance_id: str = self.aws_ec2_instance.id
        logger.info(f"Created EC2 Instance {self.aws_ec2_instance_id}")

        # Create EBS Volume
        self.volume = self.ebs_manager.create_ebs_volume(
            size=10,
            volume_type=EBSVolumeType.GP2.value,
            tags=[tag],
            resource_type="volume",
            encrypted=False,
            availability_zone=availability_zone,
        )
        self.aws_ebs_volume_id: str = self.volume.id
        logger.info(f"Created EBS Volume {self.aws_ebs_volume_id}")

        self.ebs_manager.attach_volume_to_ec2_instance(
            volume_id=self.volume.id, device=VOLUME_DEVICE, instance_id=self.aws_ec2_instance_id
        )
        logger.info(f"Attached EBS Volume {self.aws_ebs_volume_id} to EC2 Instance {self.aws_ec2_instance_id}")

        # Get CSP Account
        logger.info(f"\n----Step 1-  Get CSP Account for {config['testInput']['Account']['name']} -------")
        self.account = accounts_steps.Accounts(csp_account_name=config["testInput"]["Account"]["name"])
        self.csp_account: CSPAccount = self.account.get_csp_account()
        self.csp_account_id = self.csp_account["id"]
        self.csp_account_name = self.csp_account["name"]
        self.csp_account_customer_id = self.csp_account["customerId"]
        self.csp_account_resource_uri = self.csp_account["resourceUri"]
        logger.info(f"CSP Account: {self.csp_account}")
        assert self.csp_account is not None, "Failed to retrieve csp_account"

        # TODO: Format File System (Volume)
        # TODO: remember to close this connection.
        remote_connect = ec2.connect_to_ec2_instance(
            account_id=self.csp_account_id,
            ec2_instance_id=self.aws_ec2_instance_id,
            ec2_manager=ec2_manager,
            key_file=KEY_PAIR_NAME,
        )
        assert remote_connect, f"Failed to connect to EC2 Instance: {self.aws_ec2_instance_id}"

        file_system_type = random.choice(FILE_SYSTEM_TYPES)
        # format attached EBS and mount to EC2 - random filesystem type
        remote_connect.format_volume_and_mount(
            file_system_device=VOLUME_FS_DEVICE,
            file_system_type=file_system_type,
            mount_point=VOLUME_MOUNT,
        )
        remote_connect.close_connection()
        # Perform Inventory Sync
        logger.info(f"\n----Step 2-  Perform Inventory Refresh for {self.csp_account_id} -------")
        accounts_steps.refresh_account_inventory(config["testInput"]["Account"])

        # Validate EC2 in DSCC
        # Check created assets from fixture
        logger.info("\n----Step 3-  Validate EBS Volume in DSCC -------")
        csp_instance = ec2.get_csp_ec2_instance_by_aws_id(
            ec2_instance_id=self.aws_ec2_instance_id, account_id=self.csp_account_id
        )
        assert csp_instance, f"Did not find csp_instance, ec2_id: {self.aws_ec2_instance_id}"
        self.csp_instance_id: str = csp_instance["id"]
        logger.info(f"csp_instance found: {self.csp_instance_id}")
        csp_volume = ebs.get_csp_volume_by_aws_id(ebs_volume_id=self.aws_ebs_volume_id, account_id=self.csp_account_id)
        assert csp_volume, f"Did not find csp_volume, ebs_id: {self.aws_ebs_volume_id}"
        self.csp_volume_id: str = csp_volume["id"]
        logger.info(f"csp_volume found: {self.csp_volume_id}")

        self.csp_ebs_id = csp_volume["id"]
        self.csp_ebs_resource_uri = csp_volume["resourceUri"]

        # Create Protection Policy (AWS & Cloud)
        # logger.info(f"\n----Step 6-  Creating Protection Policy: {self.protection_policy_name}")
        # self.protection_policy = protection_policy.create_protection_policy(policy_name=self.protection_policy_name)
        # self.protection_policy_id = self.protection_policy["id"]
        # self.backup_protections_id: str = self.protection_policy["protections"][0]["id"]
        # self.cloud_protections_id: str = self.protection_policy["protections"][1]["id"]
        # logger.info(f"Protection Policy created, Name: {self.protection_policy_name}, ID: {self.protection_policy_id}")

        # Assign Protection Policy to EC2
        logger.info("\n---- Assign Protection Policy  -------")
        self.protection_job_task_uri = protection_job.create_protection_job(
            asset_id=self.csp_ebs_id,
            protections_id_one=self.backup_protections_id,
            protections_id_two=self.cloud_protections_id,
            protection_policy_id=self.protection_policy_id,
            cloud_and_backup_schedules=True,
            asset_type=AssetType.CSP_VOLUME,
        )
        logger.info(f"Protection Job taskUri: {self.protection_job_task_uri}")

        # Get Protection Job ID
        protection_job_response = protection_job.get_protection_job_by_asset_id(asset_id=self.csp_ebs_id)
        self.protection_job_id = protection_job_response["items"][0]["id"]
        logger.info(f"Protection Job ID: {self.protection_job_id}")

        # Run On-Demand Native and Cloud Backups (expecting 1 AWS Backup & 1 Cloud Backups)
        logger.info("\nCreate AWS Backup -------")
        response = protection_job.run_protection_job(protection_job_id=self.protection_job_id, scheduleIds=[1])
        logger.info(f"Run Protection Job Response: {response}")
        task_uri = helpers.get_task_uri_from_header(response=response)
        logger.info(f"Run Protection Job taskUri: {task_uri}")
        logger.info(f"Wait for task {task_uri} . . .")
        task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.headers)
        logger.info(f"Run Protection Job Task status: {task_status}")
        if task_status == helpers.TaskStatus.success:
            logger.info("Backup completed successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception("Backup failed with status'FAILED' error")
        else:
            raise Exception(f"Create backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")

        time.sleep(30)
        logger.info("\nCreate Cloud Backup -------")
        response = protection_job.run_protection_job(protection_job_id=self.protection_job_id, scheduleIds=[2])
        logger.info(f"Run Protection Job Response: {response}")
        cloud_task_uri = helpers.get_task_uri_from_header(response=response)
        logger.info(f"Run Protection Job taskUri: {cloud_task_uri}")

        logger.info("Wait for Cloud Backup task to reach 50 percentages completed . . .")
        # NOTE: Task percentage API seems to be off (reaching 50% when only at 21%)
        time.sleep(480)
        trigger_task_id = cloud_task_uri.rsplit("/", 1)[1]
        logger.info(f"Wait for Cloud Backup Task ID: {trigger_task_id}")
        task_helper.wait_for_task_percent_complete(task_id=trigger_task_id)

        logger.info("\n----Run Copy 2 Cloud & Validate  -------")
        response = start_cvsa(
            customer_id=self.csp_account_customer_id,
            account_id=self.csp_account_id,
            region=aws_session.region_name,
        )

        # NOTE: Task percentage API seems to be off (reaching 100% when only at 21%)
        time.sleep(300)
        wait_for_cloudbackup_completion(
            account_id=self.csp_account_id,
            customer_id=self.csp_account_customer_id,
            region=aws_session.region_name,
            account_name=self.csp_account_name,
        )

        logger.info(f"Validate Cloud Backup Task Status: {cloud_task_uri}")
        task_status = helpers.wait_for_task(task_uri=cloud_task_uri, api_header=self.headers)
        if task_status == helpers.TaskStatus.success:
            logger.info("Backup was successfully")
        elif task_status == helpers.TaskStatus.timeout:
            raise Exception("Backup failed with timeout error")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception("Backup failed with status'FAILED' error")
        else:
            raise Exception(f"Cloud Backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")

        self.aws_backup_id: str = None
        self.cloud_backup_id: str = None
        backup_response_data = backups.get_all_csp_volume_backups(self.csp_ebs_id)
        if backup_response_data["total"] > 0:
            for backup in backup_response_data["items"]:
                if backup["backupType"] == CSPBackupType.NATIVE_BACKUP.value:
                    self.aws_backup_id = backup["id"]
                elif backup["backupType"] == CSPBackupType.HPE_CLOUD_BACKUP.value:
                    self.cloud_backup_id = backup["id"]
        logger.info(f"AWS Backup IDs: {self.aws_backup_id}")
        logger.info(f"AWS Cloud Backup IDs: {self.cloud_backup_id}")

    def on_stop(self):
        logger.info("\n\n---- User test completed -------")
        logger.info(f"\n{'Teardown Start'.center(40, '*')}")
        if self.protection_job_id:
            logger.info(
                f"Unassigning Protection Policy {self.protection_policy_name}, Protection Job ID: {self.protection_job_id}"
            )
            protection_job.unprotect_job(self.protection_job_id)

        # Delete protection policy
        if self.protection_policy_id:
            logger.info(f"Deleting Protection Policy {self.protection_policy_name}")
            protection_policy.delete_protection_policy(self.protection_policy_id)

        # Delete EBS Backups
        if self.csp_volume_id:
            backup_response_data = backups.get_all_csp_volume_backups(self.csp_volume_id)
            if backup_response_data["total"] > 0:
                for backup in backup_response_data["items"]:
                    backup_id = backup["id"]
                    backups.delete_csp_volume_backup(self.csp_volume_id, backup_id)

        # Detach EBS Volume
        logger.info(f"Detaching EBS Volume {self.aws_ebs_volume_id} from EC2 Instance {self.aws_ec2_instance_id}")
        self.ebs_manager.detach_volume_from_instance(
            volume_id=self.aws_ebs_volume_id, device="/dev/sdh", instance_id=self.aws_ec2_instance_id
        )
        logger.info(f"Detached EBS Volume {self.aws_ebs_volume_id}")

        # Delete EBS Volume
        logger.info(f"Deleting EBS Volume {self.aws_ebs_volume_id}")
        self.ebs_manager.delete_volume(volume_id=self.aws_ebs_volume_id)
        logger.info("EBS Volume Deleted")

        # Terminate EC2 Instance
        logger.info(f"Terminating EC2 Instance {self.aws_ec2_instance_id}")
        ec2_manager.stop_and_terminate_ec2_instance(ec2_instance_id=self.aws_ec2_instance_id)
        logger.info("EC2 Instance Terminated")

        logger.info(f"\n{'Teardown Complete: Context'.center(40, '*')}")


@events.request.add_listener
def record_in_report_portal(
    request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs
):
    rp_agent.log_request_stats_in_reportportal(rp_logger, request_type, name, response_time, exception, start_time, url)


@events.quitting.add_listener
def do_checks(environment, **_kw):
    if isinstance(environment.runner, WorkerRunner):
        return

    RP_TEST_STATUS = rp_agent.ReportPortalStatus.PASSED
    logger = rp_agent.set_logger(rp_logger)
    rp_agent.log_stats_summary(environment, logger)

    stats_total = environment.runner.stats.total
    fail_ratio = stats_total.fail_ratio

    check_fail_ratio = 0.01
    logger.info(f"Total number of requests {stats_total.num_requests}")
    if stats_total.num_requests == 0:
        logger.error(f"TEST FAILED: Since no requests occurred")
        RP_TEST_STATUS = rp_agent.ReportPortalStatus.FAILED
        environment.process_exit_code = 3
    else:
        if fail_ratio > check_fail_ratio:
            logger.error(f"CHECK FAILED: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)")
            RP_TEST_STATUS = rp_agent.ReportPortalStatus.FAILED
            environment.process_exit_code = 3
        else:
            logger.info(
                f"CHECK SUCCESSFUL: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)"
            )
    if rp_mgr:
        rp_mgr.finish_test_step(step_id=rp_test_id, status=RP_TEST_STATUS)
        rp_mgr.finish_launch()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info(f"----- on test stop------")

    if security_group:
        logger.info(f"Deleting Security Group: {SG_NAME}")
        security_group_manager.delete_security_group(security_group_id=security_group.id)

    if KEY_PAIR_NAME:
        logger.info(f"Deleting Key pair {KEY_PAIR_NAME}")
        ec2_manager.delete_key_pair(key_name=KEY_PAIR_NAME)
