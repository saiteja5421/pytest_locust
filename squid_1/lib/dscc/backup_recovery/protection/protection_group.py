import requests
import json
from common.enums.asset_info_types import AssetType
from common import helpers
from common.helpers import squid_is_retry_needed
from tests.aws.config import Paths
from tests.ms365.config import MS365Paths
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from common import common

logger = logging.getLogger(__name__)
headers = helpers.gen_token()


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def delete_protection_group(protection_group_id: str) -> str:
    """Delete protection group

    Args:
        protection_group_id (str): protection group id

    Returns:
        str: delete protection group success message
    """
    try:
        url = f"{helpers.get_locust_host()}{Paths.PROTECTION_GROUPS}/{protection_group_id}"

        response = requests.request(
            "DELETE", url, headers=headers.authentication_header
        )
        logger.info(f"Delete protection group-> response code:{response.status_code}")
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        if response.status_code == requests.codes.accepted:
            return f"Protection group {protection_group_id} deleted successfully"
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(
            f"Error while deleting protection group {protection_group_id}:: {e}"
        )


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def create_static_protection_group(
    csp_account_id: str,
    csp_ec2_id_list: list[str],
    group_name: str,
    regions: list[str],
    client,
    headers,
    proxies,
    asset_type: AssetType = AssetType.CSP_MACHINE_INSTANCE,
) -> str:
    """Create protection group

    Args:
        csp_account_id (str):csp account id
        csp_ec2_id_list(list[str]):ec2 instance ids
        group_name (str):protection group name
        region (str):csp region
        asset_type (str):asset type


    Returns:
        str: delete protection group success message
    """
    # Create Protection Groups & Add EC2 Instances
    try:
        """Creates protection groups will be done simultaneously"""

        payload = {
            "accountIds": [csp_account_id],
            "assetType": asset_type.value,
            "description": "Creating new protection group for PSR test",
            "membershipType": "STATIC",
            "name": group_name,
            "cspRegions": regions,
            "staticMemberIds": csp_ec2_id_list,
        }
        logger.debug(f"[Create protection group ][payload] : {payload}")
        with client.post(
            Paths.PROTECTION_GROUPS,
            data=json.dumps(payload),
            proxies=proxies,
            headers=headers.authentication_header,
            catch_response=True,
            name="Create protection group",
        ) as response:
            try:
                logger.info(
                    f"Create protection group-Response code is {response.status_code}"
                )
                if response.status_code == requests.codes.accepted:
                    task_uri = response.headers["location"]
                    task_status = helpers.wait_for_task(
                        task_uri=task_uri, api_header=headers
                    )
                    if task_status == helpers.TaskStatus.success:
                        logger.info(
                            f"Protection group-{group_name} created successfully"
                        )
                        protection_group_id = get_protection_group_id(group_name)
                        print(f"Protection Group ID: {protection_group_id}")
                        return protection_group_id
                    elif task_status == helpers.TaskStatus.timeout:
                        raise Exception(
                            f"Creating protection group-{group_name} failed with timeout error"
                        )
                    elif task_status == helpers.TaskStatus.failure:
                        raise Exception(
                            f"Creating protection group-{group_name} failed with status'FAILED' error"
                        )
                    else:
                        raise Exception(
                            f"Creating protection group-{group_name} failed with unknown error"
                        )
                    # return response_data
                else:
                    response.failure(
                        f"Failed to create protection group, StatusCode: {str(response.status_code)} , Response text: {response.text}"
                    )
                    logger.info(f"[create_protection_group]: {response.text}")
            except Exception as e:
                response.failure(f"Error while creatig protection group:{e}")
                raise e
    except Exception as e:
        logger.error(f"Failed to create protection group {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_protection_group_id(protection_group_name: str, ms365=False) -> str:
    """get protection group

    Args:
        protection_group_name (str): protection group name

    Returns:
        str: protection group id
    """
    try:
        protection_groups = (
            get_all_protection_groups_ms365() if ms365 else get_all_protection_groups()
        )
        if protection_groups != None:
            for protection_group in protection_groups:
                logger.info(
                    f"Protection group id--> {protection_group['id']} and name-->{protection_group['name']}"
                )
                if protection_group_name == protection_group["name"]:
                    return protection_group["id"]
            else:
                length = len(protection_groups)
                logger.info(
                    f"Protection_group list::{protection_groups}, length::{length}"
                )
                logger.error(
                    f"Protection group with name::{protection_group_name} doesn't exist."
                )
        else:
            logger.error(f"No protection groups available")
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while getting protection group :: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def count_all_protection_groups():
    """get all protection group"""
    try:
        url = f"{helpers.get_locust_host()}{Paths.PROTECTION_GROUPS}?limit=1000"
        response = requests.request("GET", url, headers=headers.authentication_header)
        logger.info(f"Get all protection groups-> response code:{response.status_code}")
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        if response.status_code == requests.codes.ok:
            return response.json()["total"]
        else:
            logger.error(
                f"[count_all_protection_groups]Failed to get count of all_protection_groups-status code:{response.status_code}"
            )
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while getting all protection groups :: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_all_protection_groups():
    """get all protection group"""

    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_GROUPS}?limit=1000"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(f"Get all protection groups-> response code:{response.status_code}")
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code == requests.codes.ok:
        length = response.json()["total"]
        logger.info(f"protection group size::{length}")
        return response.json()["items"]
    else:
        logger.error(
            f"Failed to get all protection groups-status code:{response.status_code}"
        )


def get_all_protection_groups_ms365():
    """get all MS365 protection groups"""

    url = f"{helpers.get_locust_host()}{MS365Paths.PROTECTION_GROUPS}?limit=1000"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(
        f"Get all MS365 protection groups-> response code:{response.status_code}"
    )
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code == requests.codes.ok:
        length = response.json()["total"]
        logger.info(f"protection group size::{length}")
        return response.json()["items"]
    else:
        logger.error(
            f"Failed to get all MS365 protection groups-status code:{response.status_code}"
        )


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_protection_groups_by_name(name):
    """get protection group with the given name"""
    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_GROUPS}?filter=name%20eq%20'{name}'"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    logger.info(
        f"Get protection group with the name {name} -> response code:{response.status_code}"
    )
    if response.status_code == requests.codes.ok:
        return response.json()["items"]
    else:
        logger.error(
            f"Failed to get protection groups with the name {name}-status code:{response.status_code}"
        )


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def delete_all_protection_groups():
    """deletes all protection groups"""
    try:
        all_groups = get_all_protection_groups()
        if all_groups:
            for group in all_groups:
                delete_protection_group(group["id"])
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(
            f"Error while deleting protection group with id {group['id']}:: {e}"
        )
