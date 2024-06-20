"""
 Test case:
        Number of simultaneous requests to create and delete on demand Backups and hpe backup.
Steps: To create backup
    Create EC2 instances
    Create Protection policy and assign it to EC2 instance
    Each user will get one EC2 instance (At a time 5 users are doing this operation)
    The user will create backups for EC2 instance.

Steps: To delete backup
    Get the list of EC2 Instances. For ex: 10 Ec2 instance are there
    Each user will get one EC2 instance (At a time 5 users are doing this operation)
    The user will get all the backups in an EC2 instance. All the backup details will be stored
    Then delete the backups one at a time.

"""

import sys
import time
import traceback
import uuid
from locust import HttpUser, between, events
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from common import helpers
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.aws.backup.workflow.task import BackupTasks
from tests.steps.aws_protection import protection_policy_steps
from dataclasses import dataclass
from dataclasses_json import LetterCase, dataclass_json
import logging
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts

from lib.logger import rp_agent
from locust.runners import WorkerRunner
from lib.platform.aws.models.instance import Tag
from lib.platform.aws.ec2_manager import EC2Manager

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

logger = logging.getLogger(__name__)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CspInstance:
    id: str
    name: str
    account_id: str


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        logging.info("---- Start Load Test -----------")
        logging.info("On test start: Add Report portal start launch ")
        report_portal_dict = helpers.get_report_portal_info()
        user_count = environment.parsed_options.num_users
        run_time_mins = environment.parsed_options.run_time / 60
        global rp_mgr
        global rp_test_id
        global rp_logger
        test_case_name = "EC2 NATIVE BACKUP"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="BACKUP_RESTORE",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )

        logger.debug(f"Number of users are {user_count}")
        config = helpers.read_config()
        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        global ec2_manager
        ec2_manager = EC2Manager(aws_session_manager)
        global source_tag
        source_tag = Tag(Key=f"perf_test_backup_{helpers.generate_date()}", Value=f"Source_backup")
        logger.debug(f"Step 1 -> Create Ec2 instance per user")
        global source_ec2_list
        zone = config["testbed"]["AWS"]["availabilityzone"]
        image_id = config["testbed"]["AWS"]["imageid"]
        global key_name
        key_name = "Perf_Test_ec2_key" + str(uuid.uuid4())
        ec2_manager.create_ec2_key_pair(key_name=key_name)
        source_ec2_list = ec2_manager.create_ec2_instance(
            key_name=key_name,
            image_id=image_id,
            availability_zone=zone,
            min_count=1,
            max_count=user_count,
            tags=[source_tag],
        )
        logger.info(f"List of standard EC2 instances {source_ec2_list}")
        logger.info("Wait for 2 minutes after EC2 instances are creatd so that refresh inventory works correctly")
        time.sleep(120)

        logger.info(f"Step 2-> Do inventory refresh  -------")
        account = Accounts(csp_account_name=config["testInput"]["Account"]["name"])
        account.refresh_inventory()

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
        logger.info(
            "Wait for 2 minutes after refresh inventory so that all the EC2 instances will be populated into Atlas"
        )
        time.sleep(120)
    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(120, 180)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [BackupTasks]

    def on_start(self):
        try:
            self.local_ec2_instance_id = source_ec2_list.pop().id
            logger.info(f"To create local back up - ec2 instance ID:{self.local_ec2_instance_id}")
            logger.info(f"----Step 3 -  Assign Protection Policy for local backup -------")
            self.protections_policy_id = protection_policy_id
            self.protection_policy_name = protection_policy_name
            self.protections_id = protections_id
            self.cloud_protections_id = cloud_protections_id
            (
                self.protection_job_id_local,
                self.local_csp_machine_id,
                self.protection_policy_id_local,
            ) = protection_policy_steps.assign_protection_policy(
                self.local_ec2_instance_id,
                self.protections_policy_id,
                self.protection_policy_name,
                self.protections_id,
                False,
                cloud_protection_id=self.cloud_protections_id,
            )

            # logger.info(self.protection_job_id_local, self.local_csp_machine_id, self.protection_policy_id_local)
        except Exception as e:
            logger.error(f"[on_start] Exception occurred {e}")
            logger.error(traceback.format_exc())
            rp_logger.error("[on_start] Exception occurred {e}")
            rp_logger.error(traceback.format_exc())
            rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
            rp_mgr.finish_launch()
            sys.exit(1)

    def on_stop(self):
        logger.info(f"---- User test completed -------")
        # Unprotect Job
        unprotect_job_response_local = protection_job.unprotect_job(self.protection_job_id_local)
        logger.info(unprotect_job_response_local)

        # Delete protection policy
        protection_policy_response_local = protection_policy.delete_protection_policy(self.protection_policy_id_local)
        logger.info(protection_policy_response_local)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info(f"----- on test stop------")
    logger.info(f"List of source instances to be deleted {source_ec2_list}")
    ec2_manager.delete_running_ec2_instances_by_tag(source_tag)
    logger.info("Source Ec2 instances are deleted")
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
