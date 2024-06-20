from locust import between, events, task, SequentialTaskSet, HttpUser
from common import helpers
import logging
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts

from lib.platform.aws.rds_manager import RDSManager
from lib.dscc.backup_recovery.aws_protection.rds import rds_helper

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        print("---- Start Load Test -----------")
        user_count = environment.parsed_options.num_users
        logging.debug(f"Number of users are {user_count}")
        config = helpers.read_config()
        account = Accounts(csp_account_name=config["testInput"]["Account"]["name"])

        rds = RDSManager(aws_config=config["testbed"]["AWS"])
        global rds_db_list
        rds_db_list = []
        for count in user_count:
            db_data = (f"psr_db_{count}", f"psr_db_identifier_{count}")
            rds_db_list.append(db_data)

        for db_name, db_identifier in rds_db_list:
            rds_helper.create_rds_instance(db_name, db_identifier)

        logging.info(f"Step 2-> Do inventory refresh  -------")
        account.refresh_inventory()

    except Exception as e:
        logging.error(f"[on_test_start] Error while creating prerequsites::{e}")
        logging.info(f"-----Delete RDS instance----")
        for rds_db, rds_identifier in rds_db_list:
            rds.delete_db_instance_by_id(rds_identifier)
        exit()


class MyTasks(SequentialTaskSet):
    @task
    def dummy_task(self):
        print("RDS instances are created")
        self.user.environment.reached_end = True
        self.user.environment.runner.quit()


class MyUser(HttpUser):
    wait_time = between(2, 3)
    tasks = [MyTasks]
