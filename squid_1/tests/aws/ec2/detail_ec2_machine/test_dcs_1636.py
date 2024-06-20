# Test steps
# Get all the Ec2 instances for each user (On-start)
# For each user , details random Ec2 instance for each iteration (In tasks)

from locust import HttpUser, between
from tests.aws.ec2.detail_ec2_machine.task import CSPMachineInstance
from common import helpers
import tests.aws.config as config
from locust import events
from locust.runners import WorkerRunner
import logging

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logging.info("On test start: Add Report portal start launch ")


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
            config.Paths.CSP_MACHINE_INSTANCES, headers=self.headers.authentication_header, proxies=self.proxies
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


# @events.init.add_listener
# def on_locust_init(environment, **_kwargs):
#     # dont run this on workers, we only care about the aggregated numbers
#     if isinstance(environment.runner, MasterRunner) or isinstance(environment.runner, LocalRunner):
#         gevent.spawn(checker, environment)


@events.quitting.add_listener
def do_checks(environment, **_kw):
    if isinstance(environment.runner, WorkerRunner):
        return

    stats = environment.runner.stats.total
    fail_ratio = stats.fail_ratio
    # total_rps = stats.total_rps
    avg_response_time = stats.avg_response_time

    # check_rps = opts.check_rps
    check_fail_ratio = 0.2
    check_avg_response_time = 600

    if fail_ratio > check_fail_ratio:
        logging.error(f"CHECK FAILED: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)")
        environment.process_exit_code = 3
    else:
        logging.info(
            f"CHECK SUCCESSFUL: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)"
        )

    if check_avg_response_time > 0:
        if avg_response_time > check_avg_response_time:
            logging.error(
                f"CHECK FAILED: avg response time was {avg_response_time:.1f} (threshold {check_avg_response_time:.1f})"
            )
            # TODO: Update Report portal result here
            environment.process_exit_code = 3
        else:
            logging.info(
                f"CHECK SUCCESSFUL: avg response time was {avg_response_time:.1f} (threshold {check_avg_response_time:.1f})"
            )
