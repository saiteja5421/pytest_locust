"""
Test steps
[PSR] Number of simultaneous request to create a new protection group

"""

from locust import SequentialTaskSet, task
from typing import Union
from requests import codes
from common import helpers
from common.enums.asset_info_types import AssetType as AssetType
from tests.ms365.config import MS365Paths
from lib.dscc.backup_recovery.aws_protection.assets import ec2 as ec2asset
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts
from lib.platform.ms365.ms_inventory_manager import MSInventoryManager
from lib.platform.ms365.models.csp_ms_protection_groups import (
    MS365CSPProtectionGroupCreate,
)
import json
import requests
import logging
import uuid
from lib.dscc.backup_recovery.protection import protection_group
from tenacity import retry, wait_exponential, stop_after_attempt


logger = logging.getLogger(__name__)


class ProtectionGroupTasks(SequentialTaskSet):
    """Protection group tasks create and delete performance are validated."""

    def on_start(self):
        self.config = helpers.read_config()
        self.account = Accounts(
            csp_account_name=self.config["testInput"]["MS365"]["ms365_org_account_name"]
        )
        self.ms365_inmgr_obj = MSInventoryManager
        self.csp_account = self.account.get_csp_account()
        self.protection_group_id = None

    @task
    def create_protection_group(self):
        self.protection_group_name = f"psr_protection_group_{uuid.uuid4().hex}"
        try:
            """Creates protection groups will be done simultaneously"""
            static_member_ids: Union[str, list] = ([],)
            protection_group_name = self.protection_group_name
            self.ms365_org_account_id = self.account.get_csp_account()["id"]
            self.ms365_user_list = self.ms365_inmgr_obj.get_ms365_csp_users_list()
            ms_one_email_id = self.config["testInput"]["MS365"]["ms365_user_email_id"]
            self.ms365_user_id = next(
                filter(
                    lambda item: item.csp_info.email_address == ms_one_email_id,
                    self.ms365_user_list.items,
                )
            ).id
            static_member_ids = (
                [self.ms365_user_id]
                if not isinstance(self.ms365_user_id, list)
                else static_member_ids
            )

            payload: MS365CSPProtectionGroupCreate = MS365CSPProtectionGroupCreate(
                asset_type=AssetType.MS365_USER.value,
                membership_type="STATIC",
                name=protection_group_name,
                description="Creating new protection group for perf test, MS365 Protection Group",
                static_member_ids=static_member_ids,
            )

            logger.debug(f"[Create protection group ][payload] : {payload}")
            with self.client.post(
                MS365Paths.PROTECTION_GROUPS,
                # data=json.dumps(payload.to_json()),
                payload.to_json(),
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="Create protection group",
            ) as response:
                try:
                    logger.info(
                        f"Create protection group-Response code is {response.status_code}"
                    )
                    if response.status_code == requests.codes.accepted:
                        response_data = response.json()
                        task_uri = response.headers["location"].strip('"')

                        task_status = helpers.wait_for_task(task_uri=task_uri)
                        if task_status == helpers.TaskStatus.success:
                            logger.info(
                                f"Protection group-{protection_group_name} created successfully"
                            )
                            self.protection_group_id = (
                                protection_group.get_protection_group_id(
                                    protection_group_name, ms365=True
                                )
                            )
                        elif task_status == helpers.TaskStatus.timeout:
                            raise Exception(
                                f"Creating protection group-{protection_group_name} failed with timeout error"
                            )
                        elif task_status == helpers.TaskStatus.failure:
                            raise Exception(
                                f"Creating protection group-{protection_group_name} failed with status'FAILED' error"
                            )
                        else:
                            raise Exception(
                                f"Creating protection group-{protection_group_name} failed with unknown error"
                            )

                    else:
                        response.failure(f"Response text: {response.text}")
                        logger.info(f"[create_protection_group]: {response.text}")
                except Exception as e:
                    response.failure(f"Error while creatig protection group:{e}")
                    raise e
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Create Protection group",
                exception=e,
            )
            logger.error(f"Failed to create protection group {e}")

    @task
    def delete_protection_group(self):
        try:
            if self.protection_group_id:
                with self.client.delete(
                    f"{MS365Paths.PROTECTION_GROUPS}/{self.protection_group_id}",
                    proxies=self.user.proxies,
                    headers=self.user.headers.authentication_header,
                    catch_response=True,
                    name="Delete Protection group",
                ) as response:
                    logger.info(
                        f"Delete protection group-> response code:{response.status_code}"
                    )
                    if response.status_code != requests.codes.accepted:
                        response.failure(
                            f"Delete protection group failed. Name: {self.protection_group_name} -> Id: {self.protection_group_id}"
                        )
                        logger.error(
                            f"Delete protection group failed. Response code {response.status_code}. Response text: {response.text}"
                        )
            else:
                logger.error(
                    f"Protection group name:{self.protection_group_name} not listed"
                )
        except Exception as e:
            helpers.custom_locust_response(
                environment=self.user.environment,
                name="Delete Protection group",
                exception=f"Error while deleting protection group {self.protection_group_name}:: {e}",
            )
            raise e

    @task
    def on_completion(self):
        self.interrupt()
