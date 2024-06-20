import json
import random

from locust import SequentialTaskSet, task
from requests import codes
import tests.aws.config as config
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts
from common import helpers


class RegisterAccountTask(SequentialTaskSet):

    def on_start(self):
        """Per iteration use one aws account id and register csp account
        when no more aws account is there to process stop execution
        """
        if self.user.aws_account_id_list:
            self.aws_account_id = random.choice(self.user.aws_account_id_list)
        else:
            print("No aws account to register. So stop execution")
            self.user.environment.reached_end = True
            self.user.environment.runner.quit()

    @task
    def register_account(self):
        """Register CSP  account"""
        self.account_name = "Perf_" + helpers.generate_date()
        payload = {"cspId": f"arn:aws:iam::{self.aws_account_id}:", "cspType": "AWS", "name": self.account_name}
        with self.client.post(
            config.Paths.AWS_ACCOUNTS,
            data=json.dumps(payload),
            headers=self.user.headers.authentication_header,
            proxies=self.user.proxies,
            catch_response=True,
        ) as response:
            print(response.status_code)
            if response.status_code != codes.created:
                response.failure(
                    f"Failed to Register csp account {self.account_name}, StatusCode: {response.status_code}"
                )
                print(response.text)

    @task
    def on_completion(self):
        self.interrupt()

    def on_stop(self):
        # Unregister CSP account
        inventory_obj = Accounts(self.account_name)
        inventory_obj.unregister_csp_account()
