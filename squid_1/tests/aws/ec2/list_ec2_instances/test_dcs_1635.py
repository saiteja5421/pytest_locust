from lib.logger.rp_agent import ReportPortalManager
from tests.aws.ec2.list_ec2_instances.task import Ec2Instances
from locust import HttpUser, LoadTestShape, between, events
from common import helpers
from locust.runners import Runner

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


@events.test_start.add_listener
def on_test_start(**kwargs):

    print("---- Start Load Test . Create Report portal Launch -----------")
    report_portal_dict = helpers.get_report_portal_info()
    global rp_mgr
    rp_mgr = ReportPortalManager(report_portal_dict)
    rp_mgr.start_launch()


@events.test_stop.add_listener
def on_test_stop(**kwargs):  # 7

    print("---- Stop Load Test. Finish Report portal launch -----------")
    # Finish launch.
    rp_mgr.finish_launch()


class LoadUser(HttpUser):
    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [Ec2Instances]
    # user_count = 0

    def on_start(self):
        print(f"Runner count {self.environment.runner}")
        self.running_user_count = self.environment.runner.user_count
        self.list_ec2_suite_status = "passed"

        self.runner: Runner = self.environment.runner
        self.runner.iterations_started = 0

        self.rp_agent = rp_mgr
        self.service = rp_mgr.service

        self.list_ec2_suite_id = self.rp_agent.start_suite(
            name=f"List EC2 Instance suite # {self.running_user_count}", description="List ec2 instance suite"
        )

    def on_stop(self):
        self.rp_agent.finish_suite(suite_id=self.list_ec2_suite_id, status=self.list_ec2_suite_status)


class StagesShape(LoadTestShape):
    """
    A simply load test shape class that has different user and spawn_rate at
    different stages.
    Keyword arguments:
        stages -- A list of dicts, each representing a stage with the following keys:
            duration -- When this many seconds pass the test is advanced to the next stage
            users -- Total user count
            spawn_rate -- Number of users to start/stop per second
            stop -- A boolean that can stop that test at a specific stage
        stop_at_end -- Can be set to stop once all stages have run.
    """

    stages = [
        {"duration": 60, "users": 2, "spawn_rate": 1},
        {"duration": 120, "users": 5, "spawn_rate": 2},
        {"duration": 120, "users": 1, "spawn_rate": 1},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None
