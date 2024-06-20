"""
 Test case: DCS-9066
    FLR: [PSR] Run parallel index-files API on different native/cloud backups for same ec2 instance. (5 operations)
    https://nimblejira.nimblestorage.com/browse/DCS-9066
Steps:
    1. Create multiple cloud and native backups of EC2 instance.
    2. Using locust framework for API stress testing call
        "<>/backup-recovery/v1beta1/csp-machine-instances/{id}/backups/{backupId}/index-files" in parallel different native backups of same ec2 instance. (5 users)
    3. Repeat Step 2 for different cloud backups.
Test Plan: https://confluence.eng.nimblestorage.com/display/WIQ/Atlantia+FRS+PQA+Test+plan
"""

import sys
import time
import uuid
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
from tests.aws.gfrs.index_files_workflow.machine_instances.task import (
    CSPMachineInstanceBackupIndexFileTasks,
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

SG_NAME: str = "DCS_9066-" + str(uuid.uuid4())

special_characters = "!#$%&+-.?@^_~"
filename_characters = string.ascii_letters + special_characters

TAG_KEY: str = "Test_DCS_9066_" + str(uuid.uuid4())
TAG_VALUE: str = "Test_DCS_9066"
KEY_PAIR_NAME: str = "Test_DCS_9066_key_" + str(uuid.uuid4())


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        global user_count
        user_count = environment.parsed_options.num_users
        run_time_mins = environment.parsed_options.run_time / 60
        logging.info("---- Start Load Test -----------")
        report_portal_dict = helpers.get_report_portal_info()
        user_count = environment.parsed_options.num_users
        run_time_mins = environment.parsed_options.run_time / 60
        logging.info("On test start: Add Report portal start launch ")
        global rp_mgr
        global rp_test_id
        global rp_logger
        test_case_name = "FLR Machine Instance Workflow"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="FLR",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
        logging.info(f"Number of users are {user_count}")
        config = helpers.read_config()
        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        aws_session = aws(config["testbed"]["AWS"])
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
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(100, 160)
    protection_policy_id = None
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [CSPMachineInstanceBackupIndexFileTasks]

    def on_start(self):
        headers = helpers.gen_token()
        config = helpers.read_config()
        self.aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        aws_session = aws(config["testbed"]["AWS"])
        self.ebs_manager = EBSManager(self.aws_session_manager)
        self.vpc_manager = VPCManager(self.aws_session_manager)
        self.security_group_manager = SecurityGroupManager(self.aws_session_manager)

        logger.info("Create protection policy")
        self.protection_policy_name = "Test_DCS_9066_Protection_Policy_" + str(uuid.uuid4())
        self.protection_policy_obj = protection_policy.create_protection_policy(
            policy_name=self.protection_policy_name, backup_only=False
        )
        self.protection_policy_id = self.protection_policy_obj["id"]
        self.protections_id = self.protection_policy_obj["protections"][0]["id"]
        self.cloud_protections_id = self.protection_policy_obj["protections"][1]["id"]
        logger.info(f"Protection Policy created, Name: {self.protection_policy_name}, ID: {self.protection_policy_id}")
        global ebs_manager
        ebs_manager = EBSManager(self.aws_session_manager)
        tag = Tag(Key=TAG_KEY, Value=TAG_VALUE)
        availability_zone = ec2_manager.get_availability_zone()

        # Get CSP Account
        logger.info(f"\n----Step 1 Get CSP Account for {config['testInput']['Account']['name']} -------")
        account = accounts_steps.Accounts(csp_account_name=config["testInput"]["Account"]["name"])
        csp_account: CSPAccount = account.get_csp_account()
        csp_account_id = csp_account["id"]
        csp_account_name = csp_account["name"]
        csp_account_customer_id = csp_account["customerId"]
        logger.info(f"CSP Account: {csp_account}")
        assert csp_account is not None, "Failed to retrieve csp_account"

        global ec2_list
        ec2_list = []
        global ebs_list
        ebs_list = []
        global ec2_map_list
        ec2_map_list = []

        # Create Ec2 instances
        logger.info(f"\n----Step 2 Create ec2 instances")
        aws_ec2_instance_list = ec2_manager.create_ec2_instance(
            image_id=random_ami_chooser(aws_session),
            key_name=KEY_PAIR_NAME,
            availability_zone=availability_zone,
            tags=[tag],
            resource_type="instance",
            security_groups=[SG_NAME],
            max_count=user_count,
        )
        # Perform Inventory Sync
        logger.info(f"\n----Step 3 Perform Inventory Refresh for {csp_account_id} -------")
        time.sleep(60)
        account.refresh_inventory()
        time.sleep(60)
        for aws_ec2_instance in aws_ec2_instance_list:
            asset_map = {}
            ec2_list.append(aws_ec2_instance)
            aws_ec2_instance_id: str = aws_ec2_instance.id
            asset_map["aws_ec2_instance_id"] = aws_ec2_instance.id
            logger.info(f"Created EC2 Instance {aws_ec2_instance_id}")

            # Create EBS Volume
            volume = ebs_manager.create_ebs_volume(
                size=10,
                volume_type=EBSVolumeType.GP2.value,
                tags=[tag],
                resource_type="volume",
                encrypted=False,
                availability_zone=availability_zone,
            )
            ebs_list.append(volume)
            global aws_ebs_volume_id
            aws_ebs_volume_id = volume.id
            asset_map["aws_ebs_volume_id"] = aws_ebs_volume_id
            logger.info(f"Created EBS Volume {aws_ebs_volume_id}")

            ebs_manager.attach_volume_to_ec2_instance(
                volume_id=volume.id, device=VOLUME_DEVICE, instance_id=aws_ec2_instance_id
            )
            logger.info(f"Attached EBS Volume {aws_ebs_volume_id} to EC2 Instance {aws_ec2_instance_id}")

            # TODO: Format File System (Volume)
            # TODO: remember to close this connection.
            time.sleep(10)
            remote_connect = ec2.connect_to_ec2_instance(
                account_id=csp_account_id,
                ec2_instance_id=aws_ec2_instance_id,
                ec2_manager=ec2_manager,
                key_file=KEY_PAIR_NAME,
            )
            assert remote_connect, f"Failed to connect to EC2 Instance: {aws_ec2_instance_id}"

            file_system_type = random.choice(FILE_SYSTEM_TYPES)
            # format attached EBS and mount to EC2 - random filesystem type
            remote_connect.format_volume_and_mount(
                file_system_device=VOLUME_FS_DEVICE,
                file_system_type=file_system_type,
                mount_point=VOLUME_MOUNT,
            )
            remote_connect.close_connection()
            ec2_map_list.append(asset_map)
        account.refresh_inventory()
        logger.info("\n----Step 4 Validate EC2 Instance and EBS Volume in DSCC -------")
        for asset_map in ec2_map_list:
            aws_ec2_instance_id = asset_map["aws_ec2_instance_id"]
            # Validate EC2 in DSCC
            csp_instance = ec2.get_csp_ec2_instance_by_aws_id(
                ec2_instance_id=aws_ec2_instance_id, account_id=csp_account_id
            )
            assert csp_instance, f"Did not find csp_instance, ec2_id: {aws_ec2_instance_id}"
            asset_map["csp_instance"] = csp_instance
            csp_instance_id = csp_instance["id"]
            asset_map["csp_instance_id"] = csp_instance_id
            logger.info(f"csp_instance found: {csp_instance_id}")
            csp_volume = ebs.get_csp_volume_by_aws_id(ebs_volume_id=aws_ebs_volume_id, account_id=csp_account_id)
            assert csp_volume, f"Did not find csp_volume, ebs_id: {aws_ebs_volume_id}"
            asset_map["csp_volume"] = csp_volume
            csp_ebs_id = csp_volume["id"]
            asset_map["csp_ebs_id"] = csp_ebs_id
            csp_ebs_resource_uri = csp_volume["resourceUri"]
            logger.info(f"CSP Volume: {csp_ebs_id}, {csp_ebs_resource_uri}")

            # Assign Protection Policy to EC2
            logger.info(
                f"\n----Step 5 Assign Protection Policy {self.protection_policy_name} to EC2 {csp_instance_id} -------"
            )
            protection_job_task_uri = protection_job.create_protection_job(
                asset_id=csp_instance_id,
                protections_id_one=self.protections_id,
                protections_id_two=self.cloud_protections_id,
                protection_policy_id=self.protection_policy_id,
                cloud_and_backup_schedules=True,
                asset_type=AssetType.CSP_MACHINE_INSTANCE,
            )
            logger.info(f"Protection Job taskUri: {protection_job_task_uri}")

            # Get Protection Job ID
            protection_job_response = protection_job.get_protection_job_by_asset_id(asset_id=csp_instance_id)
            protection_job_id = protection_job_response["items"][0]["id"]
            asset_map["protection_job_id"] = protection_job_id
            logger.info(f"Protection Job ID: {protection_job_id}")

            # Run On-Demand Native and Cloud Backups (perform operation twice -> expecting 2 AWS Backups & 2 Cloud Backups)
            aws_backup_task_uri_list: list = []
            logger.info(f"\nCreate AWS Backup -------")
            response = protection_job.run_protection_job(protection_job_id=protection_job_id, scheduleIds=[1])
            logger.info(f"Run Protection Job Response: {response}")
            task_uri = helpers.get_task_uri_from_header(response=response)
            logger.info(f"Run Protection Job taskUri: {task_uri}")
            aws_backup_task_uri_list.append(task_uri)
            asset_map["aws_backup_task_uri_list"] = aws_backup_task_uri_list

            cloud_backup_task_uri_list: list = []
            logger.info(f"\nCreate Cloud Backup  -------")
            response = protection_job.run_protection_job(protection_job_id=protection_job_id, scheduleIds=[2])
            logger.info(f"Run Protection Job Response: {response}")
            task_uri = helpers.get_task_uri_from_header(response=response)
            logger.info(f"Run Protection Job taskUri: {task_uri}")
            cloud_backup_task_uri_list.append(task_uri)
            asset_map["cloud_backup_task_uri_list"] = cloud_backup_task_uri_list

        time.sleep(20)

        for asset_map in ec2_map_list:
            aws_backup_task_uri_list = asset_map["aws_backup_task_uri_list"]
            for task_uri in aws_backup_task_uri_list:
                logger.info(f"Wait for task {task_uri} . . .")
                task_status = helpers.wait_for_task(task_uri=task_uri, api_header=headers)
                logger.info(f"Run Protection Job Task status: {task_status}")
                if task_status == helpers.TaskStatus.success:
                    logger.info("Backup completed successfully")
                elif task_status == helpers.TaskStatus.timeout:
                    raise Exception("Backup failed with timeout error")
                elif task_status == helpers.TaskStatus.failure:
                    raise Exception("Backup failed with status'FAILED' error")
                else:
                    raise Exception(
                        f"Create backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
                    )
            cloud_backup_task_uri_list = asset_map["cloud_backup_task_uri_list"]
            for trigger_task_uri in cloud_backup_task_uri_list:
                trigger_task_id = trigger_task_uri.rsplit("/", 1)[1]
                logger.info(f"Wait for Cloud Backup Task ID: {trigger_task_id}")
                task_helper.wait_for_task_percent_complete(task_id=trigger_task_id)
        time.sleep(600)
        account.refresh_inventory()
        logger.info("\n----Step 6 Run Copy 2 Cloud & Validate  -------")
        response = start_cvsa(
            customer_id=csp_account_customer_id,
            account_id=csp_account_id,
            region=aws_session.region_name,
        )

        # NOTE: Task percentage API seems to be off (reaching 100% when only at 21%)
        time.sleep(400)
        logger.info("\n----Step 7 Wait for copy2cloud task completion  -------")
        logger.info(f"Calling wait_for_cloudbackup_completion for {csp_account_name}")
        wait_for_cloudbackup_completion(
            account_id=csp_account_id,
            customer_id=csp_account_customer_id,
            region=aws_session.region_name,
            account_name=csp_account_name,
        )

        for asset_map in ec2_map_list:
            cloud_backup_task_uri_list = asset_map["cloud_backup_task_uri_list"]
            for task_uri in cloud_backup_task_uri_list:
                logger.info(f"Validate Cloud Backup Task Status: {task_uri}")
                task_status = helpers.wait_for_task(task_uri=task_uri, api_header=headers)
                if task_status == helpers.TaskStatus.success:
                    logger.info(f"Cloud Backup was successful, task_uri: {task_uri}, task_status: {task_status}")
                elif task_status == helpers.TaskStatus.timeout:
                    raise Exception("Cloud Backup failed with timeout error")
                elif task_status == helpers.TaskStatus.failure:
                    raise Exception("Cloud Backup failed with status'FAILED' error")
                else:
                    raise Exception(
                        f"Cloud Backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}"
                    )

            aws_backup_ids: list = []
            cloud_backup_ids: list = []
            logger.info("Validate CSP Instance Backups")
            csp_instance_id = asset_map["csp_instance_id"]
            backup_response_data = backups.get_all_csp_machine_instance_backups(csp_instance_id)
            if backup_response_data["total"] > 0:
                for backup in backup_response_data["items"]:
                    if backup["backupType"] == CSPBackupType.NATIVE_BACKUP.value:
                        logger.info(f'Validated Backup: {backup["id"]}')
                        aws_backup_ids.append(backup["id"])
                    elif backup["backupType"] == CSPBackupType.HPE_CLOUD_BACKUP.value:
                        logger.info(f'Validated Cloud Backup: {backup["id"]}')
                        cloud_backup_ids.append(backup["id"])
            logger.info(f"AWS Backup IDs: {aws_backup_ids}")
            logger.info(f"AWS Cloud Backup IDs: {cloud_backup_ids}")
            aws_and_cloud_backup_ids: list = aws_backup_ids + cloud_backup_ids
            logger.info(
                f"Validated the following Backups/Cloud Backups: {aws_and_cloud_backup_ids} for CSP EBS: {csp_ebs_id}"
            )
            asset_map["aws_backup_ids"] = aws_backup_ids
            asset_map["cloud_backup_ids"] = cloud_backup_ids
            asset_map["aws_and_cloud_backup_ids"] = aws_and_cloud_backup_ids

        self.security_group = security_group
        self.current_map = ec2_map_list.pop()
        self.csp_instance_id = self.current_map["csp_instance_id"]
        self.aws_backup_ids = self.current_map["aws_backup_ids"]
        self.cloud_backup_ids = self.current_map["cloud_backup_ids"]

    def on_stop(self):
        logger.info("\n\n---- User test completed -------")
        logger.info(f"\n{'Teardown Start'.center(40, '*')}")
        self.protection_job_id = self.current_map["protection_job_id"]
        if self.protection_job_id:
            logger.info(
                f"Unassigning Protection Policy {self.protection_policy_name}, Protection Job ID: {self.protection_job_id}"
            )
            protection_job.unprotect_job(self.protection_job_id)

        # Delete EC2 Backups
        self.csp_instance_id = self.current_map["csp_instance_id"]
        self.aws_ec2_instance_id = self.current_map["aws_ec2_instance_id"]
        self.aws_ebs_volume_id = self.current_map["aws_ebs_volume_id"]

        if self.csp_instance_id:
            backup_response_data = backups.get_all_csp_machine_instance_backups(self.csp_instance_id)
            if backup_response_data["total"] > 0:
                for backup in backup_response_data["items"]:
                    backup_id = backup["id"]
                    backups.delete_csp_machine_instance_backup(self.csp_instance_id, backup_id)

        for i in range(len(ec2_list)):
            # Detach EBS Volume
            logger.info(f"Detaching EBS Volume {ebs_list[i].id} from EC2 Instance {ec2_list[i].id}")
            ebs_manager.detach_volume_from_instance(
                volume_id=ebs_list[i].id, device="/dev/sdh", instance_id=ec2_list[i].id
            )
            logger.info(f"Detached EBS Volume {ebs_list[i].id}")

            # Delete EBS Volume
            logger.info(f"Deleting EBS Volume {ebs_list[i].id}")
            ebs_manager.delete_volume(volume_id=ebs_list[i].id)
            logger.info("EBS Volume Deleted")

            # Terminate EC2 Instance
            logger.info(f"Terminating EC2 Instance {ec2_list[i].id}")
            ec2_manager.stop_and_terminate_ec2_instance(ec2_instance_id=ec2_list[i].id)
            logger.info("EC2 Instance Terminated")

        # Delete protection policy
        if self.protection_policy_id:
            logger.info(f"Deleting Protection Policy {self.protection_policy_name}")
            protection_policy.delete_protection_policy(self.protection_policy_id)

        logger.info(f"\n{'Teardown Complete: Context'.center(40, '*')}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    if security_group:
        logger.info(f"Deleting Security Group: {SG_NAME}")
        security_group_manager.delete_security_group(security_group_id=security_group.id)

    if KEY_PAIR_NAME:
        logger.info(f"Deleting Key pair {KEY_PAIR_NAME}")
        ec2_manager.delete_key_pair(key_name=KEY_PAIR_NAME)


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
