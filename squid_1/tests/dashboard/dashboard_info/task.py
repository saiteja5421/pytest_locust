from locust import SequentialTaskSet, task
from requests import codes
from common import helpers
from common.common import is_retry_needed
from tests.dashboard import dashboard_paths
import logging
from tenacity import retry, wait_exponential, stop_after_attempt

logger = logging.getLogger(__name__)


class DashboardInfoTask(SequentialTaskSet):
    proxies = helpers.set_proxy()

    apptype = "ALL"

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(20),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_dashboard_backup_capacity_usage_summary(self):
        try:
            backup_type = "CLOUD"

            with self.client.get(
                f"{dashboard_paths.DASHBOARD_BACKUP_CAPACITY_USAGE_SUMMARY}?appType={self.apptype}&backupType={backup_type}",
                headers=self.user.headers.authentication_header,
                catch_response=True,
                proxies=self.proxies,
                name="get_dashboard_backup_capacity_usage_summary",
            ) as response:
                logger.info(f"get_dashboard_backup_capacity_usage_summary-Response code is {response.status_code}")
                if response.status_code != codes.ok:
                    response.failure(
                        f"Failed to get dashboard backup capacity usage summary, StatusCode: {str(response.status_code)},response: {response.text}"
                    )
                logger.info(response.text)
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="get dashboard backup capacity usage summary",
                exception=f"Error while get dashboard backup capacity usage summary:: {e}",
            )
            raise e

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(20),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_dashboard_inventory_summary(self):
        try:
            with self.client.get(
                f"{dashboard_paths.DASHBOARD_BACKUP_INVENTORY_SUMMARY}",
                headers=self.user.headers.authentication_header,
                catch_response=True,
                proxies=self.proxies,
                name="get_dashboard_inventory_summary",
            ) as response:
                logger.info(f"get_dashboard_inventory_summary-Response code is {response.status_code}")
                if response.status_code != codes.ok:
                    response.failure(
                        f"Failed to get dashboard inventory summary, StatusCode: {str(response.status_code)},response: {response.text}"
                    )
                logger.info(f"get_dashboard_inventory_summary response text::{response.text}")
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="get dashboard inventory summary",
                exception=f"Error while get dashboard inventory summary:: {e}",
            )
            raise e

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(20),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_dashboard_job_execution_status_summary(self):
        try:
            range = "TWENTY_FOUR_HOURS"
            with self.client.get(
                f"{dashboard_paths.DASHBOARD_JOB_EXECUTION_STATUS_SUMMARY}?appType={self.apptype}&range={range}",
                headers=self.user.headers.authentication_header,
                catch_response=True,
                proxies=self.proxies,
                name="get_dashboard_job_execution_status_summary",
            ) as response:

                logger.info(f" get_dashboard_job_execution_status_summary-Response code is {response.status_code}")
                if response.status_code != codes.ok:
                    response.failure(
                        f"Failed to get dashboard job execution status summary, StatusCode: {str(response.status_code)},response: {response.text}"
                    )
                logger.info(response.text)
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="get dashboard job execution status summary",
                exception=f"Error while get dashboard job execution status summary:: {e}",
            )
            raise e

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(20),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_dashboard_protection_summary(self):
        try:
            with self.client.get(
                f"{dashboard_paths.DASHBOARD_PROTECTION_SUMMARY}",
                headers=self.user.headers.authentication_header,
                catch_response=True,
                proxies=self.proxies,
                name="get_dashboard_protection_summary",
            ) as response:
                logger.info(f"get_dashboard_protection_summary-Response code is {response.status_code}")
                if response.status_code != codes.ok:
                    response.failure(
                        f"Failed to get dashboard protection summary(, StatusCode: {str(response.status_code)},response: {response.text}"
                    )
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Get dashboard protection summary",
                exception=f"Error while get get dashboard protection summary:: {e}",
            )
            raise e

    @task
    def on_completion(self):
        self.interrupt()
