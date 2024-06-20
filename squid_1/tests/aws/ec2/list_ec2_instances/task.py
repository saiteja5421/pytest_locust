import logging
from locust import SequentialTaskSet, task
from locust_plugins import StopUser

# from pytest_reportportal import RPLogger

# from Squid.tests.AWS.EC2.list_ec2_instances.test_dcs_1635 import timestamp
import tests.aws.config as config
from requests import codes

from lib.logger.rp_agent import ReportPortalLogger, ReportPortalStatus


class Ec2Instances(SequentialTaskSet):

    def on_start(self):

        # Control based on the iteration count
        self.user.runner.iterations_started += 1

        if self.user.runner.iterations_started >= 5:
            if self.user.runner.running_user_count == 1:
                logging.info("Last user stopped, quitting runner")
                self.user.runner.quit()
            raise StopUser()

    @task
    def list_ec2_instance(self):

        print(f"iteration count {self.user.runner.iterations_started}")
        # Start test item Report Portal versions >= 5.0.0:
        # rp_agent = ReportPoratlManager(service=self.user.service, parent_item_id=self.user.list_ec2_suite_id)
        rp_step_id = self.user.rp_agent.start_test_step(
            name="list_ec2_instance", description="List Ec2 Instance", parent_item_id=self.user.list_ec2_suite_id
        )
        logging = ReportPortalLogger(service=self.user.service, item_id=rp_step_id)

        with self.client.get(
            config.Paths.CSP_MACHINE_INSTANCES,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            proxies=self.user.proxies,
        ) as response:

            print(f"Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(f"Failed to get ec2 instance list, StatusCode: {str(response.status_code)}")
                logging.error(message=f"Error {response.text}")
                self.user.list_ec2_suite_status = ReportPortalStatus.FAILED
                self.user.rp_agent.finish_test_step(step_id=rp_step_id, status=ReportPortalStatus.FAILED)
            else:
                print(response.text)
                logging.info(message=f"{response.text}")
                self.user.rp_agent.finish_test_step(step_id=rp_step_id, status=ReportPortalStatus.PASSED)

    @task
    def on_completion(self):
        self.interrupt()
