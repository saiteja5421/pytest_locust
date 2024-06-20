from requests import codes
import requests
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from common import helpers
from tests.aws.config import Paths
from common.helpers import squid_is_retry_needed
from common import common
from lib.dscc.backup_recovery.aws_protection.ebs.models.csp_volume import CSPVolume

logger = logging.getLogger(__name__)
headers = helpers.gen_token()


def get_csp_volume_by_id(csp_volume_id: str):
    url = f"{helpers.get_locust_host()}{Paths.CSP_VOLUMES}/{csp_volume_id}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if response.status_code == requests.codes.ok:
        return CSPVolume.from_json(response.text)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_csp_volume_by_aws_id(ebs_volume_id: str, account_id: str = None):
    """Get csp volume object
    Args:
        ebs_volume_id (str): EBS Volume id
    Raises:
        Exception: EBS Volume does not exists in dscc
    Returns:
        dict: csp volume response of given ebs volume id
    """
    filter = f"cspId eq '{ebs_volume_id}'"
    if account_id:
        filter += f" and accountInfo/id eq {account_id}"
    url = f"{helpers.get_locust_host()}{Paths.CSP_VOLUMES}?filter={filter}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    logger.info(f"Get csp volume response code: {response.status_code}")
    csp_volume_list = response.json()
    logger.info(f"Response: {csp_volume_list}")
    if response.status_code == codes.ok:
        if csp_volume_list["total"] == 1:
            return csp_volume_list["items"][0]

    raise Exception(f"EBS Volume {ebs_volume_id} does not exist. Check whether Inventory refresh is done")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_csp_volume_count():
    url = f"{helpers.get_locust_host()}{Paths.CSP_VOLUMES}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code == codes.ok:
        return response.json()["total"]
    else:
        raise Exception(f"Error while getting csp machine count:{response.status_code},{response.text}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_csp_volume_by_name(ebs_volume_name: str):
    """Get csp volume object

    Args:
        ebs_volume_name (str): EBS volume name

    Raises:
        Exception: EBS volume does not exists in dscc

    Returns:
        dict: csp volume instance response of given ebs volume name
    """
    page_limit = get_csp_volume_count()
    url = f"{helpers.get_locust_host()}{Paths.CSP_VOLUMES}?limit={page_limit}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    logger.info(f"Get csp volume response code: {response.status_code}")
    csp_volume_list = response.json()
    logger.info(f"Response: {csp_volume_list}")
    if response.status_code == codes.ok:
        for csp_volume_dict in csp_volume_list["items"]:
            if csp_volume_dict["name"] == ebs_volume_name:
                return CSPVolume.from_dict(csp_volume_dict)
    raise Exception(f"EBS volume {ebs_volume_name} does not exists.Check whether Inventory refresh is done")
