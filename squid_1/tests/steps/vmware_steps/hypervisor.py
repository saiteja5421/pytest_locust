from venv import logger
import requests
from common import helpers
from tests.vmware.vmware_config import Paths
from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import (
    IDNotFoundError,
    VcenterNotFoundError,
)

api_header = helpers.gen_token()
dscc_url = helpers.get_locust_host()


def get_vcenters():
    """Get all vcenters"""
    url = f"{dscc_url}{Paths.vcenter}"
    response = requests.request("GET", url, headers=api_header.authentication_header)
    return response


def get_vcenter_id_by_name(name):
    """Get vcenter id by vcenter name

    Args:
        name (str): vcenter name

    Raises:
        VcenterNotFoundError: Vcenter not found exception

    Returns:
        str: Vcenter id
    """
    response = get_vcenters()
    assert (
        response.status_code == requests.codes.ok
    ), f"failed with status code: {response.status_code} and {response.text}"
    try:
        item = next(
            filter(
                lambda item: item["name"] == name,
                response.json().get("items") if response.json().get("items") else [],
            )
        )
        return item["id"]
    except StopIteration:
        raise VcenterNotFoundError(name) from None


def get_host_id(name):
    """Get host id of host name"""
    response = get_hypervisor_hosts()
    logger.info(f"Getting ID of {name}...")
    assert response.status_code == requests.codes.ok, f"Status code: {response.status_code} => {response.text}"
    try:
        found_item = next(
            filter(
                lambda item: item["name"] == name and str(item["state"]).lower() == "ok",
                response.json().get("items") if response.json().get("items") else [],
            )
        )
        logger.info("Got the ID:" + str(found_item["id"]) + f" for {name} in the response")
        return found_item["id"]
    except StopIteration:
        logger.warning(f"ID of {name} not found.")
        raise IDNotFoundError(name) from None


def get_hypervisor_hosts():
    """Get all hypervisor hosts"""
    url = f"{dscc_url}{Paths.hypervisor_hosts}?offset=0&limit=500"
    response = requests.request("GET", url, headers=api_header.authentication_header)
    return response


def get_datastores():
    """Get all datastores"""
    url = f"{dscc_url}{Paths.datastores}?limit=1000"
    print(url)
    response = requests.request("GET", url, headers=api_header.authentication_header)
    return response


def get_datastore_id(datastore_name, vcenter_name):
    datastores = get_datastores()
    assert datastores.status_code == requests.codes.ok

    # Sometimes 'items' value returned as None, Added check here to use [] instead
    datastores = datastores.json().get("items") if datastores.json().get("items") else []
    for item in datastores:
        if item["name"] == datastore_name and item["hypervisorManagerInfo"]["name"] == vcenter_name:
            return item["id"]
    else:
        logger.warning(f"Failed to find datastore ID with name '{datastore_name}' under vcenter '{vcenter_name}'")


def get_moref(name, resp):
    if resp.status_code == requests.codes.ok:
        resp_body = resp.json()
        for item in resp_body["items"]:
            if item["name"] == name:
                return item["appInfo"]["vmware"]["moref"]


def get_networks(vcenter_id):
    url = f"{dscc_url}{Paths.vcenter}/{vcenter_id}/networks"
    response = requests.request("GET", url, headers=api_header.authentication_header)
    return response
