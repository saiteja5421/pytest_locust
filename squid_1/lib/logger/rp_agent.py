from datetime import datetime
import logging
import os
from time import time
from dotenv import load_dotenv, find_dotenv
import pytz
from locust import stats


from reportportal_client import ReportPortalService

logger = logging.getLogger(__name__)


class ReportPortalStatus:
    PASSED = "PASSED"
    FAILED = "FAILED"


class ReportPortalManager:
    def __init__(self, report_portal_dict, launch_suffix="", push_to_report_portal=True):

        if push_to_report_portal:
            self.service = ReportPortalService(
                endpoint=report_portal_dict["endpoint"],
                project=report_portal_dict["project"],
                token=report_portal_dict["token"],
            )

        else:
            self.service = None

        self.launch_name = report_portal_dict["launch_name"] + "-" + launch_suffix
        self.launch_description = report_portal_dict["description"]

    def start_launch(self):

        if self.service:
            launch_id = self.service.start_launch(
                name=self.launch_name,
                start_time=self.timestamp(),
                description=self.launch_description,
            )
        else:
            launch_id = None
        return launch_id

    def finish_launch(self):
        if self.service:
            self.service.finish_launch(end_time=self.timestamp())

            # Due to async nature of the service we need to call terminate() method which
            # ensures all pending requests to server are processed.
            # Failure to call terminate() may result in lost data.
            self.service.terminate()

    def start_suite(self, name, description):
        if self.service:
            suite_id = self.service.start_test_item(
                name=name,
                description=description,
                start_time=self.timestamp(),
                item_type="SUITE",
                # parameters={"user": self.user_count},
            )
            return suite_id
        return None

    def finish_suite(self, suite_id, status):
        if self.service:
            self.service.finish_test_item(item_id=suite_id, end_time=self.timestamp(), status=status)

    def start_test_step(self, name, description, parent_item_id=None):
        if self.service:
            item_id = self.service.start_test_item(
                name=name,
                description=description,
                start_time=self.timestamp(),
                item_type="STEP",
                parent_item_id=parent_item_id,
                parameters={"testcase": name},
            )
            # self.item_id = item_id
            return item_id
        return None

    def finish_test_step(self, step_id, status):
        if self.service:
            self.service.finish_test_item(item_id=step_id, end_time=self.timestamp(), status=status)

    def timestamp(self) -> str:
        """Timestamp required for reportportal"""
        return str(int(time() * 1000))


class ReportPortalLogger:
    def __init__(self, service, item_id):
        self.service = service
        self.item_id = item_id  # To set this call start_test_step

    def info(self, message):
        logging.info(message)
        if self.service != None:
            self.service.log(time=self.timestamp(), message=message, level="INFO", item_id=self.item_id)

    def debug(self, message):
        logging.debug(message)
        if self.service != None:
            self.service.log(time=self.timestamp(), message=message, level="DEBUG", item_id=self.item_id)

    def error(self, message):
        logging.error(message)
        if self.service != None:
            self.service.log(time=self.timestamp(), message=message, level="ERROR", item_id=self.item_id)

    def warn(self, message):
        logging.warn(message)
        if self.service != None:
            self.service.log(time=self.timestamp(), message=message, level="WARN", item_id=self.item_id)

    def timestamp(self) -> str:
        """Timestamp required for reportportal"""
        return str(int(time() * 1000))


def create_test_in_report_portal(report_portal_dict, launch_suffix, test_name, test_description):
    """
        A test item will be created in Reportportal
        If launch(Envelope of test item) is there in .env file ,it will be reused and the result will be pushed in it. This is useful to push multiple workflow in same launch.
        if launch_id is not there in .env, it will create new launch and launch_id will be updated in .env file

    Args:
        report_portal_dict (dict): report portal project ,token and launch prefix will be passed. (it is available in config.yml)
        launch_suffix (str): Suffix will be append with launch name
        test_name (str): test case name
        test_description (str): test description

    Returns:
        tuple: report portal manager obj(reportPortal client service object),test id and logger . tuple will be container None,None,None if ENABLE_REPORT_PORTAL is false
    """
    try:
        push_to_report_portal = os.environ.get("ENABLE_REPORT_PORTAL", default="False")
        logger.info(f"Push to report portal flag::{push_to_report_portal}")
        push_to_report_portal = eval(push_to_report_portal.capitalize())

        env_path = find_dotenv()
        launch_id = _get_launch_id(env_path)

        if push_to_report_portal:
            rp_mgr = ReportPortalManager(report_portal_dict, launch_suffix, push_to_report_portal)
            if launch_id:
                # Reuse the existing launch to push result
                rp_mgr.service.launch_id = launch_id
            else:
                # create new launch to push result
                launch_id = rp_mgr.start_launch()
                if launch_id:
                    _add_launch_id_to_env(env_path, launch_id)

            rp_test_id = rp_mgr.start_test_step(name=test_name, description=test_description)
            rp_logger = ReportPortalLogger(service=rp_mgr.service, item_id=rp_test_id)
            return rp_mgr, rp_test_id, rp_logger
        else:
            return None, None, None
    except Exception as e:
        logger.error(f"Push results to report portal failed->{e}")


def _add_launch_id_to_env(env_path, launch_id):
    with open(env_path, "a") as env_file:
        env_file.write("\n")
        env_file.write(f"LAUNCH_ID={launch_id}")


def _get_launch_id(env_path):
    load_dotenv(env_path)
    launch_id = os.getenv("LAUNCH_ID")
    return launch_id


def log_request_stats_in_reportportal(rp_logger, request_type, name, response_time, exception, start_time, url):
    if exception:
        formatted_error = f"Request {name} failed with exception {exception}"
        rp_logger.error(formatted_error)
    else:
        start_date_time = datetime.fromtimestamp(start_time, tz=pytz.timezone("Asia/Kolkata"))
        formatted_info = f"| Type: {request_type} | Request: {name} -> {url}| Response time: {response_time}ms | start_time: {start_date_time} |"
        if rp_logger:
            rp_logger.debug(formatted_info)
        else:
            logger.debug(formatted_info)


def set_logger(rp_logger):
    if rp_logger:
        logger = rp_logger
    else:
        logger = logging.getLogger(__name__)
    return logger


def log_stats_summary(environment, logger):
    logger.info("Result Summary")
    summary = stats.get_stats_summary(environment.runner.stats, True)
    summary_str = "\n".join([str(elem) for elem in summary])
    logger.info(summary_str)

    # logger.info(stats.get_stats_summary(environment.runner.stats, True))
    percentile_stats = stats.get_percentile_stats_summary(environment.runner.stats)
    logger.info("Percentile Summary")
    percentile_str = "\n".join([str(elem) for elem in percentile_stats])
    logger.info(percentile_str)
    if len(environment.runner.stats.errors):
        logger.info("Error Summary")
        # logger.info(stats.get_error_report_summary(environment.runner.stats))
        summary = stats.get_error_report_summary(environment.runner.stats)
        summary_str = "\n".join([str(elem) for elem in summary])
        logger.info(summary_str)
