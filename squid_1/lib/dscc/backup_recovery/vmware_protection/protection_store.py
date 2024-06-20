import json
import random
import string
import requests
from common import helpers
from requests import codes
import logging
from lib.dscc.backup_recovery.vmware_protection import protection_store_gateway
from tests.vmware.vmware_config import Paths
from common.enums.azure_locations import AzureLocations


logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


def create_protection_store(psgw_name, type, cloud_region=AzureLocations.AZURE_canadacentral):
    """This will create either (cloud/on premises) of the protection store based on type.

    Args:
        psgw_name (string): to create local/cloud store under this psg.
        type (string): Type of protection store(ON_PREMISES,CLOUD).
        cloud_region (string, optional): regions where you want to create schedules. Defaults to AWSRegions.AWS_EU_WEST_1.

    """
    protection_store_name_suffix = "".join(random.choice(string.ascii_letters) for _ in range(3))
    protection_store_name = f"{psgw_name.split('#')[0]}_{protection_store_name_suffix}"
    psgw_response = protection_store_gateway.get_psg()
    psgw_id = get_psg_id_from_response(psgw_name, psgw_response)

    if type == "CLOUD":
        protection_store_payload = {
            "displayName": f"CLOUD_{protection_store_name}",
            "protectionStoreType": "CLOUD",
            "storageLocationId": cloud_region.value,
            "storageSystemId": psgw_id,
        }
    elif type == "ON_PREMISES":
        protection_store_payload = {
            "displayName": f"ON_PREMISES_{protection_store_name}",
            "protectionStoreType": "ON_PREMISES",
            "storageSystemId": psgw_id,
        }

    logger.info(f"Protection store creation payload: {protection_store_payload}")
    payload = json.dumps(protection_store_payload, indent=4)
    try:
        url = f"{helpers.get_locust_host()}{Paths.protection_stores}"
        response = requests.request("POST", url, headers=headers.authentication_header, proxies=proxies, data=payload)
        logger.info(f"Protection store creation response{response.text}")
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == requests.codes.accepted:
            task_uri = helpers.get_task_uri_from_header(response)
            logger.info(f"create protection store task id : {task_uri.split('/')[-1]}")
            task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30,api_header=headers)
            if task_status == helpers.TaskStatus.success:
                logger.info(f"Protection store {protection_store_name} created successfully.")
            elif task_status == helpers.TaskStatus.timeout:
                logger.error("Protection store creation failed with timeout error.")
            elif task_status == helpers.TaskStatus.failure:
                raise Exception("Protection store creation failed with status'FAILED' error")
            else:
                raise Exception("Protection store creation failed with unknown error")
            logger.info(f"Create protection store {protection_store_name} succeeded of type {type}.")
            return response
        else:
            err_msg = f"Failed to create protection store. Response is {response}"
            logger.error(err_msg)
            raise Exception(err_msg)
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while creating protection store {protection_store_name}:: {e}")


def get_all_protection_stores():
    """fetches all protection stores

    Returns:
        _type_: _description_
    """
    url = f"{helpers.get_locust_host()}{Paths.protection_stores}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    assert (
        response.status_code == codes.ok
    ), f"Failed to get protection_stores.Response status code: {response.status_code} Response {response.text}"
    return response


def get_protection_store_by_name(protection_store_name):
    logger.info(f"protection stores contains: {protection_store_name}")
    response = get_all_protection_stores()
    if response.status_code == codes.ok:
        try:
            item = next(
                filter(
                    lambda item: item["displayName"] == protection_store_name,
                    response.json().get("items"),
                )
            )
            return item
        except StopIteration:
            logger.info(f"Failed to find protection store with name: {protection_store_name}")
            return {}


def get_protection_store_gateway_id(psgw_name):
    """
    To get psgw id with psgw name

    """
    protection_store_gateways = protection_store_gateway.get_psg()
    protection_store_gateway_id = get_psg_id_from_response(psgw_name, protection_store_gateways)
    return protection_store_gateway_id


def get_psg_id_from_response(psgw_name, response):
    assert response.status_code == codes.ok, f"Status code: {response.status_code} => {response.text}"
    try:
        found_item = next(
            filter(
                lambda item: item["name"].strip() == psgw_name.strip(),
                response.json().get("items"),
            )
        )
        return found_item["id"]
    except StopIteration:
        logger.info(f'PSGW VM "{psgw_name}" - not found in {response}')
        return None


def get_on_premises_and_cloud_protection_store(psgw_name):
    """Fetches the protection stores associated to current psg.

    Args:
        context: test_context

    Returns:
        strings: protection store ids (both cloud and on_premises)
    """
    protection_stores_response = get_all_protection_stores()
    psgw_id = get_protection_store_gateway_id(psgw_name)
    on_premises_store_id_list = []
    cloud_store_id_list = []
    assert (
        protection_stores_response.status_code == codes.ok
    ), f"Protection stores not fetched properly: {protection_stores_response.status_code}, {protection_stores_response.text}"
    for protection_store in protection_stores_response.json().get("items"):
        if protection_store["storageSystemInfo"]["id"] == psgw_id:
            if protection_store["protectionStoreType"] == "ON_PREMISES":
                on_premises_store_id_list.append(protection_store["id"])
            elif protection_store["protectionStoreType"] == "CLOUD":
                cloud_store_id_list.append(protection_store["id"])
    return on_premises_store_id_list, cloud_store_id_list


def delete_protection_store(protection_store_id, force=False):
    """delete protection store by protection store id

    Args:
        protection_store_id (string): protection store id that we need to be deleted.
        force (bool): while deleting store weather to use force or not. Defaults to False.

    """
    try:
        url = f"{helpers.get_locust_host()}{Paths.protection_stores}"
        response = requests.request(
            "DELETE",
            f"{url}/{protection_store_id}?force={force}",
            headers=headers.authentication_header,
            proxies=proxies,
        )
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == requests.codes.accepted:
            task_uri = helpers.get_task_uri_from_header(response)
            logger.info(f"delete protection store task id : {task_uri.split('/')[-1]}")
            task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30,api_header=headers)
            if task_status == helpers.TaskStatus.success:
                logger.info(f"Protection store with id {protection_store_id} deleted successfully.")
            elif task_status == helpers.TaskStatus.timeout:
                logger.error("Protection store deletion failed with timeout error.")
            elif task_status == helpers.TaskStatus.failure:
                raise Exception("Protection store deletion failed with status'FAILED' error")
            else:
                raise Exception("Protection store deletion failed with unknown error")

        else:
            err_msg = f"Failed to delete protection store. Response is {response}"
            logger.error(err_msg)
            raise Exception(err_msg)
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while deleting protection store with id {protection_store_id}:: {e}")


def delete_all_protection_stores_from_current_psg(psgw_name, force=False):
    """To delete all protection ids associate with psg name.

    Args:
        psgw_name (string): to get associate with psg name
        force (bool): while deleting store weather to use force or not. Defaults to False.
    """
    (onprem_protection_store_id_list, cloud_protection_store_id_list) = get_on_premises_and_cloud_protection_store(
        psgw_name
    )
    protection_store_ids = onprem_protection_store_id_list + cloud_protection_store_id_list
    for protection_store_id in protection_store_ids:
        delete_protection_store(protection_store_id, force=force)
