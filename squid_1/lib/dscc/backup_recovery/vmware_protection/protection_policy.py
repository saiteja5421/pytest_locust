import json
import logging
import requests
from requests import codes
from lib.dscc.backup_recovery.protection.payload.post_protection_policy import PostProtectionPolicy

from common import helpers
from common.common import get, post, patch, delete, put
from tests.vmware.vmware_config import Paths

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


def get_protection_policy():
    """Get all Protection policy

    Returns:
        Json Object: Return All the Protection policies
    """
    url = f"{helpers.get_locust_host()}{Paths.protection_policies}?limit=0"
    response = requests.request("GET", url, headers=headers.authentication_header)
    return response


def get_protection_policy_by_id(policy_id):
    """Get protection policy by policy id

    Args:
        policy_id (str): Protection policy id

    Returns:
        Json Object: Returns Protection policy json object
    """
    url = f"{helpers.get_locust_host()}{Paths.protection_policies}/{policy_id}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    return response.json()


def get_protection_policy_by_name(policy_name):
    """Get protection policy by name

    Args:
        policy_name (str): Protection policy name

    Returns:
        Object : Returns protection policy object
    """
    logger.info(f"Template name policy contains: {policy_name}")
    response = get_protection_policy()
    if response.status_code == codes.ok:
        try:
            item = next(
                filter(
                    lambda item: item["name"] == policy_name,
                    response.json().get("items"),
                )
            )
            return item
        except StopIteration:
            logger.info(f"Failed to find protection template with name: {policy_name}")
            return {}


def create_protection_policy(
    name,
    expire_after_unit,
    onprem_expire_value,
    cloud_expire_value,
    recurrence,
    repeat_every,
    onprem_protection_store_id_list,
    cloud_protection_store_id_list,
):
    """Create Protection policy

    Args:
        name (str): Protection policy name
        expire_after_unit (str): YEARS
        onprem_expire_value (int): Local backup expire value
        cloud_expire_value (int): Cloud backup expire value
        recurrence (str): WEEKLY,HOURLY
        repeat_every (int): Numeric value
        onprem_protection_store_id_list (list[str]): Local protection store list
        cloud_protection_store_id_list (list[str]): Cloud protection store list
    Raises:
        e: error object
        Exception: Raise proxy/other Exception

    Returns:
        Object: Returns response object
    """
    payload = PostProtectionPolicy(
        name,
        expire_after_unit,
        onprem_expire_value,
        cloud_expire_value,
        recurrence,
        repeat_every,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    )
    try:
        url = f"{helpers.get_locust_host()}{Paths.protection_policies}"
        data = payload.create()
        logger.info(f"policy data {data}")
        response = requests.request("POST", url, headers=headers.authentication_header, data=data)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        if response.status_code == requests.codes.ok:
            response_data = response.json()
            logger.info(f"Response data {response_data}")
            logger.info(f"Create protection policy-Response data::{response.status_code}")
            return response_data

        logger.info(response.text)
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while creating protection policy :: {e}")


def create_protection_policy_with_multiple_cloud_regions(
    name,
    expire_after_unit,
    onprem_expire_value,
    cloud_expire_value,
    recurrence,
    repeat_every,
    onprem_protection_store_id_list,
    cloud_protection_store_id_list,
):
    payload = PostProtectionPolicy(
        name,
        expire_after_unit,
        onprem_expire_value,
        cloud_expire_value,
        recurrence,
        repeat_every,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    )
    try:
        url = f"{helpers.get_locust_host()}{Paths.protection_policies}"
        data = json.dumps(payload)
        response = requests.request("POST", url, headers=headers.authentication_header, data=data)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        if response.status_code == requests.codes.ok:
            response_data = response.json()
            logger.info(f"Response data {response_data}")
            print(response_data)
            logger.info(f"Create protection policy-Response data::{response.status_code}")
        logger.info(response.text)
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while creating protection policy :: {e}")


def delete_protection_policy_by_id(policy_id):
    """Delete protection policy

    Args:
        policy_id (str): protection policy id

    Returns:
        Obect: Response object
    """
    url = f"{helpers.get_locust_host()}{Paths.protection_policies}/{policy_id}"
    response = requests.request("DELETE", url, headers=headers.authentication_header)
    return response
