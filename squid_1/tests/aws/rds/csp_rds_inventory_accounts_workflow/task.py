from locust import SequentialTaskSet, tag, task
from lib.dscc.backup_recovery.aws_protection.accounts.models.csp_account import CSPAccountList
from lib.dscc.backup_recovery.aws_protection.rds.models.csp_rds_accounts import CSPRDSAccount
from tests.aws.config import Paths, RDSPaths
from requests import codes
from common import helpers
import logging
import random
from tenacity import retry, wait_exponential, stop_after_attempt


# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

logger = logging.getLogger(__name__)

v1_beta_1_api, _ = helpers.get_v1_beta_api_prefix()


class CSPRDSAccountsInventory(SequentialTaskSet):
    """
    This class contains the following tasks:
    - GET CSP Account by ID
    - POST CSP Account Inventory Refresh
    The tasks will be run parallelly by virtual users
    """

    def on_start(self):
        """This function will list all the accounts from DSCC.
        If accounts are found, 'csp_rds_accounts' will be initialized.
        One of the values from 'csp_rds_accounts' will be randomly chosen by the tests.
        """
        self.csp_rds_accounts: CSPAccountList = None
        self.csp_rds_account: CSPRDSAccount = None

        # /api/v1/csp-accounts
        with self.client.get(
            Paths.AWS_ACCOUNTS,
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            name="List CSP Accounts",
        ) as response:
            logger.info(f"List CSP accounts->Response code is {response.status_code}\n Response text {response.text}")
            if response.status_code == codes.ok:
                self.csp_rds_accounts = CSPAccountList.from_json(response.text)
                if len(self.csp_rds_accounts.items) < 1:
                    logger.warning(f"CSP RDS Accounts list is empty {self.csp_rds_accounts}")
            else:
                response.failure(
                    f"Failed to get csp RDS accounts list->Response code is {response.status_code}\n Response text {response.text}"
                )

    @tag("rds_inventory")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def detail_csp_rds_accounts(self):
        """Get CSP RDS account details simultaneously"""

        # /backup-recovery/v1beta1/csp-rds-accounts/{id}
        if self.csp_rds_accounts:
            self.csp_rds_account = random.choice(self.csp_rds_accounts.items)
            with self.client.get(
                f"{v1_beta_1_api}/{RDSPaths.CSP_RDS_ACCOUNTS}/{self.csp_rds_account.id}",
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="GET CSP account details",
            ) as response:
                logger.info(
                    f"CSP account {self.csp_rds_account.id} Response code {response.status_code}\n Response text {response.text}"
                )
                if response.status_code == codes.ok:
                    self.csp_rds_account = CSPRDSAccount.from_json(response.text)
                elif response.status_code != codes.ok:
                    response.failure(
                        f"GET CSP account {self.csp_rds_account.id} failed. Response code {response.status_code}\n Response text {response.text}"
                    )
        else:
            raise Exception("No CSP RDS accounts available")

    # commenting this task since refresh inventory task will fail if we trigger refresh inventory task for same account parallely
    # @task
    @retry(
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def refresh_csp_rds_account(self):
        """Perform inventory refresh of csp rds account"""
        # /backup-recovery/v1beta1/csp-rds-accounts/{id}/refresh
        try:
            if self.csp_rds_account:
                with self.client.post(
                    f"{self.csp_rds_account.resource_uri}/refresh",
                    headers=self.user.headers.authentication_header,
                    proxies=self.user.proxies,
                    catch_response=True,
                    name="Refresh CSP account",
                ) as response:
                    try:
                        logger.info(
                            f"Refresh inventory of {self.csp_rds_account.id}->Response code {response.status_code}"
                        )
                        logger.info(f"Refresh inventory of {self.csp_rds_account.id}->Response text {response.text}")
                        if response.status_code == codes.accepted:
                            logger.info(f"Response Headers = {response.headers}")
                            task_uri = response.headers["location"]
                            task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
                            if task_status == helpers.TaskStatus.success:
                                logger.info("Refresh csp account success")
                            elif task_status == helpers.TaskStatus.timeout:
                                raise Exception(f"Refresh csp  account failed with timeout error - Task - {task_uri}")
                            elif task_status == helpers.TaskStatus.failure:
                                raise Exception(f"Refresh csp account failed with status'FAILED' error-Task-{task_uri}")
                            else:
                                raise Exception(f"Refresh csp account failed with unknown error - Task - {task_uri}")
                        else:
                            logger.error(
                                f"Refresh inventory of {self.csp_rds_account.id}->Response code is {response.status_code}"
                            )
                            logger.error(
                                f"Refresh inventory of {self.csp_rds_account.id}->Response text {response.text}"
                            )
                            response.failure(
                                f"Failed to refresh inventory, StatusCode: {response.status_code} , Response text: {response.text}"
                            )
                    except Exception as e:
                        response.failure(f"Exception during refresh for csp account {self.csp_rds_account.id} is {e}")
        except Exception as e:
            helpers.custom_locust_response(self.user.environment, name="refresh_csp_account", exception=e)

    @tag("rds_inventory")
    @task
    def on_completion(self):
        self.interrupt()
