import logging
import requests
from common import helpers
from lib.dscc.backup_recovery.protection import protection_job
from lib.dscc.backup_recovery.protection import protection_policy
from lib.dscc.backup_recovery.aws_protection import backups
from tests.aws.config import Paths
from lib.dscc.backup_recovery.protection import protection_group
from lib.dscc.backup_recovery.aws_protection.accounts.inventory import Accounts

from common.helpers import squid_is_retry_needed
from tenacity import retry, stop_after_attempt, wait_fixed
from common import common

header = helpers.gen_token()


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_all_protection_policies():
    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_POLICIES}?limit=1000"
    response = requests.request("GET", url, headers=header.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    return response.json()


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_all_ec2_instances():
    url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCES}?limit=1000"
    response = requests.request("GET", url, headers=header.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    return response.json()["items"]


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def delete_all_asset_backups():

    try:

        all_csp_instances = get_all_ec2_instances()

        if len(all_csp_instances) != 0:
            for csp_instance in all_csp_instances:
                # get csp machine instance backups
                url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCES}/{csp_instance['id']}/backups?offset=0&limit=500&sort=pointInTime desc"
                response = requests.request("GET", url, headers=header.authentication_header)
                if (
                    response.status_code == requests.codes.internal_server_error
                    or response.status_code == requests.codes.service_unavailable
                ):
                    return response
                csp_backups = response.json()["items"]

                # get backup Id's from response
                backup_ids = []
                for csp_backup in csp_backups:
                    backup_ids.append(csp_backup["id"])

                # Delete backup of csp instance
                if backup_ids != None:
                    for backup_id in backup_ids:
                        backups.delete_csp_machine_instance_backup(csp_instance["id"], backup_id)
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        logging.info(f"Error on csp instance backup deletion::{e}")


# Unregister account


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def cleanup_fake_aws_accounts():

    try:
        url = f"{helpers.get_locust_host()}{Paths.CSP_ACCOUNTS}"
        response = requests.request("GET", url, headers=header.authentication_header)
        data = response.json()["items"]
        for account in data:
            if account["name"].startswith("fake"):
                fake_account = Accounts(account["name"])
                fake_account.unregister_csp_account()
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        logging.error(f"Error on cleanup fake aws accounts {e}")


delete_all_asset_backups()
try:
    protection_job.unprotect_all()
except Exception as e:
    logging.error(f"Unprotect assets tasks failed with error::{e}")
protection_policy.delete_all_protection_policies()
protection_group.delete_all_protection_groups()

# Unregister fake accounts if exist
cleanup_fake_aws_accounts()
