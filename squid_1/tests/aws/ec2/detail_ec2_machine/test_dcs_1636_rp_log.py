# Test steps
# Get all the Ec2 instances for each user (On-start)
# For each user , details random Ec2 instance for each iteration (In tasks)
import sys
from locust import HttpUser, between
from tests.aws.ec2.detail_ec2_machine.task import CSPMachineInstance
from common import helpers
from lib.logger import rp_agent

import tests.aws.config as config
from locust import events
import logging
from locust.runners import WorkerRunner

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

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
        test_case_name = "List Ec2 Instances"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="ACCOUNTS_INVENTORY",
            test_name=test_case_name,
            test_description=f"Test Name: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )
        logging.info(f"Number of users are {user_count}")
    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [CSPMachineInstance]

    def on_start(self):
        """
        Get the list of Ec2 inventory

        """

        with self.client.get(
            config.Paths.CSP_MACHINE_INSTANCES,
            headers=self.headers.authentication_header,
            proxies=self.proxies,
            catch_response=True,
        ) as response:
            print(response.status_code)
            resp_json = response.json()
            if response.status_code == 404:
                print(f"Failed to load EC2 Machine instances -> {response.status_code}")
                self.environment.runner.quit()
            self.csp_machine_instances = resp_json["items"]


# def checker(environment):
#     while not environment.runner.state in [STATE_STOPPING, STATE_STOPPED, STATE_CLEANUP]:
#         time.sleep(1)
#         if environment.runner.stats.total.fail_ratio > 0.2:
#             print(f"fail ratio was {environment.runner.stats.total.fail_ratio}, quitting")
#             environment.runner.quit()
#             return


# # This will check for every request and stop the execution if threshold (given in checker) is crossed
# @events.init.add_listener
# def on_locust_init(environment, **_kwargs):
#     # dont run this on workers, we only care about the aggregated numbers
#     if isinstance(environment.runner, MasterRunner) or isinstance(environment.runner, LocalRunner):
#         gevent.spawn(checker, environment)


@events.request.add_listener
def record_in_report_portal(
    request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs
):
    rp_agent.log_request_stats_in_reportportal(rp_logger, request_type, name, response_time, exception, start_time, url)
    # if exception:
    #     formatted_error = f"Request {name} failed with exception {exception}"
    #     rp_logger.error(formatted_error)
    # else:
    #     start_date_time = datetime.fromtimestamp(start_time, tz=pytz.timezone("Asia/Kolkata"))
    #     formatted_info = f"| Type: {request_type} | Request: {name} -> {url}| Response time: {response_time}ms | start_time: {start_date_time} |"
    #     rp_logger.info(formatted_info)


@events.quitting.add_listener
def do_checks(environment, **_kw):
    if isinstance(environment.runner, WorkerRunner):
        return

    RP_TEST_STATUS = rp_agent.ReportPortalStatus.PASSED
    logger = rp_agent.set_logger(rp_logger)
    rp_agent.log_stats_summary(environment, logger)

    stats_total = environment.runner.stats.total
    fail_ratio = stats_total.fail_ratio
    # total_rps = stats.total_rps

    # check_rps = opts.check_rps
    check_fail_ratio = 0.01

    if fail_ratio > check_fail_ratio:
        logger.error(f"CHECK FAILED: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)")
        RP_TEST_STATUS = rp_agent.ReportPortalStatus.FAILED
        environment.process_exit_code = 3
    else:
        logger.info(
            f"CHECK SUCCESSFUL: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)"
        )
        # Logic to fail the test case if average response time is beyond expected
        # avg_response_time = stats_total.avg_response_time
        # check_avg_response_time = 600
        # if check_avg_response_time > 0:
        #     if avg_response_time > check_avg_response_time:
        #         rp_logger.error(
        #             f"CHECK FAILED: avg response time was {avg_response_time:.1f} (threshold {check_avg_response_time:.1f})"
        #         )
        #         RP_TEST_STATUS = ReportPortalStatus.FAILED

        #         environment.process_exit_code = 3
        #     else:
        #         rp_logger.info(
        #             f"CHECK SUCCESSFUL: avg response time was {avg_response_time:.1f} (threshold {check_avg_response_time:.1f})"
        #         )

    if rp_mgr:
        rp_mgr.finish_test_step(step_id=rp_test_id, status=RP_TEST_STATUS)
        rp_mgr.finish_launch()
