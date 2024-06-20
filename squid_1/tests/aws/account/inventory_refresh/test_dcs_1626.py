"""
Test cases:
        DCS-1622: Number of simultaneous requests to register csp account.
        DCS-1623: Number of simultaneous requests to get onboard_template.
        DCS-1624: Number of simultaneous requests to get list of csp accounts.
        DCS-1625: Number of simultaneous requests to get csp account details.
        DCS-1626: Number of simultaneous requests for csp account inventory refresh.
        DCS-1627: Number of simultaneous requests to validate csp account.
        DCS-1637: Number of simultaneous requests to get list of csp subnets.
        DCS-1638: Number of simultaneous requests to get list of tag keys.
        DCS-1639: Number of simultaneous requests to get list of vpc.  
        
Steps:
        Get the list of csp account created and this list will be used to 
            1. get onboarding template
            2. get csp account details
            3. inventory refresh
            4. validate csp account
            5. get list of csp subnets
            6. get list of tag keys
            7. get list of vpc

"""

import sys
from locust import HttpUser, between, events
from lib.platform.aws.aws_session import create_aws_session_manager
from tests.aws.account.inventory_refresh.task import RefreshInventoryTask
from common import helpers
from tests.aws.config import Paths
import logging
from lib.logger import rp_agent
from locust.runners import WorkerRunner
import requests

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
        global rp_mgr
        global rp_test_id
        global rp_logger
        logging.info("On test start: Add Report portal start launch ")
        test_case_name = "Inventory refresh workflow"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="ACCOUNTS_INVENTORY",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
        logging.info(f"Number of users are {user_count}")
    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(30, 45)
    tasks = [RefreshInventoryTask]

    headers = helpers.gen_token()
    proxies = helpers.set_proxy()

    url = f"{helpers.get_locust_host()}{Paths.CSP_ACCOUNTS}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(f"Get csp accounts-response code:: {response.status_code}")

    if response.status_code == requests.codes.ok:
        account_list = response.json()
        csp_account_response = account_list["items"]
        csp_account_list = []
        # Picking the real accounts not fake accounts(test accounts)
        for account in csp_account_response:
            if not account["name"].startswith("fake"):
                csp_account_list.append(account)

    def on_start(self):
        try:
            self.csp_account = LoadUser.csp_account_list.pop()
            print(self.csp_account)
            self.config = helpers.read_config()
            self.aws_session_manager = create_aws_session_manager(self.config["testbed"]["AWS"])
            self.ec2_manager = EC2Manager(self.aws_session_manager)
        except Exception as E:
            logger.error(f"Failed to get csp account info on start. Exception is {E}")
            # rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
            # rp_mgr.finish_launch()
            sys.exit(1)


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
