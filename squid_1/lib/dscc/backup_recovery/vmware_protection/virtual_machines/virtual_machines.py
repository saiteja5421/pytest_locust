import logging
import requests
from common import helpers
from tests.vmware.vmware_config import Paths

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


def get_vm_id_by_name(vm_name):
    """Get virtual machine id by VM name

    Args:
        vm_name (str): vm name

    Returns:
        str: Virtual machine uuid
    """
    url = f"{helpers.get_locust_host()}{Paths.virtual_machines}?filter=name eq '{vm_name}'"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(f"Get virtual machine -response code:: {response.status_code}")
    response_data = response.json().get("items")[0]
    return response_data["id"]
