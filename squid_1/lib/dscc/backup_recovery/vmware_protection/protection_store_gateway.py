import requests
import logging
from common import helpers
from tests.vmware.vmware_config import Paths
import json


logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


def get_psg():
    """Get All PSG details

    Returns:
        Object: Response object
    """
    url = f"{helpers.get_locust_host()}{Paths.protection_store_gateways}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(f"Get psg-response code:: {response.status_code}")
    return response


def get_psg_by_name(psg_name):
    logger.info(f"protection store gateways contains: {psg_name}")
    response = get_psg()
    if response.status_code == requests.codes.ok:
        try:
            item = next(
                filter(
                    lambda item: item["displayName"] == psg_name,
                    response.json().get("items"),
                )
            )
            return item
        except StopIteration:
            logger.info(f"Failed to find protection store gateway with name: {psg_name}")
            return {}


def create_psg(
    psgw_name,
    vcenter_id,
    host_id,
    network_name,
    network_ip,
    netmask,
    gateway,
    network_type,
    dns_ip,
    datastore_id,
):
    """_summary_

    Args:
        psgw_name (str): protection store gateway name
        vcenter_id (str): vcenter id
        host_id (str): vcenter host id
        network_name (str): Network name - VM network,Data1 or Data2
        network_ip (str): _description_
        netmask (str): _description_
        gateway (str): _description_
        network_type (str): _description_
        dns_ip (str): _description_
        datastore_id (str): _description_

    Returns:
        _type_: _description_
    """
    maxInCloudDailyProtectedDataInTiB = 1.0
    maxInCloudRetentionDays  = 1
    maxOnPremDailyProtectedDataInTiB = 1.0
    maxOnPremRetentionDays = 1
    override_cpu = (0,)
    override_ram_gib = (0,)
    override_storage_tib = (0,)
    url = f"{helpers.get_locust_host()}{Paths.protection_store_gateways}"
    payload = json.dumps(
        {
            "name": psgw_name,
            "hypervisorManagerId": vcenter_id,
            "vmConfig": {
                "hostId": host_id,
                 "maxInCloudDailyProtectedDataInTiB": maxInCloudDailyProtectedDataInTiB,
                "maxInCloudRetentionDays": maxInCloudRetentionDays,
                "maxOnPremDailyProtectedDataInTiB": maxOnPremDailyProtectedDataInTiB,
                "maxOnPremRetentionDays": maxOnPremRetentionDays,
                "network": {
                    "name": network_name,
                    "networkAddress": network_ip,
                    "subnetMask": netmask,
                    "gateway": gateway,
                    "networkType": network_type,
                    "dns": [{"networkAddress": dns_ip}],
                },
                "override": {"cpu": override_cpu, "ramInGiB": override_ram_gib, "storageInTiB": override_storage_tib},
                "datastoreIds": [datastore_id],
            },
        }
    )
    response = requests.request("POST", url, headers=headers.authentication_header, data=payload)
    logger.info(f"Create psg-response code:: {response.status_code}")
    return response.text


def create_nic(psgw_id, nic_ip, network_name, network_type, subnet, gateway=""):
    url = f"{helpers.get_locust_host()}{Paths.protection_store_gateways}/{psgw_id}/createNic"
    payload = json.dumps(
        {
            "nic": {
                "networkAddress": nic_ip,
                "networkName": network_name,
                "networkType": network_type,
                "subnetMask": subnet,
                "gateway": gateway,
            }
        }
    )
    response = requests.request("POST", url, headers=headers.authentication_header, data=payload)
    logger.info(f"Create nic-response code:: {response.status_code}")
    return response.text


def delete_psg(psgw_id):
    url = f"{helpers.get_locust_host()}{Paths.protection_store_gateways}/{psgw_id}"
    response = requests.request("DELETE", url, headers=headers.authentication_header)
    logger.info(f"Delete psgw-response code:: {response.status_code}")
    return response.text
