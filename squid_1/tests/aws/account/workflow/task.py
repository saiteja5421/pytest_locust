import json
import random
from locust import SequentialTaskSet, task
from common import helpers
import requests
import tests.aws.config as config
import urllib.parse
import logging
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts
from tenacity import retry, wait_exponential, stop_after_attempt
from common.common import is_retry_needed

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins


class CspAccountDetailsTask(SequentialTaskSet):
    def on_start(self):
        """Per iteration use one csp account and fetch details"""
        if self.user.csp_account:
            self.csp_account = random.choice(self.user.csp_account)
        else:
            logging.error("[Task_on_start] No csp account to process")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def register_account(self):
        """Register CSP  account"""

        # Using generate date function taking dummy aws account id to register csp account
        self.aws_account_id = helpers.generate_date()[8:]
        self.account_name = "fake_Perf_" + helpers.generate_date()
        payload = {"cspId": f"arn:aws:iam::{self.aws_account_id}:", "cspType": "AWS", "name": self.account_name}
        with self.client.post(
            config.Paths.AWS_ACCOUNTS,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            try:
                logging.info(f"Register account response code->{response.status_code}")
                if response.status_code != requests.codes.created:
                    response.failure(
                        f"Failed to Register csp account {self.account_name}, StatusCode: {response.status_code}, Response text: {response.text}"
                    )
                logging.info(f"Register account response {response.text}")
            except Exception as e:
                exp = f"Exception occured while registering CSP account: {e}"
                logging.error(exp)
                response.failure(exp)
                raise e

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_onboard_template(self):
        """get csp onboarding template

        Raises:
            Exception: No csp accounts
        """
        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        if self.user.csp_account:
            with self.client.get(
                f"/hybrid-cloud/v1alpha1/csp-accounts/{self.csp_account['id']}/onboardingtemplate",
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                catch_response=True,
                name="/hybrid-cloud/v1alpha1/csp-accounts/<id>/onboardingtemplate",
            ) as response:
                try:
                    logging.info(f"Get onboard template status code ->{response.status_code}")
                    if response.status_code != requests.codes.ok:
                        response.failure(
                            f"Failed to Get onboarding template for csp account {self.csp_account['name']}, StatusCode: {response.status_code}, Response text: {response.text} "
                        )
                    logging.info(f"Get onboard template response ->{response.text}")
                except Exception as e:
                    exp = f"Exception occured while getting onboard template: {e}"
                    logging.error(exp)
                    response.failure(exp)
                    raise e
        else:
            logging.error("No csp accounts present to get onboard template")
            raise Exception(f"No csp accounts present to get onboard template")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def list_csp_account(self):
        """lists csp accounts

        Raises:
            Exception: No csp accounts
        """
        if self.user.csp_account:
            with self.client.get(
                config.Paths.AWS_ACCOUNTS,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                proxies=self.user.proxies,
            ) as response:
                try:
                    logging.info(f"List csp accounts response code is {response.status_code}")
                    if response.status_code != requests.codes.ok:
                        response.failure(
                            f"Failed to get csp account list, StatusCode: {response.status_code}, Response text: {response.text}"
                        )
                except Exception as e:
                    exp = f"Exception occured while list csp accounts : {e}"
                    logging.error(exp)
                    response.failure(exp)
                    raise e
                logging.info(f"List csp accounts response {response.text}")
        else:
            logging.error("No csp accounts present to get the list")
            raise Exception(f"No csp accounts present to get the list ")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_csp_account_details(self):
        """Get csp account details

        Raises:
            Exception: No csp account
        """

        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        if self.user.csp_account:
            with self.client.get(
                f"{self.csp_account['resourceUri']}",
                headers=self.user.headers.authentication_header,
                catch_response=True,
                proxies=self.user.proxies,
            ) as response:
                try:
                    logging.info(f"Get csp account details -> response code: {response.status_code}")
                    if response.status_code != 200:
                        response.failure(
                            f"Failed to get csp account detail, StatusCode: {response.status_code}, Response text: {response.text}"
                        )
                except Exception as e:
                    exp = f"Exception occured while getting csp account details: {e}"
                    logging.error(exp)
                    response.failure(exp)
                    raise e
                logging.info(f"Get csp acount details response->{response.text}")

        else:
            logging.error("No csp account present to get the details.")
            raise Exception(f"No csp account present to get thedetails.")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def validate_csp_account(self):
        """Validate csp account

        Raises:
            Exception: Timeout error
            Exception: Failed error
            Exception: Unknown error
        """
        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        with self.client.post(
            f"{self.csp_account['resourceUri']}/validate",
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
            name="/hybrid/v1beta1/csp-accounts/<id>/validate",
        ) as response:
            try:
                logging.info(f"Validate csp account response is {response.status_code}")
                if response.status_code != requests.codes.accepted:
                    response.failure(
                        f"Failed to validate csp account {self.csp_account['name']}, StatusCode: {response.status_code}, Response text: {response.text}"
                    )
                else:
                    response_data = response.json()
                    task_uri = response.headers["location"]
                    task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
                    if task_status == helpers.TaskStatus.success:
                        logging.info("CSP account validated successfully")
                    elif task_status == helpers.TaskStatus.timeout:
                        raise Exception("CSP account validation failed with timeout error")
                    elif task_status == helpers.TaskStatus.failure:
                        raise Exception("CSP account validation failed with status'FAILED' error")
                    else:
                        raise Exception("CSP account validation failed with unknown error")
            except Exception as e:
                exp = f"Exception occured while validating CSP account: {e}"
                logging.error(exp)
                response.failure(exp)
                raise e
            logging.info(f"Validate csp account response->{response.text}")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_csp_subnets(self):
        """Get csp subnets

        Raises:
            Exception: No csp accounts
        """
        if self.user.csp_account:
            with self.client.get(
                f"/api/v1/csp-accounts/{self.csp_account['id']}/subnets",
                headers=self.user.headers.authentication_header,
                catch_response=True,
                proxies=self.user.proxies,
            ) as response:
                try:
                    logging.info(f"Get csp subnets status code-> {response.status_code}")
                    if response.status_code != 200:
                        response.failure(
                            f"Failed to get csp subnet detail, StatusCode: {response.status_code}, Response text: {response.text}"
                        )
                except Exception as e:
                    exp = f"Exception occured while getting csp subnets: {e}"
                    logging.error(exp)
                    response.failure(exp)
                    raise e
                logging.info(f"Get csp subnets response -> {response.text}")
        else:
            logging.error("No csp accounts present to get the csp subnets")
            raise Exception(f"No csp accounts present to get the csp subnets")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_tag_keys(self):
        """Get csp tag keys"""
        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        if self.user.csp_account:
            with self.client.get(
                f"{self.csp_account['resourceUri']}/csp-tag-keys",
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                catch_response=True,
                name="/hybrid/v1beta1/csp-accounts/<id>/tag-keys",
            ) as response:
                try:
                    logging.info(f"Get tag keys status code-> {response.status_code}")
                    # Getting tag value for each tag key
                    if response.status_code == requests.codes.ok:
                        tag_list = response.json()
                        for key in tag_list:
                            # encoding key since it contains special characters
                            key = urllib.parse.quote(key)
                            with self.client.get(
                                f"{self.csp_account['resourceUri']}/csp-tags?filter=key%20eq%20'{key}'",
                                headers=self.user.headers.authentication_header,
                                proxies=self.user.proxies,
                                catch_response=True,
                            ) as key_response:
                                logging.info(f"Get tag key-values status code-> {key_response.status_code}")
                                if key_response.status_code != requests.codes.ok:
                                    response.failure(
                                        f"Failed to get tag key-values, StatusCode: {key_response.status_code} response text:{key_response.text}"
                                    )
                                logging.info(f"Get tag key-values response text ->{key_response.text}")
                    else:
                        response.failure(
                            f"Failed to get tag key , StatusCode: {response.status_code}, Response text: {response.text}"
                        )
                    logging.info(f"Get tag keys response text ->{response.text}")

                except Exception as e:
                    exp = f"Exception occured while taking tag keys: {e}"
                    logging.error(exp)
                    response.failure(exp)
                    raise e
        else:
            logging.error("No csp accounts present to get tag keys")
            raise Exception(f"No csp accounts present to get tag keys")

    @task
    @retry(
        retry=is_retry_needed,
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_csp_vpc(self):
        """Get csp vpc

        Raises:
            Exception: No csp accounts
        """
        # self.csp_account['resourceUri'] will provide /api/v1/csp-accounts/{id}
        if self.user.csp_account:
            with self.client.get(
                f"/api/v1/csp-accounts/{self.csp_account['id']}/vpcs",
                headers=self.user.headers.authentication_header,
                proxies=self.user.proxies,
                catch_response=True,
                name="/api/v1/csp-accounts/<id>/vpcs",
            ) as response:
                try:
                    logging.info(f"Get csp vpc response code-> {response.status_code}")
                    if response.status_code != requests.codes.ok:
                        response.failure(
                            f"Failed to get vpc detail, StatusCode: {response.status_code}, Response text: {response.text}"
                        )
                except Exception as e:
                    exp = f"Exception occured while getting csp vpc: {e}"
                    logging.error(exp)
                    response.failure(exp)
                    raise e
                logging.info(f"Get csp vpc response->{response.text}")

        else:
            logging.error("No csp accounts present to get vpc")
            raise Exception(f"No csp accounts present to get vpc")

    @task
    def on_completion(self):
        self.interrupt()

    def on_stop(self):
        try:
            # Unregister CSP account
            logging.info("------------ Unregister CSP Account-----------------")
            inventory_obj = Accounts(self.account_name)
            inventory_obj.unregister_csp_account()
        except Exception as e:
            logging.error(f"Exception occurred during on_stop {e}")
