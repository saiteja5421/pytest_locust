import os
import time
import paramiko
from requests import codes
import requests
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from common import helpers
from tests.aws.config import Paths
from common.helpers import squid_is_retry_needed
from common import common
from common.enums.ec2_username import EC2Username
from lib.platform.aws.remote_ssh_manager import RemoteConnect
from lib.platform.aws.ec2_manager import EC2Manager

logger = logging.getLogger(__name__)
headers = helpers.gen_token()


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_csp_machine_count():
    url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCES}"
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
def get_csp_machine(ec2_instance_id: str):
    """Get csp machine instance object

    Args:
        ec2_instance_id (str): EC2 instance id

    Raises:
        Exception: EC2 instance does not exists in dscc

    Returns:
        dict: csp machine instance response of given ec2 instance id
    """

    url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCES}?filter=name eq '{ec2_instance_id}'"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    logger.info(f"Get csp machine response code: {response.status_code}")
    if response.status_code == codes.ok:
        csp_machine_list = response.json()
        for csp_machine_dict in csp_machine_list["items"]:
            if csp_machine_dict["cspId"] == ec2_instance_id:
                return csp_machine_dict
    raise Exception(f"EC2 instance {ec2_instance_id} does not exists.Check whether Inventory refresh is done")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_csp_ec2_instance_by_aws_id(ec2_instance_id: str, account_id: str = None):
    """Get csp machine instance object

    Args:
        ec2_instance_id (str): EC2 instance id

    Raises:
        Exception: EC2 instance does not exists in dscc

    Returns:
        dict: csp machine instance response of given ec2 instance id
    """

    filter_by = f"cspId eq '{ec2_instance_id}'"
    if account_id:
        filter_by += f" and accountInfo/id eq {account_id}"

    url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCES}?filter={filter_by}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    logger.info(f"Get csp machine response code: {response.status_code}")
    csp_machine_list = response.json()
    logger.info(f"Response: {csp_machine_list}")
    if response.status_code == codes.ok:
        for csp_machine_dict in csp_machine_list["items"]:
            if csp_machine_dict["cspId"] == ec2_instance_id:
                return csp_machine_dict
    raise Exception(f"EC2 instance {ec2_instance_id} does not exists.Check whether Inventory refresh is done")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_csp_machine_by_name(ec2_instance_name: str):
    """Get csp machine instance object

    Args:
        ec2_instance_name (str): EC2 instance name

    Raises:
        Exception: EC2 instance does not exists in dscc

    Returns:
        dict: csp machine instance response of given ec2 instance id
    """
    page_limit = get_csp_machine_count()
    url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCES}?limit={page_limit}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    logger.info(f"Get csp machine response code: {response.status_code}")
    csp_machine_list = response.json()
    logger.info(f"Response: {csp_machine_list}")
    if response.status_code == codes.ok:
        for csp_machine_dict in csp_machine_list["items"]:
            if csp_machine_dict["name"] == ec2_instance_name:
                return csp_machine_dict
    raise Exception(f"EC2 instance {ec2_instance_name} does not exists.Check whether Inventory refresh is done")


def connect_to_ec2_instance(
    account_id: str,
    ec2_instance_id: str,
    ec2_manager: EC2Manager,
    key_file: str,
    source_aws_ec2_instance_id: str = None,
):
    """Connect to EC2 Instance (to setup filesystem and write data)

    Args:
        account_id (str): CSP Account ID
        ec2_instance_id (str): AWS EC2 Instance ID
        ec2_manager (EC2Manager): AWS EC2 Manager object
        key_file (str): Key file name
        source_aws_ec2_instance_id (str, optional): Source AWS EC2 ID. Defaults to None.

    Returns:
        client: Remote client object
    """

    ec2 = ec2_manager.get_ec2_instance_by_id(ec2_instance_id)

    ec2_instance = ec2_manager.get_ec2_instance_by_id(source_aws_ec2_instance_id) if source_aws_ec2_instance_id else ec2
    user_name: str = EC2Username.get_ec2_username(ec2_instance=ec2_instance)

    key_file = f"{key_file}.pem"
    public_dns_name = ""
    try:
        public_dns_name = ec2_manager.wait_for_public_dns(ec2_instance_id)
        ec2_address = public_dns_name
    except Exception as e:
        logger.info(f"RemoteConnect will use ip instead of public DNS. Error: {e}")
        ec2_address = ec2.public_ip_address

    logger.info(f"Remote connection starting to {ec2_instance_id}, account {account_id}")
    logger.info(f"Key pair file {key_file}")
    logger.info(f"ec2 ip: {ec2.public_ip_address}, public dns: {public_dns_name}, connect address: {ec2_address}")
    logger.info(f"Searching in directory: {os.getcwd()}")
    logger.info(f"Private key pair exists: {os.path.exists(key_file)}")
    logger.info(f"env HTTP_PROXY: {os.getenv('HTTP_PROXY')}")

    client = None
    for i in range(6):
        try:
            client = RemoteConnect(
                instance_dns_name=ec2_address,
                username=user_name,
                pkey=paramiko.RSAKey.from_private_key_file(key_file),
                window_size=52428800,
                packet_size=327680,
            )
            if client:
                break
        except Exception as e:
            seconds = 120 + i * 120
            time.sleep(seconds)
            logger.warn(f"Create ssh client retry: {i}, Error: {e}")

    assert client, "RemoteConnect object was not created."
    return client


def generate_key_pair(ec2_manager: EC2Manager, key_pair: str):
    """Generate Key Pair

    Args:
        ec2_manager (EC2Manager): AWS EC2 Manager object
        key_pair (str): Key Pair name
    """
    all_key_pairs = ec2_manager.get_all_ec2_key_pair()
    logger.info(f"All key pairs: {all_key_pairs}")
    key_pair_present = ec2_manager.get_key_pair(key_name=key_pair)
    logger.info(f"Key pair present: {key_pair_present}")
    if key_pair_present:
        ec2_manager.delete_key_pair(key_name=key_pair)
        logger.info("Key pair deleted")
    key_pair_file = f"{key_pair}.pem"
    file_exists = os.path.exists(key_pair_file)
    if file_exists:
        logger.info(f"Removing {key_pair_file} from drive")
        os.remove(key_pair_file)
    file_exists = os.path.exists(key_pair_file)
    logger.info(f"File exists: {file_exists}")
    assert not file_exists, "Private key file still exists"

    key_generated = ec2_manager.create_ec2_key_pair(key_name=key_pair)
    logger.info(f"Key pair generated: {key_generated}")
    private_key_file = open(key_pair_file, "w")
    private_key_file.write(key_generated.key_material)
    private_key_file.close()
    logger.info(f"File saved: {key_pair_file}")
    with open(key_pair_file) as f:
        contents = f.read()
        logger.info(f"File content: {contents}")
