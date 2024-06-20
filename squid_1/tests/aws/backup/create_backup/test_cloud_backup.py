"""
 Test case:
        Number of simultaneous requests to create on demand cloud backups.
Steps:
    Create EC2 instances
    Create Protection policy and assign it to EC2 instance
    Each user will get one EC2 instance (At a time 1 user is doing this operation)
    The user will create cloud backups for EC2 instance.
"""

import uuid
from locust import HttpUser, events
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.aws.backup.create_backup.task_cloud_backup import CreateMultipleCloudBackups

from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from lib.dscc.backup_recovery.aws_protection.assets import ec2
from locust.runners import WorkerRunner
from common import helpers
from common import assets
from tests.steps.aws_protection import accounts_steps
import tests.aws.config as config
import logging
import sys
import traceback
from lib.logger import rp_agent
from lib.platform.aws.ec2_manager import EC2Manager

import locust_plugins

logger = logging.getLogger(__name__)


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
        test_case_name = "EC2 CLOUD BACKUP"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="BACKUP_RESTORE",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
        logger.info(f"Number of users are {user_count}")

    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    tasks = [CreateMultipleCloudBackups]
    protection_job_id = None
    protection_policy_id = None
    csp_machine_id = None
    headers = helpers.gen_token()

    def on_start(self):
        try:
            proxies = helpers.set_proxy()

            aws_config = helpers.read_config()
            source_tag = assets.standard_asset_tag()
            self.aws_session_manager = create_aws_session_manager(aws_config["testbed"]["AWS"])
            self.ec2_manager = EC2Manager(self.aws_session_manager)
            self.region = aws_config["testbed"]["AWS"]["region"]
            self.account_name = aws_config["testInput"]["Account"]["name"]
            with self.client.get(
                config.Paths.AWS_ACCOUNTS, headers=self.headers.authentication_header, proxies=proxies
            ) as response:
                resp_json = response.json()
                self.csp_account = resp_json["items"][1]
            print(f"----Step 1----  Create ec2 instances  -------")
            global instance_count
            instance_count = self.environment.parsed_options.num_users * 3
            zone = aws_config["testbed"]["AWS"]["availabilityzone"]
            image_id = aws_config["testbed"]["AWS"]["imageid"]
            self.key_name = "Perf_Test_ec2_key" + str(uuid.uuid4())
            self.ec2_manager.create_ec2_key_pair(key_name=self.key_name)
            ec2_instances = self.ec2_manager.create_ec2_instance(
                key_name=self.key_name,
                image_id=image_id,
                availability_zone=zone,
                min_count=1,
                max_count=instance_count,
                tags=[source_tag],
            )
            self.ec2_instances = ec2_instances

            print(f"----Step 2-  Do inventory refresh  -------")
            accounts_steps.refresh_account_inventory(aws_config["testInput"]["Account"])

            print(f"----Step 3-  Create and Assign Protection Policy  -------")
            self.protection_job_id = self.create_and_assign_protection_policy()
        except Exception as e:
            logger.error(f"[on_start] Exception occurred {e}")
            logger.error(traceback.format_exc())
            rp_logger.error("[on_start] Exception occurred {e}")
            rp_logger.error(traceback.format_exc())
            rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
            rp_mgr.finish_launch()
            sys.exit(1)

    def create_and_assign_protection_policy(self):
        """
        Creates protection job and assigns protection policy to that job

        Returns:
            array : protection job ids
        """
        response = protection_policy.create_protection_policy(cloud_only=True)
        protection_policy_id, protection_policy_name, protections_id = (
            response["id"],
            response["name"],
            response["protections"][0]["id"],
        )
        self.protection_policy_id = protection_policy_id
        self.csp_machine_ids = []
        self.protection_job_ids = []
        self.instance_to_protection_job = {}

        for ec2_instance in self.ec2_instances:
            csp_machine_dict = ec2.get_csp_machine(ec2_instance.id)
            self.csp_machine_ids.append(csp_machine_dict["id"])
            protection_job.create_protection_job(
                asset_id=csp_machine_dict["id"],
                protections_id_one=protections_id,
                protection_policy_id=protection_policy_id,
            )
            protection_job_id = protection_job.find_protection_job_id(protection_policy_name, csp_machine_dict["id"])
            self.protection_job_ids.append(protection_job_id)
            self.instance_to_protection_job[ec2_instance.id] = {
                "protection_job_id": protection_job_id,
                "asset_id": csp_machine_dict["id"],
            }
        return self.protection_job_ids

    def on_stop(self):
        print(f"---- User test completed -------")
        # Unprotect Job
        print(f"unprotect_job")
        for protection_job_id in self.protection_job_ids:
            unprotect_job_response = protection_job.unprotect_job(protection_job_id)
            print(unprotect_job_response)

        # Delete protection policy
        print(f"delete_protection_policy")
        delete_protection_policy_response = protection_policy.delete_protection_policy(self.protection_policy_id)
        print(delete_protection_policy_response)

        # Delete EC2 instance
        print(f"delete_ec2_instance")
        for ec2_instance in self.ec2_instances:
            self.ec2_manager.stop_and_terminate_ec2_instance(ec2_instance.id)
            self.ec2_manager.delete_key_pair(self.key_name)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info(f"----- on test stop------")


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
