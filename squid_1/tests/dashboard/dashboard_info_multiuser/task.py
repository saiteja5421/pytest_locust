from locust import SequentialTaskSet, task
from requests import codes
from common import helpers
from tests.dashboard import dashboard_paths
import logging

logger = logging.getLogger(__name__)


class DashboardInfoTask(SequentialTaskSet):
    proxies = helpers.set_proxy()

    apptype = "ALL"

    # def on_start(self):
    # self.headers = self.user.api_header.authentication_header

    @task
    def get_dashboard_backup_capacity_usage_summary(self):
        backup_type = "CLOUD"

        with self.client.get(
            f"{dashboard_paths.DASHBOARD_BACKUP_CAPACITY_USAGE_SUMMARY}?appType={self.apptype}&backupType={backup_type}",
            headers=self.user.api_header.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(f"get_dashboard_backup_capacity_usage_summary-Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get dashboard backup capacity usage summary, StatusCode: {str(response.status_code)},response: {response.text}"
                )
            # logger.info(f"User to be validated is {self.user.api_client_cred.credential_name}")
            logger.info(response.text)

    @task
    def get_dashboard_inventory_summary(self):
        with self.client.get(
            f"{dashboard_paths.DASHBOARD_BACKUP_INVENTORY_SUMMARY}",
            headers=self.user.api_header.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:

            logger.info(f"get_dashboard_inventory_summary-Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get dashboard inventory summary, StatusCode: {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @task
    def get_dashboard_job_execution_status_summary(self):
        range = "TWENTY_FOUR_HOURS"
        with self.client.get(
            f"{dashboard_paths.DASHBOARD_JOB_EXECUTION_STATUS_SUMMARY}?appType={self.apptype}&range={range}",
            headers=self.user.api_header.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:

            logger.info(f" get_dashboard_job_execution_status_summary-Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get dashboard job execution status summary, StatusCode: {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @task
    def get_dashboard_protection_summary(self):
        with self.client.get(
            f"{dashboard_paths.DASHBOARD_PROTECTION_SUMMARY}",
            headers=self.user.api_header.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:

            logger.info(f"get_dashboard_protection_summary-Response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get dashboard protection summary(, StatusCode: {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @task
    def on_completion(self):
        self.interrupt()
