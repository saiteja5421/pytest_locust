import traceback
import uuid
from locust import HttpUser, between, events
import sys
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.aws.protection_group.workflow.task import ProtectionGroupTasks
from common import helpers
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts
import logging
from lib.platform.aws.models.instance import Tag
from lib.logger.rp_agent import ReportPortalStatus
from lib.logger import rp_agent
from locust.runners import WorkerRunner

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

from lib.platform.aws.ec2_manager import EC2Manager

logger = logging.getLogger(__name__)


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
        test_case_name = "Protection groups workflow"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="PROTECTION_POLICY_JOBS_GROUPS",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
        logger.debug(f"Number of users are {user_count}")
        config = helpers.read_config()
        aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
        global account
        account = Accounts(csp_account_name=config["testInput"]["Account"]["name"])
        global ec2_manager
        ec2_manager = EC2Manager(aws_session_manager)
        global source_ec2_list
        global source_tag
        source_tag = Tag(Key=f"perf_test_pgroup_{helpers.generate_date()}", Value="source_ec2_pgroup")
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
            max_count=user_count * 3,
            tags=[source_tag],
        )
        logger.info(f"----Step 2-  Do inventory refresh  -------")
        account.refresh_inventory()
    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        logger.info(f"-----Delete Ec2 instance----")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"-----Delete Ec2 instance----")
        for ec2_instance in source_ec2_list:
            ec2_manager.stop_and_terminate_ec2_instance(ec2_instance.id)
        rp_mgr.finish_test_step(step_id=rp_test_id, status=ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info(f"----- on test stop------")
    ec2_manager.delete_running_ec2_instances_by_tag(source_tag)
    ec2_manager.delete_key_pair(key_name)
    config = helpers.read_config()
    account = Accounts(csp_account_name=config["testInput"]["Account"]["name"])
    account.refresh_inventory()
    if rp_mgr:
        rp_mgr.finish_launch()


class LoadUser(HttpUser):
    between(30, 60)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [ProtectionGroupTasks]

    def on_start(self):
        try:
            config = helpers.read_config()
            self.region = config["testbed"]["AWS"]["region"]
            self.ec2_instance_id1 = source_ec2_list.pop().id
            self.ec2_instance_id2 = source_ec2_list.pop().id
            self.ec2_instance_id_for_modify_protection = source_ec2_list.pop().id
            self.delete_ec2_list = []
            self.delete_ec2_list.append(self.ec2_instance_id1)
            self.delete_ec2_list.append(self.ec2_instance_id2)
            self.delete_ec2_list.append(self.ec2_instance_id_for_modify_protection)
            self.account = account
        except Exception as e:
            logger.error(f"[on_start] Exception occurs: {e}")
            logger.error(traceback.format_exc())
            rp_logger.error(f"[on_start] Exception occurs: {e}")
            rp_logger.error(traceback.format_exc())
            rp_mgr.finish_test_step(step_id=rp_test_id, status=ReportPortalStatus.FAILED)
            rp_mgr.finish_launch()
            sys.exit(1)

    def on_stop(self):
        logger.info(f"---- User test completed -------")

        # delete ec2 instance
        for instance in self.delete_ec2_list:
            ec2_manager.stop_and_terminate_ec2_instance(instance)


@events.request.add_listener
def record_in_report_portal(
    request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs
):
    rp_agent.log_request_stats_in_reportportal(rp_logger, request_type, name, response_time, exception, start_time, url)


@events.quitting.add_listener
def do_checks(environment, **_kw):
    if isinstance(environment.runner, WorkerRunner):
        return

    RP_TEST_STATUS = ReportPortalStatus.PASSED
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
            rp_logger.error(
                f"CHECK FAILED: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)"
            )
            RP_TEST_STATUS = ReportPortalStatus.FAILED
            environment.process_exit_code = 3
        else:
            rp_logger.info(
                f"CHECK SUCCESSFUL: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)"
            )
    if rp_mgr:
        rp_mgr.finish_test_step(step_id=rp_test_id, status=RP_TEST_STATUS)
        rp_mgr.finish_launch()
