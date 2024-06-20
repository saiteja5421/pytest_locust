"""
 Test case:
        DCS-1647: Number of simultaneous requests to restore EC2 instance from S3 backup by creating new EC2 instance.
        DCS-1646: Number of simultaneous requests to restore EC2 instance from S3 backup by replacing existing EC2 instance.
Steps:
    1. Create an Ec2 instance per user , Do inventory refresh and take a backup instance  
    2. Restore to multiple new EC2 instances from the backup simultaneously.
    3. Restore EC2 instances to existing from the backup simultaneously. (When we do this existing instance will be moved to stopped state but new instance will be created.)

"""

import sys
import traceback
import logging
import time
import uuid

from locust import events, HttpUser, between
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.aws.ec2.restore.workflow.task import RestoreTasks
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts
from common import helpers
from common import assets
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from lib.dscc.backup_recovery.aws_protection.assets import ec2, ebs
from tests.steps.aws_protection import ec2_steps
from tests.steps.aws_protection import protection_policy_steps
from lib.dscc.backup_recovery.aws_protection import backups
from lib.logger import rp_agent

from lib.platform.aws.models.instance import Tag
from lib.platform.aws.ebs_manager import EBSManager
from common.enums.ebs_volume_type import EBSVolumeType
from lib.dscc.backup_recovery.aws_protection.accounts.models.csp_account import CSPAccount


from locust.runners import WorkerRunner

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

from lib.platform.aws.ec2_manager import EC2Manager

logger = logging.getLogger(__name__)

VOLUME_DEVICE: str = "/dev/sdh"


source_ec2_list = []
ebs_list = []
ebs_ids_list = []
cleanup_source_ec2_list = []


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        logging.info("On test start: Add Report portal start launch ")
        report_portal_dict = helpers.get_report_portal_info()

        global rp_mgr
        global rp_test_id
        global rp_logger
        user_count = environment.parsed_options.num_users
        run_time_mins = environment.parsed_options.run_time / 60
        test_case_name = "EC2 instance restore workflow"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="BACKUP-RESTORE",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
        config = helpers.read_config()
        account = Accounts(csp_account_name=config["testInput"]["Account"]["name"])
        csp_account: CSPAccount = account.get_csp_account()
        csp_account_id = csp_account["id"]
        logger.info(f"CSP Account: {csp_account}")
        assert csp_account is not None, "Failed to retrieve csp_account"
        logger.info(f"Number of users are {user_count}")

        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        global ec2_manager
        ec2_manager = EC2Manager(aws_session_manager)
        global ebs_manager
        ebs_manager = EBSManager(aws_session_manager)
        global source_tag
        source_tag = Tag(Key=f"perf_test_restore_{helpers.generate_date()}", Value=f"Source_Restore")
        logger.debug(f"Step 1 -> Create Ec2 instance per user")

        zone = config["testbed"]["AWS"]["availabilityzone"]
        image_id = config["testbed"]["AWS"]["imageid"]
        global key_name
        key_name = "Perf_Test_ec2_key" + str(uuid.uuid4())
        ec2_manager.create_ec2_key_pair(key_name=key_name)
        global source_ec2_list
        source_ec2_list = ec2_manager.create_ec2_instance(
            key_name=key_name,
            image_id=image_id,
            availability_zone=zone,
            min_count=1,
            max_count=user_count,
            tags=[source_tag],
        )

        for i in range(0, user_count):
            # Create EBS Volume and attach it to ebs instance
            volume = ebs_manager.create_ebs_volume(
                size=10,
                volume_type=EBSVolumeType.GP2.value,
                tags=[source_tag],
                resource_type="volume",
                encrypted=False,
                availability_zone=zone,
            )
            global ebs_list
            ebs_list.append(volume)
            global ebs_ids_list
            ebs_ids_list.append(volume.id)
            logger.info(f"Created EBS Volume {volume.id}")

            ebs_manager.attach_volume_to_ec2_instance(
                volume_id=volume.id, device=VOLUME_DEVICE, instance_id=source_ec2_list[i].id
            )
            logger.info(f"Attached EBS Volume {volume.id} to EC2 Instance {source_ec2_list[i].id}")

        logger.info("Wait for 2 minutes after Ec2 Instances")
        time.sleep(120)
        logger.info(f"----Step 2-  Do inventory refresh  -------")
        account.refresh_inventory()

        # Validate EC2 in DSCC
        # Check created assets from fixture
        for i in range(0, user_count):
            ec2_instance_id = source_ec2_list[i].id
            logger.info("\n----Step 3-  Validate EBS Volume in DSCC -------")
            csp_instance = ec2.get_csp_ec2_instance_by_aws_id(
                ec2_instance_id=ec2_instance_id, account_id=csp_account_id
            )
            assert csp_instance, f"Did not find csp_instance, ec2_id: {ec2_instance_id}"
            csp_instance_id: str = csp_instance["id"]
            logger.info(f"csp_instance found: {csp_instance_id}")

            ebs_volume_id = ebs_ids_list[i]
            csp_volume = ebs.get_csp_volume_by_aws_id(ebs_volume_id=ebs_volume_id, account_id=csp_account_id)
            assert csp_volume, f"Did not find csp_volume, ebs_id: {ebs_volume_id}"
            csp_ebs_id = csp_volume["id"]
            csp_ebs_resource_uri = csp_volume["resourceUri"]
            logger.info(f"CSP Volume: {csp_ebs_id}, {csp_ebs_resource_uri}")

        logger.info(f"List of standard EC2 instances {source_ec2_list}")
        logger.info(f"List of EBS volumes {ebs_list}")

        logger.info("Create protection policy")
        global protection_policy_id
        global protection_policy_name
        global protections_id
        global cloud_protections_id
        (
            protection_policy_id,
            protection_policy_name,
            protections_id,
            cloud_protections_id,
        ) = protection_policy_steps.create_protection_policy(backup_only=False)
        logger.info(f"Created protection policy {protection_policy_name}")
    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(120, 180)
    headers = helpers.gen_token()
    tasks = [RestoreTasks]
    csp_machine_id = None
    backup_id = None

    def on_start(self):
        try:
            config = helpers.read_config()
            self.account = Accounts(csp_account_name=config["testInput"]["Account"]["name"])
            self.restored_ec2_list = []
            self.restored_ebs_list = []
            global source_ec2_list
            self.ec2_object = source_ec2_list.pop()
            global cleanup_source_ec2_list
            cleanup_source_ec2_list.append(self.ec2_object)
            self.protections_policy_id = protection_policy_id
            self.protection_policy_name = protection_policy_name
            self.protections_id = protections_id

            self.ec2_backup_dict = ec2_steps.backup_ec2_instance_for_given_policy(
                self.ec2_object.id, self.protections_policy_id, self.protection_policy_name, self.protections_id
            )
            # These properties are required to prepare restore payload
            self.backup_id = self.ec2_backup_dict["latest_backup"]["id"]
            self.account_id = self.account.get_csp_account()["id"]
            self.csp_machine = self.ec2_backup_dict["csp_machine"]
            self.csp_machine_id = self.csp_machine["id"]
            restoretag = assets.restore_asset_tag()
            self.restore_tag = []
            self.restore_tag.append(restoretag)
        except Exception as e:
            logger.error(f"[on_start] Exception occurs: {e}")
            logger.error(traceback.format_exc())
            rp_logger.error(f"[on_start] Exception occurs: {e}")
            rp_logger.error(traceback.format_exc())
            rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
            rp_mgr.finish_launch()
            sys.exit(1)

    def on_stop(self):
        logger.info(f"---- [User] restore test completed. Teardown starts-------")

        try:
            # Unprotect Job
            protection_job_id = self.ec2_backup_dict["protection_job_id"]
            unprotect_job_response = protection_job.unprotect_job(protection_job_id)
            logger.info(unprotect_job_response)

            # teardown protection policy
            protection_policy_id = self.ec2_backup_dict["protection_policy_id"]
            delete_protection_policy_response = protection_policy.delete_protection_policy(protection_policy_id)
            logger.info(delete_protection_policy_response)

            # teardown ec2 list created as part of restore operations
            logger.info(f"List of restored ec2 instances is {self.restored_ec2_list}")
            for ec2_instance_name in self.restored_ec2_list:
                csp_machine = ec2.get_csp_machine_by_name(ec2_instance_name)
                ec2_manager.stop_and_terminate_ec2_instance(csp_machine["cspId"])

            logger.info(f"List of restored ebs is {self.restored_ebs_list}")
            for ebs_volume in self.restored_ebs_list:
                csp_ebs_volume = ebs.get_csp_volume_by_name(ebs_volume)
                logger.info(f"Deleting ebs volumes with id {csp_ebs_volume['id']}")
                ebs_manager.delete_volume(csp_ebs_volume["id"])

            # delete the backup created for restore operation
            backups.delete_csp_machine_instance_backup(self.csp_machine_id, self.backup_id)

        except Exception as e:
            logger.error(f"Error while cleaning up the instance created:{e}")

        logger.info(f"---- [User] restore test completed. Teardown End-------")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info(f"----- on test stop------")
    restore_tag = assets.restore_asset_tag()
    ec2_manager.delete_running_ec2_instances_by_tag(restore_tag)
    ec2_manager.terminate_ec2_instances(source_ec2_list)
    logger.info("Restored Ec2 instances are deleted")
    global cleanup_source_ec2_list
    logger.info(f"List of source instances to be deleted {cleanup_source_ec2_list}")
    ec2_manager.delete_running_ec2_instances_by_tag(source_tag)
    ec2_manager.terminate_ec2_instances(cleanup_source_ec2_list)
    logger.info("Source Ec2 instances are deleted")
    global ebs_list
    logger.info(f"List of volumes to be deleted {ebs_list}")
    for volume in ebs_list:
        ebs_manager.delete_volume(volume_id=volume.id)
    ec2_manager.delete_key_pair(key_name)


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
