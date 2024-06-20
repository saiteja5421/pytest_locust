import sys

from locust import HttpUser, between, events
from tests.aws.protection.workflow.task import ProtectionPolicyTasks

from common import helpers
import logging
from lib.logger import rp_agent
from lib.logger.rp_agent import ReportPortalStatus, create_test_in_report_portal

from locust.runners import WorkerRunner

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


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
        test_case_name = "Protection policy workflow"
        rp_mgr, rp_test_id, rp_logger = create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="PROTECTION_POLICY_JOBS_GROUPS",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
    except Exception as e:
        logging.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    protection_policy_list = list()
    tasks = [ProtectionPolicyTasks]


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
