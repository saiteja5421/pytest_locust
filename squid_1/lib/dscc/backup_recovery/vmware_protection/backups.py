import requests
import logging
import time
from waiting import wait, TimeoutExpired
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type
from common import helpers
from tests.vmware.vmware_config import Paths
from requests import codes

from common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.dscc.backup_recovery.vmware_protection import protection_policy

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


def get_task_for_vm(filter = None):
    """Get task object for vm

    Args:
        asset_name (str): virtual machine name

    Returns:
        Object: Returns task object
    """
    url = f"{helpers.get_locust_host()}/{Paths.TASK_API}{filter}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    return response
    


def get_backups(asset_id, backup_type):
    """

    Args:
        asset_id (str): Asset id
        backup_type (str): Backu type Backups/Snapshots

    Returns:
        Object: Returns backup object
    """
    url = f"{helpers.get_locust_host()}{Paths.virtual_machines_backups}/{asset_id}/{backup_type}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    return response


def wait_for_backup_creation(asset_id: str, timeout_minutes: int = 5, sleep_seconds: int = 30) -> dict:
    """Wait for backup to be created. When backup is created state will be OK.
    When it is initiated the state would be 'starting'

    Args:
        asset_id (str): Virtual Machine id
        timeout_minutes (int): Wait time in minutes
        sleep_seconds (int): sleep time in seconds

    Raises:
        Exception: If backup not created even after timeout minutes exception will be raised

    Returns:
        dict: backup dict response of recently created
    """
    timeout = (timeout_minutes * 60) / sleep_seconds

    while timeout:
        recent_backup = get_recent_backup(asset_id)
        if recent_backup is not None:
            recent_backup_id = recent_backup["id"]
            backup_dict = get_backup_detail(asset_id, recent_backup_id)
            if backup_dict["state"] == "OK":
                logger.info("Backup is created successfully")
                return backup_dict
            else:
                time.sleep(sleep_seconds)
        else:
            time.sleep(sleep_seconds)
        timeout = timeout - 1

    raise Exception(f"Backup is not created even after {timeout_minutes} minutes")


def get_recent_backup(asset_id) -> dict:
    """Get recent HPE Local backup for given virtual machine"""

    logger.info("Wait till the backup is created")

    url = f"{helpers.get_locust_host()}{Paths.virtual_machines_backups}/{asset_id}/backups"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(f"Recent backup response {response}")
    logger.info(f"Get backups-Response code is {response.status_code}")
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return None
    if response.status_code != requests.codes.ok:
        raise Exception(
            f"[get_recent_backup] -> Unable to get backup list. backup response is {response.text}. Status code is {response.status_code}"
        )

    response_data = response.json()
    logger.debug(f"backup list {response_data}")
    backup_count = len(response_data["items"])
    if backup_count != 0:
        recent_backup = response_data["items"][backup_count - 1]
        logger.info(f"recent backup is  {recent_backup}")
        return recent_backup


def get_backup_detail(asset_id, backup_id) -> dict:
    """for the given virtual  machine get the backup detail

    Args:
        asset_id (_type_): Virtual machine id
        backup_id (_type_): Backup Id

    Raises:
        Exception: If get backup REST call fails throw exception

    Returns:
        dict: response.json() dict of backup
    """

    url = f"{helpers.get_locust_host()}{Paths.virtual_machines_backups}/{asset_id}/backups/{backup_id}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(f"Get backups-Response code is {response.status_code}")
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code != requests.codes.ok:
        raise Exception(f"[get_backup_detail] -> Unable to get backup detail for vm id {asset_id} {backup_id}")
    response_data = response.json()
    logger.info("backup detail", response_data)
    return response_data


def validate_new_backups(asset_id, backups_list, backup_type: BackupTypeScheduleIDs, timeout_minutes=10):
    """Validate new backups created

    Args:
        asset_id (str): asset id
        backups_list (list): list of backups
        backup_type (BackupTypeScheduleIDs): list of Schedule Ids
        timeout_minutes (str): timeout minutes

    Returns:
        list: backup id list
    """
    if backup_type == BackupTypeScheduleIDs.snapshot:
        _type = "Array_Snapshot"
        _type_search = "snapshots"
        logger.info("Waiting snapshot validation")
        return wait_for_backup(asset_id, backups_list, _type_search, _type, timeout_minutes)
    if backup_type == BackupTypeScheduleIDs.local:
        _type = "On-Premises"
        _type_search = "backups"
        logger.info("Waiting local backup validation")
        return wait_for_backup(asset_id, backups_list, _type_search, _type, timeout_minutes)
    if backup_type == BackupTypeScheduleIDs.cloud:
        _type = "HPE_Cloud"
        _type_search = "backups"
        logger.info("Waiting cloud backup validation")
        return wait_for_backup(asset_id, backups_list, _type_search, _type, timeout_minutes)


def wait_for_backup_task(vm_id, backup_name, last_snapshot_task_id, task_uri):
    """Wait for backup task to be completed

    Args:
        vm_id (str): virtual machine id
        backup_name (str): backup name
        last_snapshot_task_id (str): last snapshot task id
        task_uri (str): task uri
    """
    filter = f"?offset=0&limit=10&sort=createdAt+desc&filter='backup-and-recovery' in services and sourceResourceUri in ('{Paths.virtual_machines}/{vm_id}')"
    response = get_task_for_vm(filter).json()
    search_for_correct_task = [response for response in response["items"] if backup_name in response["name"]]
    logger.info(f"Response is : {response}")
    assert (
        len(search_for_correct_task) != 0
    ), f"Job for: '{backup_name}' has not been found. We got empty list: {search_for_correct_task} in a response {response['items']}"
    task_id = search_for_correct_task[0]["id"]
    assert not last_snapshot_task_id or task_id != last_snapshot_task_id, "New task hasn't been created."

    task_status = helpers.wait_for_task(task_uri=task_uri, timeout_minutes=2, sleep_seconds=30, api_header=headers)
    assert task_status == helpers.TaskStatus.success, f"Run backup task {task_id} : {task_status}"
    logger.info(f"{backup_name} has been created successfully")


@retry(retry=retry_if_exception_type(AssertionError), stop=stop_after_delay(420), wait=wait_fixed(10))
def wait_for_backup_task_with_retry(asset_name, backup_name, last_snapshot_task_id, task_uri):
    wait_for_backup_task(asset_name, backup_name, last_snapshot_task_id, task_uri)


def wait_for_backup(asset_id, backups_list, type_search, _type, timeout_minutes, sleep_seconds=30):
    backups = {}
    timeout = timeout_minutes * 60

    def _return_condition_backup():
        response = get_backups(asset_id, type_search)
        if response.status_code == codes.ok:
            nonlocal backups
            backups = response.json()
            logger.debug(f"All backups that were found: {backups}")
            if backups["total"] == backups_list["total"]:
                return False

            intersection_list = [x for x in backups["items"] if x not in backups_list["items"]]
            for item in intersection_list:
                if _type in item["name"] and item["state"] == "OK" and item["status"] == "OK":
                    logger.info(f"{item['name']} found.")
                    return item
            return False

    try:
        new_backup = wait(
            _return_condition_backup,
            timeout_seconds=timeout,
            sleep_seconds=sleep_seconds,
        )
        return new_backup
    except TimeoutExpired:
        raise AssertionError(f"New backups were not found in {timeout} seconds, we got response {backups['items']}")


def search_schedule_id_of_stores(protection_policy_id, backup_type):
    """It will search of schedule ids of protection template and returns ids based on backup type.

    Args:
        protection_policy_id (str): protection policy id
        backup_type (str): type of backup i.e., cloud or local

    Returns:
        schedule_ids: list of schedule ids
    """
    onprem_schedule_ids = []
    cloud_schedule_ids = []
    snapshot_schedule_ids = []
    protection_policies = protection_policy.get_protection_policy_by_id(protection_policy_id)
    for policy in protection_policies["protections"]:
        pid = policy["schedules"][0]["scheduleId"]
        if "Array_Snapshot" in policy["schedules"][0]["name"]:
            snapshot_schedule_ids.append(pid)
        elif "On-Premises" in policy["schedules"][0]["name"]:
            onprem_schedule_ids.append(pid)
        elif "HPE_Cloud" in policy["schedules"][0]["name"]:
            cloud_schedule_ids.append(pid)
    if backup_type == BackupTypeScheduleIDs.cloud:
        return cloud_schedule_ids

    elif backup_type == BackupTypeScheduleIDs.local:
        return onprem_schedule_ids

    elif backup_type == BackupTypeScheduleIDs.snapshot:
        return snapshot_schedule_ids


def delete_backups_with_id(asset_id, backup_id, backup_type):
    url = f"{helpers.get_locust_host()}{Paths.virtual_machines_backups}/{asset_id}/{backup_type}/{backup_id}"
    response = requests.request("DELETE", url, headers=headers.authentication_header)
    logger.info(f"Delete backups {backup_id}-Response code is {response.status_code}")
    if response.status_code != requests.codes.accepted:
        raise Exception(f"[delete_backups_with_id] -> Unable to delete backup for vm id {asset_id} {backup_id}")
    return response


def delete_all_backups_from_vm(asset_id):
    """This method deletes backups (snapshots, on_premises and cloud) from given asset id.

    Args:
        asset_id (string): Id of target backup vm
    """
    backup_response = get_backups(asset_id,"snapshots").json()
    logger.info(f"Get snapshots response : {backup_response}")
    if backup_response.get('total') != 0:
        for item in backup_response.get('items'):
            backup_id = item['id']
            logger.info(f"Snapshot id to delete: {backup_id}")
            response = delete_backups_with_id(asset_id, backup_id, backup_type="snapshots")
    else:
        logger.info(f"VM {asset_id} contains no snapshots.")

    backup_response = get_backups(asset_id,"backups").json()
    logger.info(f"Get backup response : {backup_response}")
    if backup_response.get('total') != 0:
        for item in backup_response.get('items'):
            backup_id = item['id']
            logger.info(f"Backup id to delete: {backup_id}")
            response = delete_backups_with_id(asset_id, backup_id, backup_type="backups")
    else:
        logger.info(f"VM {asset_id} contains no backups.")
