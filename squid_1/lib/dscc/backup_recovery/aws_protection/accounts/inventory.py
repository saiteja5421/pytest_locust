from requests import codes
import requests
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from common import common
from common.helpers import squid_is_retry_needed
from common import helpers
from tests.aws.config import Paths, RDSPaths

logger = logging.getLogger(__name__)


class Accounts:
    def __init__(self, csp_account_name):
        self.csp_account_name = csp_account_name
        self.api_header = helpers.gen_token()

    @retry(
        retry=squid_is_retry_needed,
        stop=stop_after_attempt(15),
        wait=wait_fixed(10),
        retry_error_callback=common.raise_my_exception,
    )
    def get_csp_account(self):
        url = f"{helpers.get_locust_host()}{Paths.CSP_ACCOUNTS}"
        response = requests.request("GET", url, headers=self.api_header.authentication_header)
        logger.info(f"Get csp accounts-response code:: {response.status_code}")

        if response.status_code == codes.ok:
            account_list = response.json()
            for account_obj in account_list["items"]:
                if account_obj["name"] == self.csp_account_name:
                    return account_obj

        logger.info(f"Get csp accounts-response is -> {response.text}")
        logger.info(f"Requested URL: {response.request.url}")
        raise Exception(f"Account {self.csp_account_name} does not exists")

    @retry(
        retry=squid_is_retry_needed,
        stop=stop_after_attempt(15),
        wait=wait_fixed(10),
        retry_error_callback=common.raise_my_exception,
    )
    def refresh_inventory(self, account_type: str = "EC2") -> None:
        """Refresh inventory - whenever adding/deleting/updating aws assets,use this to refresh inventory in DSCC

        Args:
            account_type (str, optional): Should be EC2 or RDS. Defaults to EC2

        Raises:
            Exception: Refresh inventory Task timeout error
            Exception: Refresh inventory Task status "FAILED" error
            Exception: Refresh inventory unknown error
        """
        csp_account_obj = self.get_csp_account()
        logger.info(csp_account_obj)
        csp_account_id = csp_account_obj["id"]
        url = f"{helpers.get_locust_host()}{Paths.CSP_ACCOUNTS}/{csp_account_id}/refresh"

        if account_type.upper() == "RDS":
            v1_beta_1_api, _ = helpers.get_v1_beta_api_prefix()
            url = f"{helpers.get_locust_host()}{v1_beta_1_api}/{RDSPaths.CSP_RDS_ACCOUNTS}/{csp_account_id}/refresh"

        response = requests.request("POST", url, headers=self.api_header.authentication_header)
        if response.status_code != codes.accepted:
            response_data = response.json()
            logger.error(
                f"Failed to refresh inventory for account {self.csp_account_name}, StatusCode: {response.status_code} and response data:{response_data} "
            )
        else:
            task_uri: str = None
            response_data = response.json()

            task_uri = response.headers["location"]
            task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.api_header)
            if task_status == helpers.TaskStatus.success:
                logger.info("Refresh Inventory completed successfully")
            elif task_status == helpers.TaskStatus.timeout:
                raise Exception("Refresh Inventory failed with timeout error")
            elif task_status == helpers.TaskStatus.failure:
                raise Exception("Refresh Inventory failed with status'FAILED' error")
            else:
                raise Exception("Refresh Inventory failed with unknown error")
        logger.info(response.text)

    def unregister_csp_account(self) -> None:
        """Unregister csp account

        Raises:
            Exception: Unregister Task failed
        """
        try:
            csp_account_obj = self.get_csp_account()
            csp_account_id = csp_account_obj["id"]
            url = f"{helpers.get_locust_host()}{Paths.CSP_ACCOUNTS}/{csp_account_id}"
            response = requests.request("DELETE", url, headers=self.api_header.authentication_header)
            logger.info(f"unregister_csp_account response code->{response.status_code}")
            if response.status_code != codes.accepted:
                raise Exception(
                    f"Failed to unregister csp account {csp_account_id}, StatusCode: {response.status_code}"
                )
        except Exception as e:
            raise Exception(f"Error while unregistering account {csp_account_id}:: {e}")
